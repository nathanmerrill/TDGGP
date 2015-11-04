from enum import Enum
import copy


class WonException(Exception):
    pass


class AccessError(Exception):
    pass


class GameObject:
    def __init__(self, name: str, has_attributes: bool):
        self.name = name
        self.attributes = {} if has_attributes else None

    def get_attribute(self, name):
        try:
            return self.attributes[name]
        except Exception as e:
            raise AccessError(str(self)+" does not have attribute '"+name+"'", e)

    def set_attribute(self, name, item):
        self.attributes[name] = item

    def has_attribute(self, name):
        return name in self.attributes

    def __repr__(self):
        return self.name


class Game(GameObject):
    def __init__(self, name):
        super(Game, self).__init__(name, True)
        self.collections = {}
        """:type: dict[str, Collection]"""
        self.player_collections = {}
        """:type: dict[str, Collection]"""
        self.pieces = {}
        """:type: dict[str, Piece]"""
        self.turns = {}
        """:type: dict[str, Turn]"""
        self.actions = {}
        """:type: dict[str, Action]"""
        self.min_players = 1
        self.max_players = 2
        self.starting_turn = None
        """:type: Turn"""
        self.players = []
        """:type: list[Player]"""

    def start(self, players: list):
        self.players = players
        game_state = GameState(self)
        for name, collection in self.player_collections.items():
            for player in players:
                player.collections[name] = copy.deepcopy(collection)
        try:
            import sys
            sys.setrecursionlimit(1500)
            self.starting_turn.perform(players, game_state)
        except WonException:
            print("Winners: "+str(game_state.winners))

    def __getitem__(self, item):
        if item == "collections":
            return list(self.collections.values())
        return [self.collections[item]]


class GameState:
    def __init__(self, game: Game):
        self.game = game
        self.player = None
        """:type: Player"""
        self.vars = {}
        """:type: dict[list[GameObject]]"""
        self.selected = None
        self.turns = []
        self.scopes = {
            "game": lambda: [self.game],
            "player": lambda: [self.player],
            "players": lambda: self.game.players,
            "opponents": lambda: [a for a in self.game.players if a is not self.player],
            "pieces": lambda: list(self.game.pieces.values()),
            "piece": lambda: [NamedSet(self.game.pieces)],
            "turn": lambda: [NamedSet(self.game.turns)],
            "action": lambda: [NamedSet(self.game.actions)],
            "current_turn": lambda: [self.turns[-1]]
        }
        self.winners = None

    def set_player(self, player):
        self.player = player

    def set_var(self, var, name):
        assert(type(var) == list)
        self.vars[name] = var

    def get_var(self, name):
        return self.vars[name]

    def get_selected(self):
        return self.selected

    def set_selected(self, selected):
        self.selected = selected

    def get_scopes(self, scope):
        try:
            return self.scopes[scope]()
        except KeyError:
            raise AccessError("No such scope: '"+scope+"'")


class NamedSet:
    def __init__(self, items: dict):
        self.items = items

    def __getitem__(self, item):
        return [self.items[item]]


class Visibility(Enum):
    Hidden = 0,
    Owner = 1,
    Player = 2,
    Public = 3,


class Collection(GameObject):
    def __init__(self, name):
        super(Collection, self).__init__(name, True)
        self.visible_count = Visibility.Hidden
        """:type: Visibility"""
        self.visible_top = Visibility.Hidden
        """:type: Visibility"""
        self.visible_all = Visibility.Hidden
        """:type: Visibility"""
        self.pieces = []
        self.filters = {
            "pieces": lambda s: s.pieces,
            "size": lambda s: [len(s.pieces)],
            "first": lambda s: [s.pieces[-1]] if s.pieces else [],
            "last": lambda s: [s.pieces[0]] if s.pieces else [],
        }

    def __getitem__(self, item):
        try:
            return self.filters[item](self)
        except:
            print("Pieces:"+str(self.pieces))
            raise

    def __repr__(self):
        return super(Collection, self).__repr__()+str(self.pieces)

    def __deepcopy__(self, memo):
        p = Collection(self.name)
        p.visible_top = self.visible_top
        p.visible_all = self.visible_all
        p.visible_count = self.visible_count
        p.attributes = copy.copy(self.attributes)
        return p


class Turn(GameObject):
    def __init__(self, name, action):
        super(Turn, self).__init__(name, True)
        self.action = action

    def perform(self, players, game_state: GameState):
        players = sorted(players, key=lambda p: p.index)
        for player in players:
            game_state.set_player(player)
            self.action.perform(game_state)


class Piece(GameObject):
    def __init__(self, name, parent):
        super(Piece, self).__init__(name, True)
        self.parent = parent

    def __deepcopy__(self, memo):
        p = Piece(self.name, None)
        p.attributes = copy.copy(self.attributes)
        return p


class Action(GameObject):
    def __init__(self, steps, name):
        super(Action, self).__init__(name, False)
        self.steps = steps

    def perform(self, game_state: GameState):
        for step in self.steps:
            from Game.steps import Step
            assert(isinstance(step, Step)), str(step)+" is not a step"
            step.perform(game_state)


class Player(GameObject):
    def __init__(self, index, name=None):
        if name is None:
            name = "Player "+str(index)
        super(Player, self).__init__(name, True)
        self.index = index
        self.collections = {}

    def __getitem__(self, item):
        return [self.collections[item]]

    def select(self, choices: list, min_choices: int, max_choices: int, game_state: GameState, current_action: int):
        pass

    def __repr__(self):
        return "Player "+str(self.index)
