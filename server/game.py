import random
from collections import defaultdict
from itertools import chain
import time
import copy 

class Game: 

    grid_width = 11
    grid_height = 11
    cell_width = 50
    game_types = ["local", "online"]

    initial_state = {  
        0: {"spawn_pos": (5,0), "num_pieces": [1,1,1,1,1,1], "num_placements": 3, "snake_dict": defaultdict(list), "piece_dict": defaultdict(list)},
        1: {"spawn_pos": (5,0), "num_pieces": [1,1,1,1,1,1], "num_placements": 3, "snake_dict": defaultdict(list), "piece_dict": defaultdict(list)} 
    }

    def __init__(self, user_id, game_type_, players_):
        self.game_type = game_type_
        self.users = {
            user_id: User(players_)
        }
        self.game_state = GameState(copy.deepcopy(Game.initial_state)) 
        self.state_history = []
        self.winner = None
        self.win_type = None
        self.rounds = 0
        self.player_turn = 0 

    def to_dict(self):
        return {
            "game_state": self.game_state.get_data(), 
            "state_history": self.state_history,
            "winner": self.winner,
            "win_type": self.win_type,
            "rounds": self.rounds,
            "player_turn": self.player_turn
        }
    
    def run_action(self, action):
        if not self.winner is None:
            return 
        
        self.game_state.run_action(self.player_turn, action)
        #TODO: Update state_history after every action

        self.winner = self.game_state.get_winner()
        if not self.winner is None:
            self.win_type = "Capture"
        if self.game_state.turn_over(self.player_turn): 
            self.player_turn += 1
            if self.player_turn == 2: 
                self.player_turn = 0
                self.rounds += 1 
            self.game_state.start_turn(self.player_turn)

    def back_one_step(self):
        '''
        This method, when called, will set the game_state of the current game being played 
        back by one GameState in the state_history 
        '''

        if self.state_history:
            self.state_history.pop()
            if self.state_history: 
                self.game_state = self.state_history[-1][0].get_copy()
                self.player_turn = self.state_history[-1][1]
            else:
                self.game_state = GameState(copy.deepcopy(Game.initial_state))
                self.player_turn = 0
            print(f"Went back to move {len(self.state_history)}")
        else:
            print("Cannot go back further")
    
    def get_game_state(self): 
        return self.game_state
    
    def game_full(self):
        if self.game_type == "local": 
            return True
        return len(self.users) == 2
    
    def add_user(self, user_id, player):
        self.users[user_id] = User(player)

    def user_disconnect(self, user_id):
        self.users[user_id].disconnected = True
        if not self.winner and len(self.users) > 1:
            self.winner = self.get_other_user(user_id).players[0]
            self.win_type = "Forfeit"
    
    def get_other_user(self, user_id):
        other_id = set(self.users.keys()) - {user_id}
        return self.users[other_id.pop()]

    def valid_search_pos(pos): 
        return pos[0] >= 0 and pos[0] <= Game.grid_width-1 and pos[1] >= 0 and pos[1] <= Game.grid_height-1

    def grid_search(pos, grid): 
        return grid[Game.pos_to_grid_index(pos)]
    
    def pos_to_grid_index(pos): 
        return pos[0]*Game.grid_height+pos[1]
    
    def grid_index_to_pos(indx): 
        return (indx//Game.grid_height, indx%Game.grid_height)
    
    def coords_to_grid_pos(coords): 
        return (coords[0]//Game.cell_width, coords[1]//Game.cell_width)
    
class User:
    def __init__(self, players_):
        self.players = players_
        self.last_connection = time.time()
        self.disconnected = False

class GameState:
    '''
    A GameState class contains a dictionary of dictionaries called entire_state that holds all the state data of a game. 
    It has the format: 
    entire_state = {  
        player: {"spawn_pos": (x,y), "num_pieces": int, "num_placements": int, "snake_dict": defaultdict(list), "piece_dict": defaultdict(list)},
        player: {"spawn_pos": (x,y), "num_pieces": int, "num_placements": int, "snake_dict": defaultdict(list), "piece_dict": defaultdict(list)} 
    } 
    where, 
    "snake_dict": {snake_id: [piece1, piece2, piece3], ...}
    "piece_dict": {piece1: [value, is_active, snake_id], ...}

    It is important to note that location data is stored relative to each player. For this reason, players 
    have the same spawn and can have overlapping pieces. This also means a transformation is performed 
    every time a player gets the position of enemy pieces.  

    A GameState class has many methods such as run_action and get_actions that manipulate and derive info from state data. 
    '''

    placements_per_turn = 3

    def __init__(self, entire_state): 
        self.entire_state = entire_state

    def __getitem__(self, key): 
        if key in self.entire_state: 
            return self.entire_state[key]
        else: 
            raise KeyError(f"Key '{key}' not found.")
    
    #Get Actions
    def get_actions_ls(self, player):
        actions = self.get_actions(player)
        actions_ls = []
        for snake in actions: 
            actions_ls.extend(actions[snake])

        return actions_ls

    def get_actions(self, player):
        '''
        This method takes a player and returns the legal actions of each of their snakes 
        Args: 
            player (int): either player 0 or player 1
        Returns: 
            dict: the legal actions of each snake belonging to the player  
        '''

        actions = defaultdict(list)
        player_state = self.entire_state[player]
        snakes = list(player_state["snake_dict"].keys()) + [-1]

        for snake in snakes: 
            actions[snake].extend(self.get_snake_actions(snake, player))

        return actions
    
    def get_snake_actions(self, snake, player): 
        player_state = self.entire_state[player]
        actions = []
        if snake == -1: 
            if player_state["spawn_pos"] not in player_state["piece_dict"] and len(player_state["num_pieces"]) > 0 and player_state["num_placements"] > 0: 
                return [Actions.get_placement_code(player_state["spawn_pos"])]
            else: 
                return []
        if len(player_state["num_pieces"]) > 0 and player_state["num_placements"] > 0: 
            actions.extend(self.get_snake_placements(snake, player))
        if Snake.is_active(player_state["snake_dict"][snake], player_state["piece_dict"]): 
            actions.extend(self.get_snake_movements(snake, player))
            actions.extend(self.get_snake_rolls(snake, player))
        return actions

    def get_snake_movements(self, snake, player): 
        snake_pieces, piece_dict, enemy_pieces = self.entire_state[player]["snake_dict"][snake], self.entire_state[player]["piece_dict"], self.enemy_piece_dict((player+1)%2)
        movements = [] 
        if Snake.num_inactive(snake_pieces, piece_dict) != 1: 
            return movements

        for piece_to_move in snake_pieces: 
            if len(Piece.get_connections(piece_to_move, snake_pieces)) == 1: 
                perimeter = list(set(chain.from_iterable([Piece.get_non_connections(piece, snake_pieces) for piece in snake_pieces if piece != piece_to_move])))
                legal_move_positions = [pos for pos in perimeter if pos not in enemy_pieces or piece_dict[piece_to_move][0] >= enemy_pieces[pos][0]]
                movements.extend(Actions.get_movement_codes(piece_to_move, legal_move_positions))
        return movements  

    def get_snake_rolls(self, snake, player): 
        snake_pieces, piece_dict = self.entire_state[player]["snake_dict"][snake], self.entire_state[player]["piece_dict"]
        return Actions.get_roll_codes([piece for piece in snake_pieces if not piece_dict[piece][1]])

    def get_snake_placements(self, snake, player): 
        player_state = self.entire_state[player]
        if player_state["spawn_pos"] in player_state["snake_dict"][snake]: 
            snake_pieces, enemy_pieces = self.entire_state[player]["snake_dict"][snake], self.enemy_piece_dict((player+1)%2)
            return Actions.get_placement_codes(Snake.get_empty_perimeter(snake_pieces, enemy_pieces))
        else: 
            return []

    #Make Actions
    def run_action(self, player, action): 
        '''
        This method takes a player and action and will change the state data to reflect the action taken
        Args: 
            player (int): either player 0 or player 1
            action (str): encodes the action being taken 
        '''

        action_decode = action.split("-")
        type = action_decode[0]
        if type == "p": 
            self.place_piece((int(action_decode[1]), int(action_decode[2])), player)
        if type == "m":
            self.move_piece((int(action_decode[1]), int(action_decode[2])), (int(action_decode[3]), int(action_decode[4])), player)
        if type == "r":  
            self.roll_piece((int(action_decode[1]), int(action_decode[2])), None, player)
        if type == "dr": 
            self.roll_piece((int(action_decode[1]), int(action_decode[2])), int(action_decode[3]), player) 

    def roll_piece(self, pos, value, player): 
        piece_dict = self.entire_state[player]["piece_dict"]
        if not value: 
            value = random.randint(1, 6)
        piece_dict[pos][0] = value
        piece_dict[pos][1] = True
        self.check_matching_values(piece_dict[pos][2], player)

    def move_piece(self, to_move, move_loc, player): 
        piece_dict, enemy_pieces = self.entire_state[player]["piece_dict"], self.enemy_piece_dict((player+1)%2)
        
        to_move_val = piece_dict[to_move][0]
        if move_loc in enemy_pieces: 
            self.remove_piece(Piece.reflected(move_loc), (player+1)%2)
        self.add_piece(move_loc, to_move_val, player)
        self.remove_piece(to_move, player)
        self.make_snake_inactive(piece_dict[move_loc][2], player)

    def place_piece(self, position, player): 
        player_state, piece_dict = self.entire_state[player], self.entire_state[player]["piece_dict"] 
        player_state = self.entire_state[player]
        val = player_state["num_pieces"].pop(0)
        self.add_piece(position, val, player)
        player_state["num_placements"] -= 1

        if player_state["spawn_pos"] in piece_dict:
            self.check_matching_values(piece_dict[player_state["spawn_pos"]][2], player)

    def start_turn(self, player):
        self.activate_pieces(player)
        self.check_all_matching_snakes(player)
        self.entire_state[player]["num_placements"] = GameState.placements_per_turn

    def check_all_matching_snakes(self, player): 
        snake_dict = self.entire_state[player]["snake_dict"]
        for snake in snake_dict: 
            self.check_matching_values(snake, player)

    def activate_pieces(self, player): 
        piece_dict = self.entire_state[player]["piece_dict"]
        for piece in piece_dict: 
            piece_dict[piece][1] = False 

    def check_matching_values(self, snake, player): 
        player_state, snake_pieces, piece_dict = self.entire_state[player], self.entire_state[player]["snake_dict"][snake], self.entire_state[player]["piece_dict"] 
        if piece_dict[snake_pieces[0]][0] == 1 or len(snake_pieces) == 1: 
            return 
        all_matching = all([piece_dict[piece][0] == piece_dict[snake_pieces[0]][0] for piece in snake_pieces])
        if all_matching: 
            if len(player_state["num_pieces"]) < 9:
                player_state["num_pieces"].append(piece_dict[snake_pieces[0]][0])
            for piece in snake_pieces: 
                piece_dict[piece][0] = 1 
                piece_dict[piece][1] = True

    def make_snake_inactive(self, snake, player): 
        snake_pieces, piece_dict = self.entire_state[player]["snake_dict"][snake], self.entire_state[player]["piece_dict"]
        for piece in snake_pieces: 
            piece_dict[piece][1] = True

    def add_piece(self, pos, val, player): 
        '''
        This method takes the position and value of a peice and adds it to the data of a given player  
        Args: 
            pos (tuple): (x, y) position on board 
            val (int): value of piece 
            player (int): either player 0 or player 1
        '''

        snake_dict, piece_dict = self.entire_state[player]["snake_dict"], self.entire_state[player]["piece_dict"]
        connected_snakes = Piece.get_connected_snakes(pos, piece_dict) 

        #create parent snake 
        snake_id = Snake.get_unique_id() if not connected_snakes else Snake.get_combined_snakes(connected_snakes, snake_dict, piece_dict) 

        #add piece to the snake and piece dictionaries
        snake_dict[snake_id].append(pos)
        piece_dict[pos] = [val, False, snake_id]

    def remove_piece(self, pos, player): 
        '''
        This method takes the position of a peice and removes it from the data of a given player  
        Args: 
            pos (tuple): (x, y) position on board 
            player (int): either player 0 or player 1
        '''

        snake_dict, piece_dict = self.entire_state[player]["snake_dict"], self.entire_state[player]["piece_dict"]
        if pos not in piece_dict: 
            return 
        connections = Piece.get_connections(pos, piece_dict)
        snake_id_to_remove = piece_dict[pos][2] 

        #remove piece 
        snake_dict[snake_id_to_remove].remove(pos)
        piece_dict.pop(pos)

        #handle split snakes 
        if len(connections) >= 2:
            while connections: 
                snake_id = Snake.get_unique_id()
                snake_pieces = []
                Snake.snake_search(connections[0], visited=snake_pieces, to_search=snake_dict[snake_id_to_remove], to_find=connections, snake_id=snake_id, piece_dict=piece_dict)
                snake_dict[snake_id] = snake_pieces
            snake_dict.pop(snake_id_to_remove)
        elif Snake.is_empty(snake_id_to_remove, snake_dict): 
            snake_dict.pop(snake_id_to_remove)

    #Game features
    def get_winner(self): 
        for player in self.entire_state: 
            if self.no_actions(player) or self.spawn_occupied(player): 
                return (player+1)%2
        return None 

    def spawn_occupied(self, player):
        spawn_pos, enemy_pieces = self.entire_state[player]["spawn_pos"], self.enemy_piece_dict((player+1)%2)
        return spawn_pos in enemy_pieces
    
    def spawn_self_occupied(self, player):
        spawn_pos, piece_dict = self.entire_state[player]["spawn_pos"], self.entire_state[player]["piece_dict"]
        return spawn_pos in piece_dict

    def turn_over(self, player): 
        snake_dict, piece_dict = self.entire_state[player]["snake_dict"], self.entire_state[player]["piece_dict"]
        an_active_snake = any([Snake.is_active(snake_pieces, piece_dict) for snake_pieces in snake_dict.values()])
        return len(snake_dict) > 0 and not an_active_snake
    
    def no_actions(self, player): 
        snake_dict, num_pieces = self.entire_state[player]["snake_dict"], self.entire_state[player]["num_pieces"]
        longest_snake = max([len(snake_pieces) for snake_pieces in snake_dict.values()]) if snake_dict else 0
        return len(num_pieces) == 0 and longest_snake <= 1 
    
    def get_total_pieces(self, player): 
        return len(self.entire_state[player]["piece_dict"])+len(self.entire_state[player]["num_pieces"])
    
    def get_num_immobile_snakes(self, player): 
        num_immobile = 0
        for snake_pieces in self.entire_state[player]["snake_dict"].values():
            if Snake.is_immobile(snake_pieces, self.entire_state[player]["piece_dict"]): 
                num_immobile += 1
        return num_immobile
    
    #Create States 
    def get_board_piece_state(self, player): 
        '''
        This method takes a player and returns a 1-dim list of the values of every peice in the game. 
        It also adds the "num_pieces" of each player to the end of this list. 
        Args: 
            player (int): either player 0 or player 1
        '''

        state = []
        state.extend(self.get_board_state(player))
        state.extend([self.entire_state[player]["num_pieces"], self.entire_state[(player+1)%2]["num_pieces"]])
        return state
    
    def get_board_state(self, player): 
        '''
        This method takes a player and returns a 1-dim list of the values of every peice in the game. 
        Enemy pieces are represented as positive while a given player pieces are negative 
        Args: 
            player (int): either player 0 or player 1
        '''

        player_pieces, enemy_pieces = self.entire_state[player]["piece_dict"], self.enemy_piece_dict((player+1)%2)
        grid = [0]*(Game.grid_width*Game.grid_height)
        for piece, data in player_pieces.items(): 
            grid[Game.pos_to_grid_index(piece)] = -data[0]
        for piece, data in enemy_pieces.items(): 
            grid[Game.pos_to_grid_index(piece)] = data[0]
        return grid

    def generate_successor(self, player, action):
        '''
        This method takes a player and action and will change the state data to reflect the action taken + 
        return a deep copy of that new game state 
        Args: 
            player (int): either player 0 or player 1
            action (str): encodes the action being taken 
        Returns: 
            new_state (obs): GameState object with changed data 
        '''
        
        new_state = GameState(self.get_data_copy())
        new_state.run_action(player, action)
        return new_state
        
    #Helpful Methods 
    def get_data(self):
        return self.entire_state
    
    def get_copy(self):
        return GameState(self.get_data_copy())
    
    def get_data_copy(self): 
        return copy.deepcopy(self.entire_state)

    def get_player_data(self, player):
        return self.entire_state[player]
    
    def get_player_from_pos(self, pos): 
        for player in self.entire_state:
            if pos in self.entire_state[player]["piece_dict"]:
                return player
        return None
    
    def enemy_piece_dict(self, player): 
        '''
        This method takes an enemy player and performs a geometric reflection to get the accurate location of their pieces 
        Args: 
            player (int): either player 0 or player 1 
        Returns: 
            reflected_piece_dict (dict): player pieces that have been geometrically reflected 
        '''

        reflected_piece_dict = defaultdict(list)
        for piece in self.entire_state[player]["piece_dict"]: 
                new_piece = Piece.reflected(piece)
                reflected_piece_dict[new_piece] = self.entire_state[player]["piece_dict"][piece]
        return reflected_piece_dict
    
    def pos_empty(self, player, pos): 
        return pos not in self.entire_state[player]["piece_dict"]

class Snake: 
    snake_id = 0 

    def get_combined_snakes(ids_to_connect, snake_dict, piece_dict):
        if not ids_to_connect: 
            return None 
        if len(ids_to_connect) == 1:
            return ids_to_connect[0]
        
        # add pieces from all combined snakes to the first snake, 
        # reassign snake_ids of pieces, and remove every snake except the first 
        for id in ids_to_connect[1:]: 
            for piece in snake_dict[id]: 
                snake_dict[ids_to_connect[0]].append(piece)
                piece_dict[piece][2] = ids_to_connect[0]
            snake_dict.pop(id)
        
        return ids_to_connect[0] 
    
    def snake_search(pos, visited, to_search, to_find, snake_id, piece_dict):
        visited.append(pos)
        if pos in to_find:
            to_find.remove(pos)
        piece_dict[pos][2] = snake_id
        for piece in Piece.get_connections(pos, to_search):
            if piece not in visited: 
                Snake.snake_search(piece, visited, to_search, to_find, snake_id, piece_dict)

    def get_unique_id():
        Snake.snake_id += 1
        return Snake.snake_id 
    
    def get_perimeter(snake_pieces): 
        return list(set(chain.from_iterable([Piece.get_non_connections(piece, snake_pieces) for piece in snake_pieces]))) 

    def get_empty_perimeter(snake_pieces, enemy_pieces): 
        return list(set(chain.from_iterable([Piece.get_empty_adjacent(piece, snake_pieces, enemy_pieces) for piece in snake_pieces]))) 

    def is_immobile(pieces, piece_dict): 
        if len(pieces) < 4: 
            return False
        for piece in pieces: 
            if Piece.is_immobile(piece, piece_dict): 
                return True
        return False

    def is_active(pieces, piece_dict): 
        if len(pieces) == 1: 
            return not piece_dict[pieces[0]][1]
        else:
            return sum([piece_dict[piece][1] for piece in pieces]) < 2 
    
    def num_inactive(pieces, piece_dict):
        return sum([piece_dict[piece][1] for piece in pieces])

    def get_pieces_from_pos(pos, snake_dict, piece_dict): 
        return snake_dict[piece_dict[pos][2]]

    def is_empty(snake_id, snake_dict): 
        return len(snake_dict[snake_id]) == 0 

class Piece:
    rel_edge_positions = [(1,0), (-1,0), (0,1), (0,-1)]
    rel_corner_positions = [[(1,0), (0,1), (1,1)], [(1,0), (0,-1), (-1,-1)], [(-1,0), (0,1), (-1,1)], [(-1,0), (0,-1), (-1,-1)]]

    def is_immobile(pos, pieces): 
        for corner in Piece.rel_corner_positions: 
            if all([(pos[0]+rel_pos[0], pos[1]+rel_pos[1]) in pieces for rel_pos in corner]):
                return True 
        return False

    def reflected(piece):
        x_line = Game.grid_height//2
        y_line = Game.grid_width//2
        return (2*x_line-piece[0], 2*y_line-piece[1]) 

    def get_connected_snakes(pos, pieces): 
        return list(set([pieces[(pos[0]+rel_edge[0], pos[1]+rel_edge[1])][2] for rel_edge in Piece.rel_edge_positions if (pos[0]+rel_edge[0], pos[1]+rel_edge[1]) in pieces]))

    def get_connections(pos, pieces): 
        return [(pos[0]+rel_edge[0], pos[1]+rel_edge[1]) for rel_edge in Piece.rel_edge_positions if (pos[0]+rel_edge[0], pos[1]+rel_edge[1]) in pieces]
        
    def get_non_connections(pos, pieces):
        return [(pos[0]+rel_edge[0], pos[1]+rel_edge[1]) for rel_edge in Piece.rel_edge_positions if Game.valid_search_pos((pos[0]+rel_edge[0], pos[1]+rel_edge[1])) and (pos[0]+rel_edge[0], pos[1]+rel_edge[1]) not in pieces]

    def get_empty_adjacent(pos, pieces1, pieces2): 
        return [(pos[0]+rel_edge[0], pos[1]+rel_edge[1]) for rel_edge in Piece.rel_edge_positions if Game.valid_search_pos((pos[0]+rel_edge[0], pos[1]+rel_edge[1])) and (pos[0]+rel_edge[0], pos[1]+rel_edge[1]) not in pieces1 and (pos[0]+rel_edge[0], pos[1]+rel_edge[1]) not in pieces2]

    def get_adjacent(pos): 
        return [(pos[0]+rel_edge[0], pos[1]+rel_edge[1]) for rel_edge in Piece.rel_edge_positions if Game.valid_search_pos((pos[0]+rel_edge[0], pos[1]+rel_edge[1]))]

class Actions:

    def get_movement_code(pos1, pos2): 
        return "m"+"-"+str(pos1[0])+"-"+str(pos1[1])+"-"+str(pos2[0])+"-"+str(pos2[1])

    def get_movement_codes(to_move, locations):
        return [Actions.get_movement_code(to_move, loc) for loc in locations]
    
    def get_placement_code(pos): 
        return "p"+"-"+str(pos[0])+"-"+str(pos[1])

    def get_placement_codes(cells): 
        return [Actions.get_placement_code(cell) for cell in cells]

    def get_roll_code(pos): 
        return "r"+"-"+str(pos[0])+"-"+str(pos[1])

    def get_roll_codes(cells):
        return [Actions.get_roll_code(cell) for cell in cells]
    
    def get_droll_code(pos, val): 
        return "dr"+"-"+str(pos[0])+"-"+str(pos[1])+"-"+str(val)
    
    def get_droll_codes(roll_code): 
        action_decode = roll_code.split("-")
        type = action_decode[0]
        pos = (int(action_decode[1]), int(action_decode[2]))

        return [Actions.get_droll_code(pos, val) for val in range(1,7)]
   