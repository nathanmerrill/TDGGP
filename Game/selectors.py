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

    def select_one(self, game_state: GameState):
        item = self.select(game_state)
        assert(len(item) == 1), str(self)+" selected "+str(len(item))+" items"
        return item[0]

    def select_one_of_type(self, game_state: GameState, item_type):
        item = self.select_one(game_state)
        assert(isinstance(item, item_type)), \
            str(self) + " selected item of type " + str(type(item)) + " instead of " + str(item_type)
        return item


class OperatorSelector(Selector):
    def __init__(self, left: Selector, op: operator, right: Selector):
        self.left = left
        self.right = right
        self.operator = operators[op]
        self.str = op

    def select(self, game_state: GameState):
        left_selected = self.left.select_one(game_state)
        right_selected = self.right.select_one(game_state)
        assert(type(left_selected) == type(right_selected)), \
            str(self.left) + " did not match type with "+str(self.right) \
            + ": " + str(type(left_selected)) + " vs " + str(type(right_selected)) \
            + " Left value: "+str(left_selected)+" Right value: "+str(right_selected)
        return [self.operator(left_selected, right_selected)]

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
        assert(self.context_name[0] not in ("$", ":", "@"))
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
