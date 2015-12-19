from Game import selectors as selector_models
from Game import tests as test_models
from pyparsing import *


class BadSelector(Exception):
    pass

valid_name = Word(alphas+"_")
named_object_separator = "::"
context_separator = ":"

variable = "$" + valid_name
game_scope = CaselessLiteral("game")
player_scope = CaselessLiteral("player") ^ CaselessLiteral("players") ^ CaselessLiteral("opponents")
turn_scope = CaselessLiteral("current_turn")
false = CaselessLiteral("false")
true = CaselessLiteral("true")
number = Optional("-")+Word(nums)

literal_collection = (game_scope ^ player_scope) + context_separator + valid_name
literal_piece = CaselessLiteral("pieces") ^ (CaselessLiteral("piece") + named_object_separator + valid_name)
literal_turn = CaselessLiteral("turn") + named_object_separator + valid_name
literal_action = CaselessLiteral("action") + named_object_separator + valid_name


numeric = Forward()
collection = Forward()
piece = Forward()
turn = Forward()
action = Forward()
attribute = Forward()
boolean = Forward()
player = Forward()

item = (numeric ^ piece ^ collection ^ boolean ^ player ^ turn ^ action ^ sglQuotedString)


def func_matcher(name, param, numeric_param=False):
    return CaselessLiteral(name)+"("+param+(","+numeric if numeric_param else Empty())+")"

count_function = func_matcher("count", item)
random_collection_function = func_matcher("random", collection, True)
random_piece_function = func_matcher("random", piece, True)
first_piece_function = func_matcher("first", piece)

collection_to_pieces = context_separator + CaselessLiteral("pieces")

collection_pieces = collection + collection_to_pieces

test = (numeric + oneOf("= <= >= > < !=") + numeric) ^ piece ^ collection ^ (collection + "=" + collection) ^ (piece + "=" + piece)

to_attribute = "@" + valid_name

piece_in_filter = piece ^ collection_to_pieces
attribute_in_filter = to_attribute ^ attribute
count_in_filter = func_matcher("count", piece_in_filter)
random_in_filter = func_matcher("random", piece_in_filter, True)
first_in_filter = func_matcher("first", piece_in_filter)
numeric_in_filter = Forward()

numeric_in_filter << (count_in_filter ^ attribute_in_filter ^ number ^ variable ^ boolean ^ sglQuotedString) + ZeroOrMore(oneOf("+ - *") + numeric_in_filter)

testing_attributes = ((numeric_in_filter + oneOf("= <= >= > != <") + numeric_in_filter) ^ attribute_in_filter)

attribute_test = "["+(testing_attributes) + "]"

testing_collections = (piece_in_filter ^ random_in_filter ^ first_in_filter)

collection_piece_test = "["+( testing_collections)+"]"

collection_test = collection_piece_test ^ attribute_test


partial_collection = (literal_collection ^ random_collection_function) + ZeroOrMore(attribute_test)
partial_piece = (literal_piece ^ random_piece_function ^ first_piece_function ^ (partial_collection + collection_to_pieces)) + ZeroOrMore(attribute_test)
partial_action = literal_action + ZeroOrMore(attribute_test)
partial_turn = (turn_scope ^ literal_turn) + ZeroOrMore(attribute_test)
partial_player = player_scope + ZeroOrMore(attribute_test)

piece << (partial_piece ^ collection_pieces ^ attribute ^ variable) + ZeroOrMore(attribute_test)
collection << (partial_collection ^ attribute ^ variable) + ZeroOrMore(collection_test)
turn << (partial_turn ^ attribute ^ variable) + ZeroOrMore(attribute_test)
action << (partial_action ^ attribute ^ variable) + ZeroOrMore(attribute_test)
player << (partial_player ^ attribute ^ variable) + ZeroOrMore(attribute_test)

attribute << (partial_piece ^ partial_collection ^ partial_action ^ partial_turn ^ partial_player ^ variable ^ game_scope) + to_attribute


numeric << (number ^ count_function ^ attribute ^ variable) + ZeroOrMore(oneOf("+ - *") + numeric)

