import socket
import threading
import time

# 服务器类
class Server:
    def __init__(self, host, port, max_players):
        self.confirmed_grid = []
        self.locked_grid = []
        self.surface_list = []
        self.host = host
        self.port = port
        self.max_players = max_players
        self.players = []
        self.lock = threading.Lock()
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((host, port))
        self.server_socket.listen(max_players)

    def start(self):
        print("服务器已启动,等待玩家连接...")
        while len(self.players) < self.max_players:
            client_socket, client_address = self.server_socket.accept()
            player_id = len(self.players) + 1
            player = {
                "id": player_id,
                "socket": client_socket,
                "address": client_address,
                "color": player_id
            }
            self.players.append(player)
            print(f"玩家 {player_id} 连接成功")
            threading.Thread(target=self.handle_player, args=(player_id,)).start()

    def grid_remove(self,id):
        if len(self.locked_grid) > 0 :
            self.locked_grid = [cell for cell in self.locked_grid if cell[2] != id]

    def grid_check(self,row,column,id):
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

        print("The flag is: "+ str(flag))
        return flag

    def handle_player(self, player_id):
        player = self.get_player(player_id)
        socket = player["socket"]
        self.send_player_info(player_id)
        while True:
            try:
                data = socket.recv(2048)
                if data:
                    message = data.decode()
                    if("Surface" in message):
                        print("给所有user发送消息ing")
                        for other_player in self.players:
                            print(data)
                            other_player["socket"].send(data)
                        print("发送结束 END")

                    # 
                    print(message)
                    message_parts = message.split(",")
                    print("msg[0] is "+ message_parts[0])

                    if message_parts[0] == "Initial":
                        print("正在给玩家初始化棋盘...."+str(player))
                        if len(self.surface_list)>0:
                            for surface in self.surface_list:
                                time.sleep(0.01)
                                player["socket"].send(surface)
                        print("初始化完毕....")

                    if message_parts[0] == "Confirm":
                        row, column,id = int(message_parts[1]), int(message_parts[2]),int(message_parts[3])
                        cell = (row, column,id)
                        if cell not in self.confirmed_grid:
                            self.confirmed_grid.append(cell)
                        print(len(self.confirmed_grid))

                    elif message_parts[0] == "gridRequest":
                        row, column, player_id= int(message_parts[1]), int(message_parts[2]), int(message_parts[3])
                        if self.grid_check(row,column,player_id):
                            time.sleep(0.1)
                            socket.send("Grid_ALLOWED".encode())
                        else:
                            socket.send("Grid_NOT_ALLOWED".encode())

                    elif "Surface" in message_parts[0]:
                        if data not in self.surface_list:
                            self.surface_list.append(data)
                            print("len of surface is: "+str(len(self.surface_list)))
                        
                else:
                    self.remove_player(player_id)
                    self.grid_remove(player_id)
                    print(f"玩家 {player_id} 断开连接")
                    break

            except Exception as e:
                print(f"与玩家 {player_id} 的连接发生错误:{str(e)}")
                self.remove_player(player_id)
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

# 测试服务器
server = Server("localhost", 12346, 3)
server.start()
