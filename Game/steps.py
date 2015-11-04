from enum import Enum
from Game.selectors import Selector, ValueSelector
from Game.tests import Test
from Game.game import GameState, Action
import copy


class Step:
    def perform(self, game_state: GameState):
        pass


class ActionStep(Step):
    def __init__(self, action_selector: Selector):
        self.action_selector = action_selector

    def perform(self, game_state: GameState):
        action = self.action_selector.select_one_of_type(game_state, Action)
        action.perform(game_state)


class TestStep(Step):
    def __init__(self, test: Test, true_action_selector: Selector, false_action_selector: Selector):
        self.test = test
        self.false = false_action_selector
        self.true = true_action_selector

    def perform(self, game_state: GameState):
        selector = self.true if self.test.test(game_state) else self.false
        if selector is None:
            return
        selector.select_one_of_type(game_state, Action).perform(game_state)


class WhileStep(Step):
    def __init__(self, test: Test, action_selector: Selector):
        self.test = test
        self.action_selector = action_selector

    def perform(self, game_state: GameState):
        action = self.action_selector.select_one_of_type(game_state, Action)
        while self.test.test(game_state):
            action.perform(game_state)


class RepeatStep(Step):
    def __init__(self, count: Selector, action_selector: Selector, label: str=None):
        self.count = count
        self.action_selector = action_selector
        self.label = "count" if label is None else label

    def perform(self, game_state: GameState):
        count = self.count.select_one_of_type(game_state, int)
        action = self.action_selector.select_one_of_type(game_state, Action)
        for _ in range(count):
            action.perform(game_state)


class ForEachStep(Step):
    def __init__(self, selector: Selector, action_selector: Selector, label: str=None):
        self.selector = selector
        self.action_selector = action_selector
        self.label = "selected" if label is None else label

    def perform(self, game_state: GameState):
        action = self.action_selector.select_one_of_type(game_state, Action)
        for piece in self.selector.select(game_state):
            game_state.set_var([piece], self.label)
            action.perform(game_state)


class AssignAttributeStep(Step):
    def __init__(self, assign_to_selector: Selector, assign_selector: Selector, attribute_name: str):
        self.assign_to_selector = assign_to_selector
        self.assign_selector = assign_selector
        self.attribute_name = attribute_name

    def perform(self, game_state: GameState):
        attribute = self.assign_selector.select_one(game_state)
        for game_object in self.assign_to_selector.select(game_state):
            assert(game_object.attributes is not None), str(game_object)+" does not have attributes to assign"
            game_object.attributes[self.attribute_name] = attribute


class GiveTurnStep(Step):
    def __init__(self, players_selector: Selector, turn: Selector):
        self.turn = turn
        self.players_selector = players_selector

    def perform(self, game_state: GameState):
        from Game.game import Turn
        turn = self.turn.select_one_of_type(game_state, Turn)
        game_state.turns.append(turn)
        turn.perform(self.players_selector.select(game_state), game_state)
        game_state.turns.pop()


class EndGameStep(Step):
    def __init__(self, winners_selector: Selector):
        self.winners = winners_selector

    def perform(self, game_state: GameState):
        game_state.winners = self.winners.select(game_state)
        from Game.game import WonException
        raise WonException()


class Positions(Enum):
    First = 0,
    Last = 1,
    Random = 2,


class MovePieces(Step):
    def __init__(self, pieces: Selector, to: Selector, position: Positions=None, count: Selector=None, copy: bool=None):
        self.pieces = pieces
        self.to = to
        self.position = Positions.First if position is None else position
        self.count = count
        self.copy = copy is True

    def perform(self, game_state: GameState):
        from Game.game import Collection
        collection = self.to.select_one_of_type(game_state, Collection)
        pieces = self.pieces.select(game_state)
        if not self.copy:
            pieces = self.pieces.select(game_state)
            if self.count is not None:
                pieces = pieces[:self.count.select(game_state)[0]]
            collections = set()
            for piece in pieces:
                from Game.game import Piece
                assert(type(piece) == Piece), str(self.pieces)+" did not return pieces, rather: "+str(type(piece))
                collections.add(piece.parent)
            to_remove = set(pieces)

            for c in collections:
                to_move = [piece for piece in c.pieces if piece not in to_remove]
                c.pieces[:] = to_move
                assert(c.pieces == to_move)
        else:
            pieces = [copy.deepcopy(piece) for piece in pieces for _ in range(self.count.select(game_state)[0])]
        for piece in pieces:
            piece.parent = collection
        if self.position is Positions.First:
            collection.pieces.extend(pieces)
        elif self.position is Positions.Last:
            collection.pieces[:] = pieces + collection.pieces
        else:
            import random
            position = random.randint(0,len(collection.pieces))
            collection.pieces[:] = collection.pieces[:position] + pieces + collection.pieces[position:]


class ShuffleCollection(Step):
    def __init__(self, collection_selector: Selector):
        self.collection_selector = collection_selector

    def perform(self, game_state: GameState):
        for collection in self.collection_selector.select(game_state):
            import random
            random.shuffle(collection.pieces)


class Select(Step):
    def __init__(self, selector: Selector, filters: list, label: str=None):
        self.filters = filters
        self.selector = selector
        self.label = "selected" if label is None else label

    def perform(self, game_state: GameState):
        selected = self.selector.select(game_state)
        for f in self.filters:
            selected = f.filter(selected, game_state)
        try:
            game_state.set_var(selected, self.label)
        except:
            print("Selector: "+str(self.selector))
            print("Selected: "+str(selected))
            raise

    def __repr__(self):
        return str(self.selector)+"["+", ".join(str(f) for f in self.filters)+"]"


class PlayerSelect(Step):
    def __init__(self, select: Select, label: str=None, min_pieces: Selector=None, max_pieces: Selector=None):
        self.select = select
        self.min = ValueSelector(0) if min_pieces is None else min_pieces
        self.max = ValueSelector(99999999) if max_pieces is None else max_pieces
        self.label = "selected" if label is None else label

    def perform(self, game_state: GameState):
        self.select.perform(game_state)
        selected = game_state.get_var(self.select.label)
        real_max = self.max.select_one_of_type(game_state, int)
        real_min = self.min.select_one_of_type(game_state, int)
        assert(real_min <= real_max), "Min greater than max"
        assert(real_min <= len(selected)), "Min greater than available options selected by "+str(self.select)
        if real_max > len(selected):
            real_max = len(selected)
        if selected:
            selected = game_state.player.select(selected, real_min, real_max, game_state, id(self))
            assert(len(selected) <= real_max)
            assert(len(selected) >= real_min)
        game_state.set_var(selected, self.label)


class PlayerChoice(Step):
    def __init__(self, options: dict):
        self.options = options

    def perform(self, game_state: GameState):
        choice = game_state.player.select(list(self.options.keys()), 1, 1, game_state, id(self))
        assert(len(choice) == 1), "Can only select 1 choice"
        self.options[choice[0]].perform(game_state)
