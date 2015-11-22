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

    def get_attribute(self, name: str):
        try:
            return self.attributes[name]
        except Exception as e:
            raise AccessError(str(self)+" does not have attribute '"+name+"'", e)

    def set_attribute(self, name: str, item):
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
        self.state = GameState(self)

    def assign_players(self, players: list):
        self.players = players
        for name, collection in self.player_collections.items():
            for player in players:
                player.collections[name] = copy.deepcopy(collection)

    def start(self, players: list):
        if players:
            self.assign_players(players)
        try:
            import sys
            sys.setrecursionlimit(1500)
            self.starting_turn.perform([self.players[0]], self.state)
        except WonException:
            pass
        for player in players:
            if player in self.state.winners:
                player.won()
            else:
                player.lost()
        return self.state.winners

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

        self.winners = []

    def set_player(self, player):
        self.player = player

    def set_var(self, var, name):
        assert(type(var) == list)
        self.vars[name] = var

    def get_var(self, name):
        return self.vars[name]

    def get_selected(self):
        return self.selected

    def del_var(self, var):
        if var in self.vars:
            del self.vars[var]

    def set_selected(self, selected):
        self.selected = selected


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

    def is_visible(self, visibility: Visibility, game_state: GameState):
        return visibility == Visibility.Player or visibility == Visibility.Public or \
               (visibility == Visibility.Owner and self in game_state.player.collections.values())

    def top_visible(self, game_state: GameState):
        return self.is_visible(self.visible_top, game_state)

    def all_visible(self, game_state: GameState):
        return self.is_visible(self.visible_all, game_state)

    def count_visible(self, game_state: GameState):
        return self.is_visible(self.visible_count, game_state)


class Turn(GameObject):
    def __init__(self, name, action):
        super(Turn, self).__init__(name, True)
        self.action = action

    def perform(self, players, game_state: GameState):
        players = sorted(players, key=lambda p: p.index)
        old_player = game_state.player
        for player in players:
            game_state.set_player(player)
            self.action.perform(game_state)
        game_state.set_player(old_player)


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
        from Game.steps import Step
        assert(all(isinstance(step, Step) for step in steps))

    def perform(self, game_state: GameState):
        for step in self.steps:
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

    def won(self):
        pass

    def lost(self):
        pass