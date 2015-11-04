import operator

comparisons = {
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
    "=": operator.eq,
    "!=": operator.ne,
}


class Test:
    def test(self, game_state):
        pass


class TestComparison(Test):
    def __init__(self, obj1, comparison, obj2):
        self.comparison = comparison
        self.obj1 = obj1
        self.obj2 = obj2

    def test(self, game_state):
        if str(self) == "$card@points=garden":
            print("Hi")
        left = self.obj1.select(game_state)
        right = self.obj2.select(game_state)
        if len(left) == 0 or len(right) == 0:
            return False
        assert(len(left) == 1), str(self.obj1) + " returned "+str(len(left))+" objects: " + str(left)
        assert(len(right) == 1), str(self.obj2) + " returned "+str(len(left))+" objects: " + str(right)
        return self.comparison(left[0], right[0])

    def __repr__(self):
        return str(self.obj1)+str(self.comparison)+str(self.obj2)


class TestExists(Test):
    def __init__(self, selector):
        self.selector = selector

    def test(self, game_state):
        return len(self.selector.select(game_state)) != 0

    def __repr__(self):
        return "Exists("+str(self.selector)+")"
