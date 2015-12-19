from Game.game import *
from Game import parser, randomplayer, manualplayer
from Game.steps import *
from fann2 import libfann
from Game.selectors import *
from typing import Sequence, List, Mapping, Union, Optional
import click, random, os, pickle

SCORER_FILE_SUFFIX = "-score.nn"
CHOICE_FILE_SUFFIX = "-choice.nn"
INPUT_MAPPER_FILE_SUFFIX = "-input.map"
OUTPUT_MAPPER_FILE_SUFFIX = "-output.map"


def create_neural_network(input_size: int, output_size: int) -> libfann.neural_net:
    network = libfann.neural_net()
    network.create_standard_array([input_size, (input_size+output_size)/2, output_size])
    return network


def load_or_create_neural_network(path: str, input_size: int, output_size: int) -> libfann.neural_net:
    if os.path.exists(path):
        network = libfann.neural_net()
        network.create_from_file(path)
    else:
        network = create_neural_network(input_size, output_size)
    return network


def save_mapper(path: str, mapper: Union["NeuralNetworkInput", "NeuralNetworkOutputMapper"]) -> None:
    with open(path, 'wb') as file:
        pickle.dump(mapper, file)


def read_mapper(path: str) -> Union["NeuralNetworkInput", "NeuralNetworkOutputMapper"]:
    with open(path, 'rb') as file:
        return pickle.load(file)


class LearningPlayer(Player):
    def __init__(self,
                 index: int,
                 input_mapper: "NeuralNetworkInput",
                 output_mapper: "NeuralNetworkOutputMapper",
                 scorer: libfann.neural_net,
                 chooser: libfann.neural_net):
        super(LearningPlayer, self).__init__(index)
        self.input = input_mapper
        self.output = output_mapper
        self.scorer = scorer
        self.chooser = chooser
        self.learning = False
        self.previous_choices = []
        self.previous_input = []
        self.previous_output = []
        self.previous_action = None  # type: Optional[int]
        self.exploration_rate = .1

    def select(self,
               choices: List[Union[GameObject, str]],
               min_choices: int,
               max_choices: int,
               game_state: GameState,
               current_action: int):
        # Generate input, get scores for each available choice
        input_array = self.input.generate(game_state, current_action)
        output_array = self.chooser.run(input_array)
        # Score current state, teach AI
        score = self.scorer.run(input_array)
        self.update_network(score[0])
        # Select choices
        if random.random() < self.exploration_rate:
            self.learning = False
            to_choose = random.sample(choices, random.randint(min_choices, max_choices))
        else:
            self.learning = True
            choice_scores = self.output.map(output_array, current_action)
            to_choose = self.choose_top_choices(choices, choice_scores, min_choices, max_choices)
            # Update History
            self.previous_choices = to_choose
            self.previous_input = input_array
            self.previous_output = output_array
            self.previous_action = current_action
        return to_choose

    def update_network(self, score: int):
        if self.learning:  # If not on first turn
            self.scorer.train(self.previous_input, [score])
            updated = self.output.new_output(self.previous_output, self.previous_choices, score, self.previous_action)
            self.chooser.train(self.previous_input, updated)

    @staticmethod
    def choose_top_choices(choices: Sequence[str], mapping: Mapping, min_choices: int, max_choices: int) -> List[str]:

        def get_mapping(obj):
            if type(obj) == str:
                return mapping[obj]
            return mapping[obj.name]
        try:
            sorted_choices = list(reversed(sorted(choices, key=get_mapping)))
        except KeyError:
            print(choices)
            print(mapping)
            raise
        if min_choices and get_mapping(sorted_choices[min_choices-1]) < .5:
            return sorted_choices[:min_choices]
        elif get_mapping(sorted_choices[max_choices-1]) > .5:
            return sorted_choices[:max_choices]
        else:
            for index in range(min_choices, max_choices):
                if get_mapping(sorted_choices[index]) > .5:
                    return sorted_choices[:index]
            return sorted_choices[:max_choices]

    def won(self) -> None:
        self.update_network(1)

    def lost(self) -> None:
        self.update_network(0)


def get_value_type(attribute):
    if type(attribute) in {bool, int} or isinstance(attribute, GameObject):
        return type(attribute)
    return attribute


