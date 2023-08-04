import socket
import threading
import time

# Server Class
class Server:
    def __init__(self, host, port, max_players): 
        # Initializes various server-related variables
        self.confirmed_grid = [] # Stores confirmed grid information, where each grid is represented as a tuple (row, column, id) indicating the row, column, and player ID.
        self.locked_grid = [] # Stores locked grid information, used for handling concurrent access.
        self.surface_list = [] # Saves the ID of the corresponding player based on the name
        self.players_id = {} # Saves whether the corresponding player is online or not according to the name
        self.is_connect = {}    
        self.host = host # The address and port on which the server listens.
        self.port = port
        self.max_players = max_players # The maximum number of players the game supports.
        self.players = [] # The current list of connected players, where each player is represented as a dictionary containing ID, socket, address, and color information.
        self.lock = threading.Lock()
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((host, port))
        self.server_socket.listen(max_players) # Creates a server socket listening on the specified address and port.

    def start(self):
        """
        - Starts the server and waits for player connections.
        - Accepts new connections as long as the number of connected players is less than the specified maximum player count.
        - Creates new threads to handle each player's messages and requests.
        """
        print("Server is up, waiting for players to connect...")
        while len(self.players) < self.max_players:
            client_socket, client_address = self.server_socket.accept()
            # Get the name of the player

            data = client_socket.recv(2048)
            player_name = data.decode()
            print("At start: The player name is: "+str(player_name))

            # Player Connected
            if player_name in self.is_connect and self.is_connect[player_name]:
                print(f"Player {player_name}({self.players_id[player_name]}) is connected.")
                # Send a connected message to the client
                client_socket.send("CONNECTED".encode())
                continue
            if player_name not in self.is_connect:
                if len(self.players) == self.max_players:
                    client_socket.send("FULL".encode())
                    continue

                # If it's a newly created player
                player_id = len(self.players) + 1
                player = {
                    "id": player_id,
                    "player_name": player_name,
                    "name": 'Player_%d'%player_id,
                    "socket": client_socket,
                    "address": client_address,
                    "color": player_id
                }
                self.players_id[player_name] = player_id
                self.players.append(player)
                print(f"Player {player_name}({player_id}) Created Successfully.")
            else:
                # Player created but reconnected after disconnection
                player_id = self.players_id[player_name]
                self.set_player_socket(player_id, client_socket, client_address)
                print(f"Player {player_name}({player_id}) reconnected.")
            self.is_connect[player_name] = True
            print(f"Player {player_id} connected Successfully.")
            threading.Thread(target=self.handle_player, args=(player_name,)).start()

    def update_and_send_player_list(self):
        """
        - Assembles and sends the current player list to all connected players.
        """
        player_list_message = "PLAYERLIST,|"
        for player in self.players:
            player_list_message += f"{player['id']}-{player['color']}-{player['player_name']}|"
        player_list_message = player_list_message[:-1]  # Remove the trailing comma
        for player in self.players:
            if not self.is_connect[player["player_name"]]:
                continue
            player["socket"].send(player_list_message.encode())

    def grid_remove(self,id):
        """
        - Removes locked grid information for a given player ID.
        """
        if len(self.locked_grid) > 0 :
            self.locked_grid = [cell for cell in self.locked_grid if cell[2] != id]

    def grid_check(self,row,column,id):
        """
        - Checks if a grid can be locked to avoid multiple players accessing the same grid simultaneously.
        """
        print("the start confirmed_list" + str(self.confirmed_grid))
        print("the start locked_list:" + str(self.locked_grid))
        new_cell = (row, column, id)
        self.grid_remove(id)

        flag = True

        for cell in self.locked_grid:
            if cell[0] == row and cell[1] == column:
                flag = False
        for cell in self.confirmed_grid:
            if cell[0] == row and cell[1] == column:
                flag = False

        self.locked_grid.append(new_cell)

        print("the new cells"+str(new_cell))
        print("the list after update:" + str(self.locked_grid))
        
        

        print("The flag is: "+ str(flag))
        return flag

    def handle_player(self, player_name):
        
        player_id = self.players_id[player_name]
        player = self.get_player(player_id)
        socket = player["socket"]
        self.send_player_info(player_id)
        
        while True:
            try:
                data = socket.recv(1024)
                if data:
                    decoded_data = data.decode()
                    if "messageEND" in decoded_data:
                        print("execute messageEND")
                        messages = decoded_data.split("messageEND")
                        for message in messages[:-1]:
                            self.handle_single_message(message, player, socket, player_id)
                    else:
                        print("execute non-messageEND")
                        self.handle_single_message(decoded_data, player, socket, player_id)
                else:
                    print(f"Player {player_id} disconnected.")
                    self.is_connect[player_name] = False
                    break

            except Exception as e:
                print(f"playing with {player_id} connection error has occurred:{str(e)}")
                self.is_connect[player_name] = False
                break

    def handle_single_message(self, message, player, socket, player_id):
        if "Surface" in message:
            print("Sending messages to all users...")
            for other_player in self.players:
                if not self.is_connect[other_player["player_name"]]:
                    continue
                other_player["socket"].send(message.encode())
            if self.is_game_over():
                self.handle_game_over()
            print("Sending Data END")

        message_parts = message.split(",")

        if message_parts[0] == "Initial":
            print("Initializing the board for the players...."+str(player))
            self.update_and_send_player_list()
            if len(self.surface_list) > 0:
                for surface in self.surface_list:
                    time.sleep(0.5)
                    player["socket"].send(surface)
            print("Initialization complete.")

        if message_parts[0] == "Confirm":
            print("in Confirm, -- msg1 is: " + str(message_parts))
            row, column, id = int(message_parts[1]), int(message_parts[2]), int(message_parts[3])
            cell = (row, column, id)
            if cell not in self.confirmed_grid:
                self.confirmed_grid.append(cell)
            print(len(self.confirmed_grid))

        elif message_parts[0] == "gridRequest":
            print("in gridRequest -- msg1 is: " + str(message_parts))
            row, column, player_id = int(message_parts[1]), int(message_parts[2]), int(message_parts[3])
            if self.grid_check(row, column, player_id):
                time.sleep(0.1)
                socket.send("Grid_ALLOWED".encode())
            else:
                socket.send("Grid_NOT_ALLOWED".encode())

        elif "Surface" in message_parts[0]:
            if message.encode() not in self.surface_list:
                self.surface_list.append(message.encode())
                print("len of surface is: "+str(len(self.surface_list)))

    def send_player_info(self, player_id):
        """
        - Sends player information, including ID and color, to the player.
        """
        player = self.get_player(player_id)
        color = player["color"]
        message = f"INFO,{player_id},{color}"
        player["socket"].send(message.encode())

    def remove_player(self, player_id):
        """
        - Removes a player with a specific ID from the server.
        """
        with self.lock:
            player = self.get_player(player_id)
            if player:
                self.players.remove(player)
                player["socket"].close()

    def get_player(self, player_id):
        """
        Retrieve player information based on the given player_id.
        Parameters:
            - player_id (int): The ID of the player whose information is to be retrieved.
        Returns:
            - dict or None: If a player with the specified player_id is found in the list of players,
                a dictionary containing the player's information (ID, socket, address, and color) is returned.
                If no player is found with the given player_id, the function returns None.
        """
        for player in self.players:
            if player["id"] == player_id:
                return player
        return None
        
    def set_player_socket(self, player_id, player_socket, player_address):
        """
         - Update the socket and address information of a player based on the given player_id.
        Parameters:
            - player_id (int): The ID of the player whose socket and address information will be updated.
            - player_socket (socket object): The new socket object associated with the player.
            - player_address (tuple): The new address (IP and port) associated with the player's socket.
        """
        for player in self.players:
            if player["id"] == player_id:
                player["socket"] = player_socket
                player["address"] = player_address

    def is_game_over(self):
        """

        :return:
        """

        confirmed_grid = len(self.confirmed_grid)
        #
        leave_grides = 64 - confirmed_grid
        print("leave",leave_grides)
        my_dict = self.count_player_grids()  # get player grids
        print("player data",my_dict)
        sencond_value = self.get_second_largest(my_dict)
        print("the sencond player",sencond_value)
        if leave_grides != 0:

            max_value = max(my_dict.values())
            if not sencond_value + int(leave_grides) >= max_value:
                return True
        else:
            return True

        # return len(self.confirmed_grid) == 5

    def handle_game_over(self):
        """

        :return:
        """
        print("game over")
        print("player data:",self.count_player_grids())  #
        winner = self.getwinner()
        print("Eighth",self.getwinner())  # get winner
        self.send_game_over_to_clients(winner)
        for player in self.players:
            player["socket"].close()

    def close_all_connections(self):
        """
        Close all links
        :return:
        """
        for player in self.players:
            player["socket"].close()

        self.players = []
        print("All play connections have been disconnected.")
        
    def count_player_grids(self):
        """
        Counting users' grids
        :return:
        """
        player_grids = {}
        for cell in self.confirmed_grid:
            player_id = cell[2]
            print("player_id",player_id)
            if player_id in player_grids:
                player_grids[player_id] += 1
            else:
                player_grids[player_id] = 1
        print("player grids is:",player_grids)
        return player_grids

    def get_player_name_by_id(self,players, id):
        for player in players:
            if player['id'] == id:
                return player['player_name']

    def getwinner(self):
        """

        :return:winner
        """
        playerdata = self.count_player_grids()
        # max_item = max(playerdata.items(), key=lambda x: x[1])
        max_list = []
        max_value = max(playerdata.values())
        for m, n in playerdata.items():
            if n == max_value:
                max_list.append(m)
        
        print("max list:",max_list)
        # max_list = [2, 1]
        playernamelist = []
        for i in max_list:
            playername = self.get_player_name_by_id(self.players,i)
            playernamelist.append(playername)
        print("winnerlist is ",playernamelist)
        winner = ' '.join(str(i) for i in playernamelist) + ","
        print("winner is:", winner)

        return winner
    def send_game_over_to_clients(self, winner):
        """
        send game over to clinets
        :param winner: the winner text
        """

        message = f"GAME_OVER,{winner}"
        print("ninth",message[1])
        for player in self.players:
            player["socket"].send(message.encode())
    def get_second_largest(self,dictionary):
        if len(dictionary) < 2:
            return 0

        sorted_values = sorted(dictionary.values(), reverse=True)
        second_largest_value = 0

        for value in sorted_values:
            if value < max(sorted_values):
                second_largest_value = value
                break

        if second_largest_value is None:
            return 0

        # second_largest_keys = [key for key, value in dictionary.items() if value == second_largest_value]
        return second_largest_value

# Server test
def get_lan_ip():
    try:
        # Get the hostname of the local machine
        host_name = socket.gethostname()
        # Get the IP address associated with the hostname
        host_ip = socket.gethostbyname(host_name)
        # Print the hostname and IP address for debugging purposes
        print("Hostname :  ", host_name)
        print("IP : ", host_ip)
        # Return the obtained IP address
        return host_ip
    except:
        # If an exception occurs during the process (e.g., unable to resolve the hostname to an IP address),
        # print an error message indicating the failure
        print("Unable to get Hostname and IP")

# Obtain the local IP address (IPv4) of the current machine
lan_ip = get_lan_ip()
print(lan_ip)

# Server test
# Create a server instance using the obtained local IP address, listening on port 12345,
# and supporting a maximum of 3 players
server = Server(lan_ip, 12345, 3)
# Start the server, allowing it to accept player connections and handle gameplay
server.start()
