import socket
import threading
import time


# 服务器类
class Server:
    def __init__(self, host, port, max_players):
        self.confirmed_grid = []
        self.locked_grid = []
        self.surface_list = []
        # Save the corresponding player's ID based on the name
        self.players_id = {}
        # Save the corresponding player's online status based on their name
        self.is_connect = {}
        self.host = host
        self.port = port
        self.max_players = max_players
        self.players = []
        self.lock = threading.Lock()
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((host, port))
        self.server_socket.listen(max_players)

    def start(self):
        print("The server has started, waiting for players to connect...")
        while True:
            client_socket, client_address = self.server_socket.accept()
            # Obtain the player's name
            data = client_socket.recv(2048)
            player_name = data.decode()
            # Player connected
            if player_name in self.is_connect and self.is_connect[player_name]:
                print(f"player {player_name}({self.players_id[player_name]}) connected")
                # Send connected messages to clients
                client_socket.send("CONNECTED".encode())
                continue
            if player_name not in self.is_connect:
                if len(self.players) == self.max_players:
                    client_socket.send("FULL".encode())
                    continue
                # If it is a newly created player
                player_id = len(self.players) + 1
                player = {
                    "id": player_id,
                    "player_name": player_name,
                    "socket": client_socket,
                    "address": client_address,
                    "color": player_id
                }
                self.players_id[player_name] = player_id
                self.players.append(player)
                print(f"player {player_name}({player_id}) created successfully")
            else:
                # The player has created it, but reconnected after disconnecting
                player_id = self.players_id[player_name]
                self.set_player_socket(player_id, client_socket, client_address)
                print(f"player {player_name}({player_id}) reconnected")
            self.is_connect[player_name] = True
            threading.Thread(target=self.handle_player, args=(player_name,)).start()

    def update_and_send_player_list(self):
        player_list_message = "PLAYERLIST,|"
        for player in self.players:
            player_list_message += f"{player['id']}-{player['player_name']}-{player['color']}|"
        player_list_message = player_list_message[:-1]  # Remove the trailing comma
        for player in self.players:
            if not self.is_connect[player["player_name"]]:
                continue
            player["socket"].send(player_list_message.encode())

    def grid_remove(self, id):
        if len(self.locked_grid) > 0:
            self.locked_grid = [cell for cell in self.locked_grid if cell[2] != id]

    def grid_check(self, row, column, id):
        print(self.locked_grid)
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

        print(self.locked_grid)
        print(new_cell)
        print(self.confirmed_grid)

        print("The flag is: " + str(flag))
        return flag

    def handle_player(self, player_name):
        player_id = self.players_id[player_name]
        print("Player id: ", player_id)
        player = self.get_player(player_id)
        socket = player["socket"]
        self.send_player_info(player_id)
        while True:
            try:
                data = socket.recv(2048)
                if data:
                    message = data.decode()
                    if "Surface" in message:
                        print("Sending messages to all users")
                        for other_player in self.players:
                            if not self.is_connect[other_player["player_name"]]:
                                continue
                            print(data)
                            other_player["socket"].send(data)
                        print("Sending END")

                    # 
                    print(message)
                    message_parts = message.split(",")
                    print("msg[0] is " + message_parts[0])

                    if message_parts[0] == "Initial":
                        print("Initializing chessboard for player...." + str(player))
                        self.update_and_send_player_list()
                        if len(self.surface_list) > 0:
                            for surface in self.surface_list:
                                time.sleep(0.01)
                                player["socket"].send(surface)
                        print("Initialization completed....")

                    if message_parts[0] == "Confirm":
                        row, column, id = int(message_parts[1]), int(message_parts[2]), int(message_parts[3])
                        cell = (row, column, id)
                        if cell not in self.confirmed_grid:
                            self.confirmed_grid.append(cell)
                        print(len(self.confirmed_grid))

                    elif message_parts[0] == "gridRequest":
                        row, column, player_id = int(message_parts[1]), int(message_parts[2]), int(message_parts[3])
                        if self.grid_check(row, column, player_id):
                            time.sleep(0.1)
                            socket.send("Grid_ALLOWED".encode())
                        else:
                            socket.send("Grid_NOT_ALLOWED".encode())

                    elif "Surface" in message_parts[0]:
                        if data not in self.surface_list:
                            self.surface_list.append(data)
                            print("len of surface is: " + str(len(self.surface_list)))

                else:
                    print(f"player {player_id} Disconnect")
                    self.is_connect[player_name] = False
                    break

            except Exception as e:
                print(f"player {player_id} Connected with error:{str(e)}")
                self.is_connect[player_name] = False
                break

    def send_player_info(self, player_id):
        player = self.get_player(player_id)
        color = player["color"]
        message = f"INFO,{player_id},{color}"
        player["socket"].send(message.encode())

    def remove_player(self, player_id):
        player = self.get_player(player_id)
        self.players.remove(player)
        player["socket"].close()

    def get_player(self, player_id):
        for player in self.players:
            if player["id"] == player_id:
                return player
        return None

    def set_player_socket(self, player_id, player_socket, player_address):
        for player in self.players:
            if player["id"] == player_id:
                player["socket"] = player_socket
                player["address"] = player_address


# 测试服务器
def get_lan_ip():
    try:
        host_name = socket.gethostname()
        host_ip = socket.gethostbyname(host_name)
        print("Hostname :  ", host_name)
        print("IP : ", host_ip)
        return host_ip
    except:
        print("Unable to get Hostname and IP")


lan_ip = get_lan_ip()
print(lan_ip)

server = Server(lan_ip, 12346, 3)
server.start()
