import cProfile
from Game import start

players = [x(index) for index, x in enumerate([start.player_types["Random"]]*2)]
profiler = cProfile.Profile()
profiler.enable()
start.run_game("../games/dominion.xml", players)
profiler.disable()
profiler.print_stats(sort="time")