def get_all_attributes(game):
    game_state = game.state
    attributes = {
        Collection: set(),
        Piece: set(),
        Player: set(),
        Turn: set(),
        Game: set(),
    }
    attribute_values = dict()
    for collection in game.collections.values():
        attributes[Collection].update(collection.attributes)
        for name, val in collection.attributes.items():
            attribute_values.setdefault((Collection, name), set()).add(get_value_type(val))
    for piece in game.pieces.values():
        attributes[Piece].update(piece.attributes)
        for name, val in piece.attributes.items():
            attribute_values.setdefault((Piece, name), set()).add(get_value_type(val))
    for action in game.actions.values():
        for step in action.steps:
            from Game.steps import AssignAttributeStep
            if type(step) == AssignAttributeStep:
                selected = step.assign_to_selector.select(game_state)[0]
                selector_type = Player if isinstance(selected, Player) else type(selected)
                attributes[selector_type].add(step.attribute_name)
                value_type = get_value_type(step.assign_selector.select(game_state)[0])
                attribute_values.setdefault((selector_type, step.attribute_name), set()).add(value_type)
    return attributes, attribute_values


def get_all_choice_steps(game):
    choice_step_types = {PlayerChoice, PlayerSelect}
    actions = list(game.actions.values())
    for action in game.actions.values():
        for step in action.steps:
            if isinstance(step, TestStep):
                if step.false:
                    actions.append(step.false.select_one(game.state))
                if step.true:
                    actions.append(step.true.select_one(game.state))
            elif isinstance(step, WhileStep):
                actions.append(step.action_selector.select_one(game.state))
            elif isinstance(step, RepeatStep):
                actions.append(step.action_selector.select_one(game.state))
            elif isinstance(step, ForEachStep):
                actions.append(step.action_selector.select_one(game.state))

    return sorted([step
                  for action in actions
                  for step in action.steps
                  if type(step) in choice_step_types],
                  key=lambda step: step.line_num)


class InputItem:
    def __init__(self, selector):
        self.selector = selector

    def generate(self, game_state: GameState) -> float:
        pass


class PlayerInputItem(InputItem):
    def generate(self, game_state: GameState):
        players = self.selector.select(game_state)
        if len(players) == 0:
            return 0
        return int(players[0] == game_state.player)


class StringInputItem(InputItem):
    def __init__(self, selector, string):
        super(StringInputItem, self).__init__(selector)
        self.string = string

    def generate(self, game_state: GameState):
        return int(self.selector.select_one_of_type(game_state, str) == self.string)


class GameObjectInputItem(InputItem):
    def __init__(self, selector, item_name):
        super(GameObjectInputItem, self).__init__(selector)
        self.item_name = item_name

    def generate(self, game_state: GameState):
        return int(self.selector.select_one(game_state).name == self.item_name)


class IntInputItem(InputItem):
    def generate(self, game_state: GameState):
        selected = self.selector.select(game_state)
        if len(selected) == 0:
            return 0
        value = selected[0]
        return value/(value+1)


class BooleanInputItem(InputItem):
    def generate(self, game_state: GameState):
        selected = self.selector.select(game_state)
        if len(selected) == 0:
            return .5
        return int(selected[0])


class GameObjectInputSet:
    def __init__(self, possible_options: list, selector: Selector):
        self.possible_options = dict((option.name, index)
                                     for index, option in enumerate(sorted(possible_options,
                                                                           key=lambda option: option.name)))
        self.selector = selector

    def generate(self, game_state: GameState):
        array = [0]*(len(self.possible_options)+1)
        selected = self.selector.select(game_state)
        if len(selected) == 0:
            array[-1] = 1
        else:
            array[self.possible_options[selected[0].name]] = 1

        return array


