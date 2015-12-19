import random

num_iterations = 10000
history = 500
min_chance = .5
max_chance = .9

successes = [random.random() < min_chance + (i*(max_chance-min_chance) / num_iterations)
             for i in range(num_iterations)]

aggregate = [sum(successes[max(0,i-history):i])/min(history, i+1) for i in range(num_iterations)]

print("\n".join(str(a)+", "+str(b) for a, b in zip(aggregate, range(num_iterations))))

