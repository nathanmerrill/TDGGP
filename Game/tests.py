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
        left = self.obj1.select(game_state)
        right = self.obj2.select(game_state)
        assert(len(left) == 1)
        assert(len(right) == 1)
        try:
            return self.comparison(left[0], right[0])
        except:

            print([parent.get_attribute(self.obj1.attribute_name)
                  for parent in self.obj1.parent.select(game_state)
                  if parent.has_attribute(self.obj1.attribute_name)])
            print(type(self.obj1))
            print(self.obj1.select(game_state))
            print(self.obj1.parent.select(game_state))
            print(left[0])
            raise

    def __repr__(self):
        return str(self.obj1)+str(self.comparison)+str(self.obj2)


class TestExists(Test):
    def __init__(self, selector):
        self.selector = selector

    def test(self, game_state):
        return len(self.selector.select(game_state)) != 0

    def __repr__(self):
        return "Exists("+str(self.selector)+")"