class AttributeInputSet:
    def __init__(self, game_object: Selector, game: Game, attributes: dict):
        self.array = []
        for name, values in sorted(attributes.items()):
            selector = AttributeSelector(name, game_object)
            for value in values:
                if value == int:
                    self.array.append(IntInputItem(selector))
                elif value == bool:
                    self.array.append(BooleanInputItem(selector))
                elif issubclass(value, Player):
                    self.array.append(PlayerInputItem(selector))
                elif type(value) == str:
                    self.array.append(StringInputItem(selector, value))
                else:
                    if value == Collection:
                        object_set = list(game.player_collections.values()) + \
                                     list(game.collections.values())
                    elif value == Piece:
                        object_set = game.pieces.values()
                    elif value == Turn:
                        object_set = game.turns.values()
                    elif value == Action:
                        object_set = game.actions.values()
                    else:
                        raise AssertionError("Bad state")
                    self.array.append(GameObjectInputSet(object_set, selector))

    def generate(self, game_state):
        array = []
        for item in self.array:
            generated = item.generate(game_state)
            if type(generated) == list:
                array.extend(generated)
            else:
                array.append(generated)
        return array


class StepInputSet:
    def __init__(self, steps):
        self.steps = dict((step.line_num, index) for index, step in enumerate(steps))

    def generate(self, current_action: int):
        array = [0]*len(self.steps)
        array[self.steps[current_action]] = 1
        return array


class CollectionInputSet:
    def __init__(self, collection_name, possible_attributes, game: Game, scope: ScopeSelector):
        self.selector = ContextSelector(collection_name, scope)
        self.attributes = AttributeInputSet(self.selector, game, possible_attributes)
        self.first_item = GameObjectInputSet(list(game.pieces.values()), ContextSelector("first", self.selector))
        self.piece_counts = dict((piece.name, index) for index, piece in sorted(enumerate(game.pieces.values())))

    def generate(self, game_state):
        collections = self.selector.select(game_state)
        array = []
        collection_size = []
        collection_pieces = [0]*len(self.piece_counts)
        for collection in collections:
            if collection.count_visible(game_state) or collection.all_visible(game_state):
                length = len(collection.pieces)
                collection_size.append(length/(length+1))
            if collection.all_visible(game_state):
                for piece in collection.pieces:
                    index = self.piece_counts[piece.name]
                    collection_pieces[index] = -1/(collection_pieces[index]-2)
        if len(collections) == 1:
            array.extend(self.first_item.generate(game_state))
            array.extend(self.attributes.generate(game_state))
        array.extend(collection_size)
        array.extend(collection_pieces)
        return array


class NeuralNetworkInput:
    def __init__(self, game: Game):
        attribute_names, attribute_values = get_all_attributes(game)
        self.possible_steps = StepInputSet(get_all_choice_steps(game))

        def attributes_of_class(class_type):
            return dict([(attribute_name, attribute_values[(class_type, attribute_name)])
                        for attribute_name in attribute_names[class_type]])
        self.game_attributes = AttributeInputSet(ScopeSelector("player"), game, attributes_of_class(Game))
        self.turn_attributes = AttributeInputSet(ScopeSelector("current_turn"), game, attributes_of_class(Turn))
        collection_scopes = {
            "game": game.collections,
            "player": game.player_collections,
            "opponents": game.player_collections
        }
        self.collections = [
            CollectionInputSet(collection, attributes_of_class(Collection), game, ScopeSelector(scope_name))
            for scope_name, collections in collection_scopes.items() for collection in collections
        ]
        self.input_length = len(self.generate(game.state, list(self.possible_steps.steps.keys())[0]))

    def generate(self, game_state, current_action) -> list:
        array = []
        array.extend(self.possible_steps.generate(current_action))
        array.extend(self.game_attributes.generate(game_state))
        array.extend(self.turn_attributes.generate(game_state))
        for collection in self.collections:
            array.extend(collection.generate(game_state))
        return array


