from Game import parser, players
import click

player_types = {
    'Human': players.ManualPlayer,
    'Random': players.RandomPlayer
}


@click.command()
@click.option("--game_path", prompt="Game Path", help="Path to the game's XML")
@click.option("--num_players", prompt="Num Players", help="Number of players to play with")
@click.option("--player_type", prompt="Player Type", help="Type of players to play with.  Allowed options: " +
                                                          ", ".join(player_types.keys()))
def start(game_path, num_players, player_type):
    game = parser.parse_xml(game_path)
    all_players = list(map(player_types[player_type], range(int(num_players))))
    game.start(all_players)

if __name__ == '__main__':
    start()