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
    def test(self, game_state, item):
        pass


class TestComparison(Test):
    def __init__(self, obj1, comparison, obj2):
        self.comparison = comparison
        self.obj1 = obj1
        self.obj2 = obj2

    def test(self, game_state, selected):
        left = self.obj1.select(game_state, selected)
        right = self.obj2.select(game_state, selected)
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

    def test(self, game_state, selected):
        return len(self.selector.select(game_state, selected)) != 0

    def __repr__(self):
        return str(self.selector)
