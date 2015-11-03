from enum import Enum
from Game.selectors import Selector, ValueSelector
from Game.tests import Test
from Game.game import GameState
import copy


class Step:
    def perform(self, game_state: GameState):
        pass


class ActionStep(Step):
    def __init__(self, action_selector: Selector):
        self.action_selector = action_selector

    def perform(self, game_state: GameState):
        for action in self.action_selector.select(game_state):
            action.perform(game_state)


class TestStep(Step):
    def __init__(self, test: Test, false_action_selector: Selector, true_action_selector: Selector):
        self.test = test
        self.false = false_action_selector
        self.true = true_action_selector

    def perform(self, game_state: GameState):
        selector = self.false if self.test.test(game_state) else self.true
        if selector is None:
            return
        selection = selector.select(game_state)
        for action in selection:
            try:
                action.perform(game_state)
            except:
                print("Selector: "+str(selector))
                print("Selected: "+str(selection))
                raise


class WhileStep(Step):
    def __init__(self, test: Test, action_selector: Selector):
        self.test = test
        self.action_selector = action_selector

    def perform(self, game_state: GameState):
        while self.test.test(game_state):
            for action in self.action_selector.select(game_state):
                action.perform(game_state)


class RepeatStep(Step):
    def __init__(self, count: Selector, action_selector: Selector, label: str=None):
        self.count = count
        self.action_selector = action_selector
        self.label = "count" if label is None else label

    def perform(self, game_state: GameState):
        count = self.count.select(game_state)
        assert(len(count) == 1)
        for _ in range(int(count[0])):
            for action in self.action_selector.select(game_state):
                action.perform(game_state)


class ForEachStep(Step):
    def __init__(self, selector: Selector, action_selector: Selector, label: str=None):
        self.selector = selector
        self.action_selector = action_selector
        self.label = "selected" if label is None else label

    def perform(self, game_state: GameState):
        if str(self.selector) == "player:hand:pieces":
            print("Pieces:"+str(self.selector.select(game_state)))
        for piece in self.selector.select(game_state):
            game_state.set_var([piece], self.label)
            for action in self.action_selector.select(game_state):
                action.perform(game_state)


class AssignAttributeStep(Step):
    def __init__(self, assign_to_selector: Selector, assign_selector: Selector, attribute_name: str):
        self.assign_to_selector = assign_to_selector
        self.assign_selector = assign_selector
        self.attribute_name = attribute_name

    def perform(self, game_state: GameState):
        to_assign = self.assign_selector.select(game_state)
        assert(len(to_assign) == 1)
        attribute = to_assign[0]
        for game_object in self.assign_to_selector.select(game_state):
            game_object.attributes[self.attribute_name] = attribute


class GiveTurnStep(Step):
    def __init__(self, players_selector: Selector, turn: Selector):
        self.turn = turn
        self.players_selector = players_selector

    def perform(self, game_state: GameState):
        turn = self.turn.select(game_state)
        assert(len(turn) == 1)
        game_state.turns.append(turn[0])
        turn[0].perform(self.players_selector.select(game_state), game_state)
        game_state.turns.pop()


class EndGameStep(Step):
    def __init__(self, winners_selector: Selector):
        self.winners = winners_selector

    def perform(self, game_state: GameState):
        game_state.winners = self.winners.select(game_state)


class Positions(Enum):
    First = 0,
    Last = 1,
    Random = 2,


class MovePieces(Step):
    def __init__(self, pieces: Selector, to: Selector, position: Positions=None, count: Selector=None, copy: bool=None):
        self.pieces = pieces
        self.to = to
        self.position = Positions.First if position is None else position
        import Game.selectors
        self.count = count
        self.copy = copy is True

    def perform(self, game_state: GameState):
        collection = self.to.select(game_state)[0]
        pieces = self.pieces.select(game_state)
        if not self.copy:
            pieces = self.pieces.select(game_state)
            if self.count is not None:
                pieces = pieces[:self.count.select(game_state)[0]]
            collections = set()
            for piece in pieces:
                collections.add(piece.parent)
            to_remove = set(pieces)

            print("Moving "+str(self.pieces)+" to "+str(self.to))
            print(self.pieces.select(game_state))

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


class PlayerSelect(Step):
    def __init__(self, select: Select, label: str=None, min_pieces: Selector=None, max_pieces: Selector=None):
        self.select = select
        self.min = ValueSelector(0) if min_pieces is None else min_pieces
        self.max = ValueSelector(float("inf")) if max_pieces is None else max_pieces
        self.label = "selected" if label is None else label

    def perform(self, game_state: GameState):
        self.select.perform(game_state)
        selected = game_state.get_var(self.select.label)
        if selected:
            real_max = min(len(selected), self.max.select(game_state)[0])
            real_min = min(len(selected), self.min.select(game_state)[0])
            selected = game_state.player.select(selected, real_min, real_max, game_state, id(self))
        game_state.set_var(selected, self.label)


class PlayerChoice(Step):
    def __init__(self, options: dict):
        self.options = options

    def perform(self, game_state: GameState):
        choice = game_state.player.select(list(self.options.keys()), 1, 1, game_state, id(self))
        self.options[choice].perform(game_state)
