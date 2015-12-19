from lxml import etree as ET
from lxml import etree as Element
from Game import game as game_models, \
    tests as test_models, \
    selectors as selector_models, \
    filters as filter_models, \
    steps as step_models
from Game import selectorparser
__author__ = 'Nathan Merrill'


class BadGameXML(Exception):
    def __init__(self, message, element: Element):
        message = "Error on line:"+str(element.sourceline)+" on tag <"+element.tag+">\n\t"+message
        super(BadGameXML, self).__init__(message)


class BadAttribute(Exception):
    pass


def parse_xml(filename):
    tree = ET.parse(filename)
    root = tree.getroot()
    return create_game(root)


def create_game(root: Element):
    game = game_models.Game(root.attrib['name'])
    game.max_players = root.attrib['max_players']
    game.min_players = root.attrib['min_players']
    add_actions(root.find("actions"), game)
    add_collections(root.find("collections"), game)
    add_turns(root.find("turns"), game)
    add_pieces(root.find("pieces"), game)
    return game


def add_pieces(element: Element, game: game_models.Game):
    for piece in element:
        name = piece.attrib["id"]
        new_piece = game_models.Piece(name, None)
        for attribute in piece:
            if attribute.tag == "attribute":
                try:
                    attribute_value = int(attribute.text)
                except ValueError:
                    if attribute.text.lower() == "true":
                        attribute_value = True
                    elif attribute.text.lower() == "false":
                        attribute_value = False
                    else:
                        attribute_value = attribute.text
                new_piece.attributes[attribute.attrib["name"]] = attribute_value
        game.pieces[name] = new_piece
    for piece in element:
        for relation in piece:
            if relation.tag == "relation":
                related_name = relation.attrib["to"]
                if related_name in game.actions:
                    related = game.actions[related_name]
                elif related_name in game.collections:
                    related = game.collections[related_name]
                elif related_name in game.pieces:
                    related = game.pieces[related_name]
                elif related_name in game.turns:
                    related = game.turns[related_name]
                else:
                    raise BadGameXML("Relation doesn't exist", relation)
                game.pieces[piece.attrib["id"]].attributes[relation.attrib["name"]] = related


def add_turns(element: Element, game: game_models.Game):
    for turn in element:
        name = turn.attrib["id"]
        new_turn = game_models.Turn(action=game.actions[turn.attrib["action"]], name=name)
        game.turns[name] = new_turn
        if turn.attrib.get("initial") is not None:
            game.starting_turn = new_turn


def add_collections(element: Element, game: game_models.Game):
    for collection in element:
        (game.collections
         if collection.attrib['scope'] == 'game'
         else game.player_collections)[collection.attrib['id']] = create_collection(collection)


def create_collection(element: Element):
    collection = game_models.Collection(element.attrib['id'])
    for prop in element:
        if prop.tag == "attribute":
            try:
                attribute_value = int(prop.text)
            except ValueError:
                if prop.text.lower() == "true":
                    attribute_value = True
                elif prop.text.lower() == "false":
                    attribute_value = False
                else:
                    attribute_value = prop.text
            collection.attributes[prop.attrib['name']] = attribute_value
        elif prop.tag == "visibility":
            visible_to = game_models.Visibility[prop.attrib["to"].capitalize()]
            if prop.attrib["item"] == "top":
                collection.visible_top = visible_to
            elif prop.attrib["item"] == "all":
                collection.visible_all = visible_to
            elif prop.attrib["item"] == "count":
                collection.visible_count = visible_to
    return collection


def add_actions(element: Element, game):
    for action in element:
        game.actions[action.attrib['id']] = create_action(action)


def create_action(element: Element):
    if "id" in element.attrib:
        name = element.attrib["id"]
    else:
        name = str(element.sourceline)
        for parent in element.iterancestors():
            if "id" in parent.attrib:
                name += parent.attrib["id"]
                break
    return game_models.Action(list(parse_step(step) for step in element), name)


def parse_step(element: Element):
    actions = {
        "if": parse_if,
        "player-select": parse_player_select,
        "select": parse_select,
        "move-pieces": parse_move_pieces,
        "repeat": parse_repeat,
        "assign-attribute": parse_assign_attribute,
        "perform": parse_perform,
        "shuffle-collection": parse_shuffle_collection,
        "player-choice": parse_player_choice,
        "give-turn": parse_give_turn,
        "end-game": parse_end_game,
        "remove": parse_remove,
    }
    if element.tag not in actions:
        raise BadGameXML("Invalid tag:<"+element.tag+">", element)
    try:
        action = actions[element.tag](element)
    except Exception as e:
        raise BadGameXML("Error thrown:"+str(e), element)
    return action


def parse_remove(element: Element):
    return step_models.RemoveStep(element.attrib["label"], element.sourceline)


def parse_end_game(element: Element):
    return step_models.EndGameStep(selectorparser.parse(element.attrib["winners"], selectorparser.player), element.sourceline)


