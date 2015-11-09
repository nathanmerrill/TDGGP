from Game.game import Player, GameState, Visibility


class ManualPlayer(Player):
    def select(self, choices: list, min_choices: int, max_choices: int, game_state: GameState, current_action: int):
        input(self.name)
        choices = sorted(choices, key=lambda k: k.name)
        chosen = []
        while True:
            if min_choices == max_choices or (min_choices == 0 and max_choices == 1):
                print("Select "+str(min_choices if min_choices else 1)+" of the following:")
            else:
                print("Select "+str(min_choices if min_choices else 1)+" to "+str(max_choices)+" of the following:")
            print(game_object_str(game_state.turns[-1]))
            print("\t-1: Print game state")
            if min_choices == 0:
                print("\t0: None")
            for index, choice in enumerate(choices):
                print("\t"+str(index+1)+": "+print_obj(choice, game_state))
            if max_choices == 1:
                print("Enter choice: ")
            elif min_choices > 1:
                print("Enter choices, separated by comma: ")
            else:
                print("Enter choice(s), separated by comma: ")
            while True:
                chosen = list(map(int, input().split(",")))
                if len(chosen) is not 1:
                    if -1 in chosen or 0 in chosen:
                        print("Invalid input.")
                        continue
                if -1 in chosen or 0 in chosen:
                    break
                elif len(chosen) < min_choices or len(chosen) == 0:
                    print("Selected too few items, you need at least "+str(min_choices))
                    continue
                elif len(chosen) > max_choices:
                    print("Selected too many items, you can have at most "+str(max_choices))
                    continue
                break
            if -1 in chosen:
                print(print_obj(game_state.game, game_state))
                continue
            if 0 in chosen:
                chosen = []
                break
            else:
                chosen = [choices[choice-1] for choice in chosen]
                break
        return chosen


def print_obj(obj, game_state):
    from Game.game import Collection, Player, Game
    if type(obj) is Collection:
        return collection_str(obj, game_state)
    elif type(obj) is Player:
        return player_str(obj, game_state)
    elif type(obj) is Game:
        return game_str(obj, game_state)
    else:
        return game_object_str(obj)


def game_str(game, game_state):
    string = game_object_str(game)
    string += "\n\t" + game_object_str(game_state.turns[-1])
    for collection in game.collections.values():
        string += tabify_str(collection_str(collection, game_state))
    for player in game.players:
        string += tabify_str(player_str(player, game_state))
    return string


def tabify_str(string):
    return "\n\t"+"\n\t".join(string.split("\n"))


def player_str(player, game_state):
    string = game_object_str(player)
    for collection in player.collections.values():
        string += tabify_str(collection_str(collection, game_state))
    return string


def collection_str(collection, game_state):
    string = game_object_str(collection)
    if is_visible(collection.visible_count, collection, game_state):
        string += " Count: "+str(len(collection.pieces))
    if is_visible(collection.visible_all, collection, game_state):
        if len(collection.pieces):
            string += "\n\t"+"\n\t".join(game_object_str(piece) for piece in collection.pieces)
    elif is_visible(collection.visible_top, collection, game_state) and len(collection.pieces):
        string += " Top: "+game_object_str(collection.pieces[0])
    return string


def is_visible(visibility, collection, game_state):
    return visibility == Visibility.Player or visibility == Visibility.Public or \
           (visibility == Visibility.Owner and collection in game_state.player.collections.values())


def game_object_str(obj):
    return obj.name + ("["+", ".join(key+"="+str(val) for key, val in
                                     sorted(obj.attributes.items(), key=lambda k: k[0]))+"]" if obj.attributes else "")
