import socket
import threading
import game_grid
import json
import base64
import pygame
import io
from game_grid import Grids

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255,0,0)
GREEN = (0,255,0)
BLUE = (0,0,255)
YELLOW = (255,204,0)

Drawing_colors = {
    0: WHITE, 
    1: BLACK,
}
player_colors = {
    1:RED,
    2:GREEN,
    3:BLUE,
    4:YELLOW,
}

# 客户端类
class Client:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.player_id = None
        self.player_color = None
        self.allow_move = False
        self.waiting_for_drawing = False
        self.grid = Grids()  # Create an instance of Grids class
        # self.grid = self.grid_instance.init_grid()  # Call init_grid method of the instance
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.connect((host, port))
        threading.Thread(target=self.receive_data).start()

    def receive_data(self):
        while True:
            try:
                data = self.server_socket.recv(2048)
                if data:
                    message = data.decode()
                    print(message)
                    self.handle_message(message)
                else:
                    print("与服务器的连接已断开")
                    break
            except Exception as e:
                print(f"与服务器的连接发生错误:{str(e)}")
                break

    def base64_to_surface(self, message):
        data = json.loads(message)
        row = data['row']
        column = data['column']
        image_str = data['drawing']
        image_bytes = base64.b64decode(image_str)
        image_io = io.BytesIO(image_bytes)
        surface = pygame.image.load_extended(image_io, 'PNG')
        print(f"Row: {row}, Column: {column}")
        self.grid.set_cell_surface(row,column,surface)
        return surface

    def handle_message(self, message):
        message_parts = message.split(",")
        message_type = message_parts[0]
        print(message_type)
        if message_type == "INFO":
            self.handle_player_info(message_parts)

        elif "Surface" in message_type:
            self.base64_to_surface(message)

        if message_type == "Grid_ALLOWED":
            self.allow_move = True
            
        elif message_type == "Grid_NOT_ALLOWED":
            self.allow_move = False

    def send_doodle(self, doodle_info):
        # Encode doodle info as a JSON string
        doodle_str = json.dumps(doodle_info)
        self.server_socket.send(doodle_str.encode())

    def handle_player_info(self, message_parts):
        self.player_id = int(message_parts[1])
        self.player_color = player_colors[self.player_id]
        print(f"您的玩家ID为:{self.player_id},颜色为:{self.player_color}")

    def send_message(self, message):
        self.server_socket.send(message.encode())

# 创建客户端实例
client = Client("localhost", 12346)

# 向服务器发送连接请求
client.send_message("CONNECT")
game_grid.run_game(client.grid,client)
