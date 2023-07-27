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

    def update_and_send_player_list(self):
        player_list_message = "PLAYERLIST,|"
        for player in self.players:
            player_list_message += f"{player['id']}-{player['color']}|"
        player_list_message = player_list_message[:-1]  # Remove the trailing comma
        for player in self.players:
            player["socket"].send(player_list_message.encode())

    def grid_remove(self,id):
        if len(self.locked_grid) > 0 :
            self.locked_grid = [cell for cell in self.locked_grid if cell[2] != id]

    def grid_check(self,row,column,id):
        print("First",self.locked_grid)
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

        print("Sencond",self.locked_grid)
        print("Third",new_cell)
        print("Fourth",self.confirmed_grid)

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
                            print("Fifth",data)
                            other_player["socket"].send(data)
                        if self.is_game_over():
                            for other_player in self.players:
                                if other_player["id"] != player_id:
                                    other_player["socket"].send(data)
                            self.handle_game_over()
                        print("发送结束 END")

                    # 
                    print("Sixth",message)
                    message_parts = message.split(",")
                    print("msg[0] is "+ message_parts[0])

                    if message_parts[0] == "Initial":
                        print("正在给玩家初始化棋盘...."+str(player))
                        self.update_and_send_player_list()
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
                        print("Seventh",len(self.confirmed_grid))




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
                    # elif "Surface" in message_parts[0] and self.is_game_over():
                    #     self.handle_game_over()

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
        # player = self.get_player(player_id)
        # self.players.remove(player)
        # player["socket"].close()
        with self.lock:
            player = self.get_player(player_id)
            if player:
                self.players.remove(player)
                player["socket"].close()

    def get_player(self, player_id):
        for player in self.players:
            if player["id"] == player_id:
                return player
        return None

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

            if sencond_value:
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
        self.send_game_over_to_clients(winner)  # send msg
        self.close_all_connections()  # close connections

    def close_all_connections(self):
        """
        关闭所有链接
        :return:
        """
        for player in self.players:
            player["socket"].close()

        self.players = []
        print("所有玩连接已断开")

    def count_player_grids(self):
        """
        统计用户的格子数
        :return:
        """
        player_grids = {}
        for cell in self.confirmed_grid:
            player_id = cell[2]
            if player_id in player_grids:
                player_grids[player_id] += 1
            else:
                player_grids[player_id] = 1
        return player_grids





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
        winner = ''
        for i in max_list:
            winner = winner + " " + str(i) + " "

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
            return None

        sorted_values = sorted(dictionary.values(), reverse=True)
        second_largest_value = None

        for value in sorted_values:
            if value < max(sorted_values):
                second_largest_value = value
                break

        if second_largest_value is None:
            return None

        # second_largest_keys = [key for key, value in dictionary.items() if value == second_largest_value]
        return second_largest_value
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

