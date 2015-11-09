from Game.game import Player


class RandomPlayer(Player):
    def select(self, choices: list, min_choices: int, max_choices: int, *args):
        import random
        return random.sample(choices, random.randint(min_choices, max_choices))