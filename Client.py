import socket
import sys
import threading
import sys
import game_grid
import json
import tkinter as tk
from tkinter import simpledialog
import base64
import pygame
import io
import tkinter as tk
from tkinter import simpledialog
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

# Client Class
class Client:
    def __init__(self, host, port):
        # Initialize the attributes of the class
        self.host = host # Server host address
        self.port = port # Server port number
        self.player_name = None # Player's name (initially None)
        self.player_id = None # Player's ID (initially None)
        self.player_color = None  # Player's color (initially None)
        self.allow_move = False # Flag for allowing player moves (initially False)
        self.waiting_for_drawing = False  # Flag for waiting for drawing (initially False)
        self.grid = Grids()  # Create an instance of Grids class
        self.player_list = [] # List to store player information
        self.game_status = True  # set game_status=True
        self.winner = None  # Variable to store the winner of the game (initially None)
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # Create a socket for the client to connect to the server
        self.server_socket.connect((host, port)) # Connect the client socket to the server using provided host and port
        threading.Thread(target=self.receive_data).start() # Start a new thread to run the receive_data method concurrently

    def receive_data(self):
        while True:
            try:
                data = self.server_socket.recv(2048) # Receive data from the server (up to 2048 bytes)
                if data: # Check if data has been received
                    message = data.decode()
                    # print(message)
                    if message == "CONNECTED": # Check the message content and take appropriate actions
                        print("Please do not reconnect the server")
                        sys.exit(0)
                    if message == "FULL":
                        print("Reached maximum players")
                        sys.exit(0)
                    self.handle_message(message) # Call a method to handle the received message
                else:
                    print("Connection to the server has been disconnected.")
                    break
            except Exception as e:
                print(f"An error occurred connecting to the server:{str(e)}")
                break
 # Convert base64-encoded image data to a pygame surface and update the grid
    def base64_to_surface(self, message):
        data = json.loads(message)
        row = data['row']
        column = data['column']
        image_str = data['drawing']
        image_bytes = base64.b64decode(image_str)
        image_io = io.BytesIO(image_bytes)
        surface = pygame.image.load_extended(image_io, 'PNG') # Load image into a pygame surface
        print(f"Row: {row}, Column: {column}")
        self.grid.set_cell_surface(row,column,surface)  # Update grid cell with the surface
        return surface

    def handle_message(self, message):  # Handle different types of incoming messages
        message_parts = message.split(",")
        message_type = message_parts[0]
        print(message_type)
        if message_type == "INFO":
            self.handle_player_info(message_parts)

        if "Surface" in message_type:
            self.base64_to_surface(message)

        if message_type == "PLAYERLIST":
            self.update_player_list(message) 

        if message_type == "Grid_ALLOWED":
            self.allow_move = True
            
        elif message_type == "Grid_NOT_ALLOWED":
            self.allow_move = False
        if message_type == "GAME_OVER":
            winner_id = str(message_parts[1])
            print(f"Game is over, Player: {winner_id} is Win!")
            #update game_staus,winner
            self.game_status=False
            self.winner =winner_id

    def update_player_list(self, message): # Update the player list based on the received message
        player_list = message.split('|')[1:]
        self.player_list.clear()
        for infor in player_list:
            if infor:
                player_id, player_color, player_name = infor.split('-')
                player_id = int(player_id)
                self.player_list.append((player_id, player_colors[player_id], player_name))
        print('Updating playerlist:')
        print('\n'.join([f'The player ID is:{item[0]}, Name: {item[2]}, Color:{item[1]}'for item in self.player_list]))

    def send_doodle(self, doodle_info): # Send doodle information to the server
        # Encode doodle info as a JSON string
        doodle_str = json.dumps(doodle_info)
        self.server_socket.send(doodle_str.encode())

    def handle_player_info(self, message_parts): # Handle player information received from the server
        self.player_id = int(message_parts[1])
        self.player_color = player_colors[self.player_id]
        print(f"Your player ID is:{self.player_id}, And color is:{self.player_color}")

    def send_message(self, message): # Send a plain text message to the server
        self.server_socket.send(message.encode())

# Creating a Client Instance
def get_lan_ip():
    try:
        host_name = socket.gethostname()
        host_ip = socket.gethostbyname(host_name)
        print("Hostname :  ", host_name)
        print("IP : ", host_ip)
        return host_ip
    except:
        print("Unable to get Hostname and IP")

# Input IP address and create a Client instance
ip = input("Please input the ip addr,(press 1 use local host)")
if ip == "1":
    ip = get_lan_ip()

client = Client(ip, 12345)

# # Ask the user to enter a name
# player_name = input("Input your name: ")

# # Send name to server
# client.send_message(player_name)


# Creating a hidden Tkinter window
root = tk.Tk()
root.withdraw()

# Pop up a dialog box to get the player name
client.player_name = simpledialog.askstring('Player name', 'Please input player name:', initialvalue='', parent=root)

# Destroying the Tkinter window
root.destroy()
client.send_message(client.player_name)

game_grid.run_game(client.grid, client)