from Game.game import GameState
from Game.tests import Test
import operator
operators = {
    '+': operator.add,
    '-': operator.sub,
    '*': operator.mul,
    '/': operator.floordiv,
}


class Selector:
    def select(self, game_state: GameState, selected: list) -> list:
        pass

    def select_one(self, game_state: GameState, selected: list):
        item = self.select(game_state, selected)
        assert(len(item) == 1), str(self)+" selected "+str(len(item))+" items"
        return item[0]

    def select_one_of_type(self, game_state: GameState, item_type, selected: list):
        item = self.select_one(game_state, selected)
        assert(isinstance(item, item_type)), \
            str(self) + " selected item of type " + str(type(item)) + " instead of " + str(item_type)
        return item


class IteratingSelector(Selector):
    def __init__(self, selectors):
        self.selectors = selectors

    def select(self, game_state: GameState, selected: list):
        current_selected = selected
        for selector in self.selectors:
            current_selected = selector.select(game_state, current_selected)
        return current_selected

    def __repr__(self):
        return "".join([str(selector) for selector in self.selectors])


class OperatorSelector(Selector):
    def __init__(self, left: Selector, op: operator, right: Selector):
        self.left = left
        self.right = right
        self.operator = operators[op]
        self.str = op

    def select(self, game_state: GameState, selected: list):
        left_selected = self.left.select_one(game_state, selected)
        right_selected = self.right.select_one(game_state, selected)
        assert(type(left_selected) == type(right_selected)), \
            str(self.left) + " did not match type with "+str(self.right) \
            + ": " + str(type(left_selected)) + " vs " + str(type(right_selected)) \
            + " Left value: "+str(left_selected)+" Right value: "+str(right_selected)
        return [self.operator(left_selected, right_selected)]

    def __repr__(self):
        return str(self.left) + self.str + str(self.right)


class ValueSelector(Selector):
    def __init__(self, value):
        self.value = value

    def select(self, game_state: GameState, selected: list):
        assert(selected is None)
        return [self.value]

    def __repr__(self):
        return str(self.value)

    def get_type(self, game_state):
        return type(self.value)


class AttributeSelector(Selector):
    def __init__(self, attribute_name: str):
        self.attribute_name = attribute_name

    def select(self, game_state: GameState, selected: list):
        try:
            return [parent.get_attribute(self.attribute_name)
                    for parent in selected
                    if parent.has_attribute(self.attribute_name)]
        except:
            print("Self: "+str(self))
            print("Selected: "+str(selected))
            raise

    def __repr__(self):
        return "@"+self.attribute_name


class SizeSelector(Selector):
    def __init__(self, to_count: Selector):
        self.to_count = to_count

    def select(self, game_state: GameState, selected: list):
        return [len(self.to_count.select(game_state, selected))]

    def __repr__(self):
        return "count("+str(self.to_count)+")"


class FirstSelector(Selector):
    def __init__(self, first_of: Selector):
        self.first_of = first_of

    def select(self, game_state: GameState, selected: list):
        return [self.first_of.select(game_state, selected)[0]]

    def __repr__(self):
        return "first("+str(self.first_of)+")"


class RandomSelector(Selector):
    def __init__(self, random_from: Selector, count: Selector):
        self.random_from = random_from
        self.count = count

    def select(self, game_state: GameState, selected: list):
        import random
        return random.sample(self.random_from.select(game_state, selected), self.count.select(game_state, selected))


class ContextSelector(Selector):
    def __init__(self, context_name: str):
        self.context_name = context_name
        assert(self.context_name[0] not in {"$", ":", "@"})

    def select(self, game_state: GameState, selected: list):
        try:
            return [child
                    for parent in selected
                    for child in parent[self.context_name]]
        except:
            print("Self: "+str(self))
            print("Context: "+self.context_name)
            print("Selected: "+str(selected))
            raise

    def __repr__(self):
        return ":"+self.context_name


class NamedSet:
    def __init__(self, items: dict):
        self.items = items

    def get_item(self, item):
        return [self.items[item]]


class NamedItemSelector(Selector):
    def __init__(self, item_name):
        self.item_name = item_name

    def select(self, game_state: GameState, selected: list):
        assert(len(selected) == 1)
        return selected[0].get_item(self.item_name)

    def __repr__(self):
        return "NamedItem::"+self.item_name


scopes = {
    "game": lambda s: [s.game],
    "player": lambda s: [s.player],
    "players": lambda s: s.game.players,
    "opponents": lambda s: [a for a in s.game.players if a is not s.player],
    "pieces": lambda s: list(s.game.pieces.values()),
    "piece": lambda s: [NamedSet(s.game.pieces)],
    "turn": lambda s: [NamedSet(s.game.turns)],
    "action": lambda s: [NamedSet(s.game.actions)],
    "current_turn": lambda s: [s.turns[-1]]
}


class ScopeSelector(Selector):

    def __init__(self, scope: str):
        self.scope = scope

    def select(self, game_state: GameState, selected: list):
        return scopes[self.scope](game_state)

    def __repr__(self):
        return self.scope


class VariableSelector(Selector):
    def __init__(self, variable_name: str):
        self.variable_name = variable_name

    def select(self, game_state: GameState, selected: list):
        return game_state.get_var(self.variable_name)

    def __repr__(self):
        return "$"+self.variable_name


class FilterSelector(Selector):
    def __init__(self, test):
        self.test = test

    def select(self, game_state: GameState, selected: list):
        return [item for item in selected if self.test.test(game_state, item)]

    def __repr__(self):
        return "["+str(self.test)+"]"