class NeuralNetworkOutputMapper:
    def __init__(self, game: Game):
        choice_steps = get_all_choice_steps(game)
        self.mappings = dict()
        self.output_length = 0
        for choice in choice_steps:
            if isinstance(choice, PlayerSelect):
                self.mappings[choice.line_num] = None
            elif isinstance(choice, PlayerChoice):
                objects = list(sorted(choice.options.keys()))
                self.add_mapping(choice.line_num, objects)

    def add_mapping(self, line_number, objects):
        self.mappings[line_number] = ObjectMapping(objects, self.output_length)
        self.output_length += len(objects)

    def map(self, neural_output, current_action):
        mapping = self.mappings[current_action]
        assert(len(neural_output) == self.output_length)
        return dict(zip(mapping.objects, neural_output[mapping.start_index:]))

    def new_output(self, neural_output: list, chosen: list, new_value: float, past_action: int):
        mapping = self.mappings[past_action]
        chosen = set(chosen)
        new_values = [new_value if obj in chosen else neural_output[mapping.start_index+index]
                      for index, obj in enumerate(mapping.objects)]
        neural_output[mapping.start_index:mapping.start_index + len(new_values)] = new_values
        return neural_output

    def missing_mappings(self):
        return any(value is None for value in self.mappings.values())


class ObjectMapping:
    def __init__(self, objects, start_index):
        self.objects = objects
        self.start_index = start_index


class ExploratoryPlayer(Player):
    def __init__(self, index, output_mapper: NeuralNetworkOutputMapper):
        super(ExploratoryPlayer, self).__init__(index)
        self.output_mapper = output_mapper

    def select(self, choices: list, min_choices: int, max_choices: int, game_state: GameState, current_action: int):
        to_choose = random.sample(choices, random.randint(min_choices, max_choices))
        if self.output_mapper.mappings[current_action] is None:
            selection_type = type(choices[0])
            if selection_type == Piece:
                objects = list(game_state.game.pieces.values())
            elif selection_type == Collection:
                objects = list(game_state.game.collections.values())
                objects.extend(game_state.game.player_collections.values())
            else:
                raise AssertionError("Bad selection type")
            objects = [obj.name for obj in objects]
            objects.sort()
            self.output_mapper.add_mapping(current_action, objects)
        return to_choose


@click.command()
@click.option("--game_path", prompt="Game Path", help="Path to the game's XML")
@click.option("--num_iterations", prompt="Iterations", help="Number of times the AI should play itself", type=int)
@click.option("--refresh", default=False, help="Pass true if you want the AI to forget all previous learning")
def learn_game(game_path: str, num_iterations: int, refresh: bool):
    game = parser.parse_xml(game_path)
    game.start([randomplayer.RandomPlayer(0), randomplayer.RandomPlayer(1)])
    input_mapper_path = game.name + INPUT_MAPPER_FILE_SUFFIX
    input_mapper = NeuralNetworkInput(game) if refresh or not os.path.exists(input_mapper_path) \
        else read_mapper(input_mapper_path)
    output_mapper_path = game.name + OUTPUT_MAPPER_FILE_SUFFIX
    output_mapper = NeuralNetworkOutputMapper(game) if refresh or not os.path.exists(output_mapper_path) \
        else read_mapper(output_mapper_path)
    while output_mapper.missing_mappings():
        players = [ExploratoryPlayer(0, output_mapper), ExploratoryPlayer(1, output_mapper)]
        parser.parse_xml(game_path).start(players)
    chooser_path = game.name + CHOICE_FILE_SUFFIX
    chooser = create_neural_network(input_mapper.input_length, output_mapper.output_length) if refresh \
        else load_or_create_neural_network(chooser_path, input_mapper.input_length, output_mapper.output_length)
    scorer_path = game.name + SCORER_FILE_SUFFIX
    scorer = create_neural_network(input_mapper.input_length, 1) if refresh \
        else load_or_create_neural_network(scorer_path, input_mapper.input_length, 1)

    players = [
        LearningPlayer(0, input_mapper, output_mapper, scorer, chooser),
        manualplayer.ManualPlayer(1)
    ]
    wins = 0
    losses = 0

    def save():
        save_mapper(input_mapper_path, input_mapper)
        save_mapper(output_mapper_path, output_mapper)
        chooser.save(chooser_path)
        scorer.save(scorer_path)
    for i in range(int(num_iterations)):
        print("Game "+str(i))
        winners = parser.parse_xml(game_path).start(players)
        wins += int(all(isinstance(winner, LearningPlayer) for winner in winners))
        losses += int(not(any(isinstance(winner, LearningPlayer) for winner in winners)))
        if i % 100 == 0:
            save()
    print("Winners:"+str(wins))
    print("Losers:"+str(losses))
    save()


if __name__ == '__main__':
    learn_game()
