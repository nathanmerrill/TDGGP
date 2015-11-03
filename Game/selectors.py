from Game.game import GameState
import operator
operators = {
    '+': operator.add,
    '-': operator.sub,
    '*': operator.mul,
    '/': operator.floordiv,
}


class Selector:
    def select(self, game_state: GameState) -> list:
        pass


class OperatorSelector(Selector):
    def __init__(self, left: Selector, op: operator, right: Selector):
        self.left = left
        self.right = right
        self.operator = operators[op]
        self.str = op

    def select(self, game_state: GameState):
        try:
            assert(len(self.left.select(game_state)) == 1)
            assert(len(self.right.select(game_state)) == 1)
            assert(type(self.right.select(game_state)[0]) == int)
            assert(type(self.left.select(game_state)[0]) == int)
            return [self.operator(self.left.select(game_state)[0], self.right.select(game_state)[0])]
        except:
            print("Test: "+str(self))
            print("Left: "+str(self.left.select(game_state)))
            print("Right: "+str(self.right.select(game_state)))
            raise

    def __repr__(self):
        return str(self.left) + self.str + str(self.right)


class ValueSelector(Selector):
    def __init__(self, value):
        assert(value is not None)
        self.value = value

    def select(self, game_state: GameState):
        return [self.value]

    def __repr__(self):
        return str(self.value)


class AttributeSelector(Selector):
    def __init__(self, attribute_name: str, parent: Selector):
        self.attribute_name = attribute_name
        self.parent = parent

    def select(self, game_state: GameState):
        try:
            return [parent.get_attribute(self.attribute_name)
                    for parent in self.parent.select(game_state)
                    if parent.has_attribute(self.attribute_name)]
        except:
            print("Self: "+str(self))
            print("Selected: "+str(self.parent.select(game_state)))
            raise

    def __repr__(self):
        return str(self.parent)+"@"+self.attribute_name


class SizeSelector(Selector):
    def __init__(self, parent: Selector):
        self.parent = parent

    def select(self, game_state: GameState):
        return [len(self.parent.select(game_state))]

    def __repr__(self):
        return str(self.parent)+":count"


class ContextSelector(Selector):
    def __init__(self, context_name: str, parent: Selector):
        self.context_name = context_name
        self.parent = parent

    def select(self, game_state: GameState):
        try:
            return [child
                    for parent in self.parent.select(game_state)
                    for child in parent[self.context_name]]
        except:
            print("Self: "+str(self))
            print("Context: "+self.context_name)
            print("Selected: "+str(self.parent.select(game_state)))
            raise

    def __repr__(self):
        return str(self.parent)+":"+self.context_name


class ScopeSelector(Selector):
    def __init__(self, scope: str):
        self.scope = scope

    def select(self, game_state: GameState):
        return game_state.get_scopes(self.scope)

    def __repr__(self):
        return self.scope


class VariableSelector(Selector):
    def __init__(self, variable_name: str):
        self.variable_name = variable_name

    def select(self, game_state: GameState):
        return game_state.get_var(self.variable_name)

    def __repr__(self):
        return "$"+self.variable_name


class SelectedSelector(Selector):
    def select(self, game_state: GameState):
        return [game_state.get_selected()]

    def __repr__(self):
        return "selected"
