from Game.game import GameState


class Filter:
    def filter(self, selected, game_state: GameState):
        pass


class TestFilter(Filter):
    def __init__(self, test):
        self.test = test

    def filter(self, selected, game_state: GameState):
        new_selected = []
        for item in selected:
            game_state.set_selected(item)
            if self.test.test(game_state):
                new_selected.append(item)
        return new_selected

    def __repr__(self):
        return "Test("+str(self.test)+")"


class TestOutFilter(Filter):
    def __init__(self, test_out):
        self.test_out = test_out

    def filter(self, selected, game_state):
        new_selected = self.test_out.filter(selected, game_state)
        return [s for s in selected if s not in new_selected]

    def __repr__(self):
        return "Not("+str(self.test_out)+")"


class RandomFilter(Filter):
    def __init__(self, count):
        self.count = count

    def filter(self, selected, game_state):
        import random
        return list(random.sample(selected, self.count))

    def __repr__(self):
        return "Random("+str(self.count)+")"