def parse_give_turn(element: Element):
    return step_models.GiveTurnStep(selectorparser.parse(element.attrib["to"], selectorparser.player),
                                    selectorparser.parse(element.attrib["turn"], selectorparser.turn),
                                    element.sourceline)


def parse_player_choice(element: Element):
    return step_models.PlayerChoice(dict([(child.attrib["value"], create_action(child)) for child in element]),
                                    element.sourceline)


def parse_shuffle_collection(element: Element):
    return step_models.ShuffleCollection(selectorparser.parse(element.attrib["collection"], selectorparser.collection), element.sourceline)


def parse_perform(element: Element):
    action = selectorparser.parse(element.attrib["action"], selectorparser.action)
    return step_models.ActionStep(action, element.sourceline)


def parse_assign_attribute(element: Element):
    parts = selectorparser.attribute.parseString(element.attrib["attribute"])
    attr_name = parts[-1]
    attr = selectorparser.to_selector(parts[:-2])
    value = selectorparser.parse(element.attrib["value"], selectorparser.item)
    return step_models.AssignAttributeStep(attr, value, attr_name, element.sourceline)


def parse_repeat(element: Element):
    label = element.attrib.get("label")
    action = create_action(element)
    action_selector = selector_models.ValueSelector(action)
    if "over" in element.attrib:
        over = selectorparser.parse(element.attrib["over"], selectorparser.item)
        repeat = step_models.ForEachStep(over, action_selector, label, element.sourceline)
    elif "test" in element.attrib or "exists" in element.attrib:
        test = parse_comparison(element.attrib["test"]) \
            if "test" in element.attrib \
            else parse_exists(element.attrib["exists"])
        repeat = step_models.WhileStep(test, action_selector, element.sourceline)
    elif "count" in element.attrib:
        count = selectorparser.parse(element.attrib["count"], selectorparser.numeric)
        repeat = step_models.RepeatStep(count, action_selector, label, element.sourceline)
    else:
        raise BadGameXML("Repeat has no attribute to repeat over", element)
    return repeat


def parse_move_pieces(element: Element):
    pieces = selectorparser.parse(element.attrib['pieces'], selectorparser.piece)
    to = selectorparser.parse(element.attrib['to'], selectorparser.collection)
    copy = element.attrib.get("copy") == 'true'
    count = selectorparser.parse(element.attrib["count"], selectorparser.numeric) if "count" in element.attrib else None
    position = step_models.Positions[element.attrib.get("position")] if "position" in element.attrib else None
    return step_models.MovePieces(pieces, to, position, count, copy, element.sourceline)


def parse_select(element: Element):
    return step_models.Select(selectorparser.parse(element.attrib["from"], selectorparser.item), element.get("label"), element.sourceline)


def parse_filter(element: Element):
    if "exists" in element.attrib:
        f = filter_models.TestFilter(parse_exists(element.attrib["exists"]))
    elif "test" in element.attrib:
        f = filter_models.TestFilter(parse_comparison(element.attrib["test"]))
    elif "random" in element.attrib:
        f = filter_models.RandomFilter(int(element.attrib["random"]))
    else:
        raise BadGameXML("<filter> tag needs one of the following attributes: exists, test, random", element)
    if "out" in element.attrib and element.attrib["out"] == "true":
        f = filter_models.TestOutFilter(f)
    return f


def parse_player_select(element: Element):
    selector = parse_select(element)
    selector = step_models.PlayerSelect(selector,
                                        selectorparser.parse(element.attrib.get("min"), selectorparser.numeric),
                                        selectorparser.parse(element.attrib.get("max"), selectorparser.numeric),
                                        selectorparser.parse(element.attrib.get("player"), selectorparser.player),
                                        element.sourceline)
    return selector


def parse_if(element: Element):
    false = None
    true = None
    for child in element:
        if child.tag == "false":
            if false is not None:
                raise BadGameXML("Cannot have multiple false tags", element)
            false = create_action(child)
        elif child.tag == "true":
            if true is not None:
                raise BadGameXML("Cannot have multiple true tags", element)
            true = create_action(child)
        else:
            raise BadGameXML("Invalid tag:<"+child.tag+">", element)
    if ("test" in element.attrib and "exists" in element.attrib) \
            or ("test" not in element.attrib and "exists" not in element.attrib):
        raise BadGameXML("<if> must either have a 'test' attribute or an 'exists' attribute", element)
    try:
        true = selector_models.ValueSelector(true) if true is not None else None
        false = selector_models.ValueSelector(false) if false is not None else None
        parser = parse_comparison(element.attrib['test']) if "test" in element.attrib \
            else parse_exists(element.attrib['exists'])
        return step_models.TestStep(parser, true, false, element.sourceline)
    except BadAttribute as e:
        raise BadGameXML("Exception thrown", element) from e


def parse_comparison(test_str):
    return selectorparser.to_test(selectorparser.test.parseString(test_str))


def parse_exists(test_str):
    return selectorparser.to_test(selectorparser.item.parseString(test_str))