boolean << (test ^ true ^ false)


def parse(string, selector_type):
    if string is None:
        return None
    print(string)
    try:
        return to_selector((StringStart()+selector_type+StringEnd()).setDebug(False).parseString(string))
    except (Exception, RecursionError, ValueError):
        raise


def to_selector(tokens) -> selector_models.Selector:
    selectors = to_selectors(tokens)
    if len(selectors) == 1:
        return selectors[0]
    return selector_models.IteratingSelector(selectors)

def to_selectors(tokens) -> list:
    selectors = []
    iterator = 0
    while iterator < len(tokens):
        next_token = tokens[iterator].lower()
        if next_token == "::":
            selectors.append(selector_models.NamedItemSelector(tokens[iterator + 1]))
            iterator += 2
            continue
        if next_token == ":":
            selectors.append(selector_models.ContextSelector(tokens[iterator + 1]))
            iterator += 2
            continue
        if next_token == "[":
            open_braces = 1
            for i in range(iterator+1, len(tokens)):
                a = tokens[i]
                if a == "[":
                    open_braces += 1
                elif a == "]":
                    open_braces -= 1
                    if open_braces == 0:
                        end_position = i
                        break
            else:
                raise AssertionError("Braces don't close")
            t = to_test(tokens[iterator + 1:end_position])
            selectors.append(selector_models.FilterSelector(t))
            iterator = end_position+1
            continue
        if next_token in ("count", "first", "random"):
            open_parens = 1
            comma_position = -1
            for i in range(iterator+2, len(tokens)):
                a = tokens[i]
                if a == "(":
                    open_parens += 1
                if a == ")":
                    open_parens -= 1
                    if open_parens == 0:
                        end_position = i
                        break
                if a == "," and open_parens == 1:
                    comma_position = a
            else:
                raise AssertionError("Parenthesis don't close")
            if next_token == "count":
                selector = to_selector(tokens[iterator+2:end_position])
                selectors.append(selector_models.SizeSelector(selector))
            elif next_token == "first":
                selector = to_selector(tokens[iterator+2:end_position])
                selectors.append(selector_models.FirstSelector(selector))
            else:
                print(tokens)
                selector = to_selector(tokens[iterator+2:comma_position])
                count = to_selector(tokens[comma_position+1:end_position])
                selectors.append(selector_models.RandomSelector(selector, count))
            iterator = end_position+1
            continue
        if next_token == "false":
            selectors.append(selector_models.ValueSelector(False))
            iterator += 1
            continue
        if next_token == "true":
            selectors.append(selector_models.ValueSelector(True))
            iterator += 1
            continue
        if next_token == "$":
            selectors.append(selector_models.VariableSelector(tokens[iterator+1]))
            iterator += 2
            continue
        if next_token == "@":
            selectors.append(selector_models.AttributeSelector(tokens[iterator+1]))
            iterator += 2
            continue
        if next_token in selector_models.scopes:
            selectors.append(selector_models.ScopeSelector(next_token))
            iterator += 1
            continue
        if next_token in selector_models.operators and selectors:
            left = selector_models.IteratingSelector(selectors)
            right = to_selector(tokens[iterator+1:])
            return [selector_models.OperatorSelector(left, next_token, right)]
        if next_token == "-":
            selectors.append(selector_models.ValueSelector(-int(tokens[iterator+1])))
            iterator += 2
            continue
        if str(next_token).startswith("'"):
            selectors.append(next_token[1:-1])
            iterator += 1
            continue
        selectors.append(int(next_token))
        iterator += 1
    return selectors


def to_test(arr: list) -> test_models.Test:
    equality_indicies = [i in test_models.comparisons for i in arr]
    if True in equality_indicies:
        equality_index = equality_indicies.index(True)
        before = to_selector(arr[:equality_index])
        after = to_selector(arr[equality_index+1:])
        return test_models.TestComparison(before, test_models.comparisons[arr[equality_index]], after)
    else:
        return test_models.TestExists(to_selector(arr))