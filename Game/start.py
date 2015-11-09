from Game import parser, manualplayer, learningplayer, randomplayer
import click

player_types = {
    'Human': manualplayer.ManualPlayer,
    'Random': randomplayer.RandomPlayer,
    'Learning': learningplayer.LearningPlayer,
}


@click.command()
@click.option("--game_path", prompt="Game Path", help="Path to the game's XML")
@click.option("--players", prompt="Num Players", help="Comma delimited list of players to play with. Allowed types: " +
                                                      ",".join(player_types.keys()))
def start(game_path, players):
    game = parser.parse_xml(game_path)
    all_players = [player_types[player](index) for index, player in enumerate(players.split(","))]
    game.start(all_players)

if __name__ == '__main__':
    start()