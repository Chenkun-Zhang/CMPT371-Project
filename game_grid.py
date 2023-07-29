import pygame
import io
import base64
import time
import os

COLOR = {
    (255, 255, 255): 'WHITE',
    (0, 0, 0): 'BLACK',
    (255, 0, 0): 'RED',
    (0, 255, 0): 'GREEN',
    (0, 0, 255): 'BLUE',
    (255, 204, 0): 'YELLOW',
}

# Define some colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

# This sets the WIDTH and HEIGHT of each grid location & window size
WIDTH = 50
HEIGHT = 50
WINDOW_SIZE = [800, 800]

# This sets the margin between each cell
MARGIN = 5
curr_grid = []


def color_distance(c1, c2):
    return sum((x1 - x2) ** 2 for x1, x2 in zip(c1, c2))


def downsample_drawing(drawing, client):
    player_color = client.player_color
    new_drawing = pygame.Surface((50, 50))
    print(player_color)
    for x in range(50):
        for y in range(50):
            avg_color = sum(
                color_distance(drawing.get_at((2 * x + dx, 2 * y + dy)), player_color) for dx in range(2) for dy in
                range(2)) / 4
            new_color = avg_color <= 10  # You need to set an appropriate color_distance_threshold
            new_drawing.set_at((x, y), player_color if new_color else WHITE)
    return new_drawing


def is_half_filled(surface, client):
    total_pixels = 0
    player_color_pixels = 0
    player_color = client.player_color
    for x in range(surface.get_width()):
        for y in range(surface.get_height()):
            pixel = surface.get_at((x, y))
            if color_distance(pixel, player_color) == 0:
                player_color_pixels += 1
            total_pixels += 1

    return player_color_pixels / total_pixels > 0.5


def surface_to_base64(surface):
    print(surface)
    image_io = io.BytesIO()
    pygame.image.save_extended(surface, image_io, 'PNG')
    image_str = base64.b64encode(image_io.getvalue()).decode()
    return image_str


class Grids:
    def __init__(self):
        self.grid = self.init_grid()
        self.draw_pos = (WINDOW_SIZE[0] // 2 - WIDTH, WINDOW_SIZE[1] - HEIGHT * 4)

    def init_grid(self):
        grid = []
        for row in range(8):
            grid.append([])
            for column in range(8):
                drawing = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                drawing.fill((0, 0, 0, 0))  # Fill with transparent color
                grid[row].append({"color": WHITE, "filled": False, "drawing": drawing})
        return grid

    def set_cell_surface(self, row, column, surface):
        print(surface)
        print("set_cell_surface被调用")
        if 0 <= row < 8 and 0 <= column < 8:
            drawing = pygame.transform.scale(surface, (WIDTH, HEIGHT))  # Rescale the surface to match the cell size
            self.grid[row][column]["drawing"] = drawing
        else:
            print("Invalid cell position: ({}, {})".format(row, column))

    # 绘制 8*8 网格
    def draw_grid(self, screen):
        for row in range(8):
            for column in range(8):
                pygame.draw.rect(screen, self.grid[row][column]['color'],
                                 [(MARGIN + WIDTH) * column + MARGIN, (MARGIN + HEIGHT) * row + MARGIN, WIDTH, HEIGHT])
                screen.blit(pygame.transform.scale(self.grid[row][column]["drawing"], (WIDTH, HEIGHT)),
                            [(MARGIN + WIDTH) * column + MARGIN, (MARGIN + HEIGHT) * row + MARGIN])

    # 在底部放大所选窗口，screen包含了绘图
    def draw_selected_cell(self, screen, drawing_area, selected_cell):

        # 绘制grid的背景
        pygame.draw.rect(screen, WHITE, [self.draw_pos[0], self.draw_pos[1], WIDTH * 2, HEIGHT * 2])

        # 绘制用户的回绘制
        screen.blit(pygame.transform.scale(drawing_area, (WIDTH * 2, HEIGHT * 2)), self.draw_pos)

        row, column = selected_cell

        screen.blit(pygame.transform.scale(drawing_area, (WIDTH, HEIGHT)),
                    [(MARGIN + WIDTH) * column + MARGIN, (MARGIN + HEIGHT) * row + MARGIN])


class Player:
    def __init__(self, client):
        self.id = client.player_id
        self.color = client.player_color
        self.client = client
        self.mouse_pressed = False
        self.selected_cell = None
        self.drawing_area = pygame.Surface((WIDTH * 2, HEIGHT * 2))
        self.info_area = pygame.Surface((WIDTH * 4, HEIGHT * 4))

    def send_confirm_info(self, row, column):
        Message = f"Confirm,{row},{column},{self.client.player_id}"
        self.client.send_message(Message)

    def handle_mouse_down(self, pos, grids_instance):
        column = pos[0] // (WIDTH + MARGIN)
        row = pos[1] // (HEIGHT + MARGIN)
        if 0 <= row < 8 and 0 <= column < 8:
            if self.client.waiting_for_drawing:  # If we are waiting for the drawing to complete
                print("Still processing previous ALLOW message")
                return  # Return without sending a new gridRequest message
            gridMessage = f"gridRequest,{row},{column},{self.id}"
            print(gridMessage)
            self.client.server_socket.send(gridMessage.encode())
            time.sleep(0.1)
            if not self.client.allow_move:
                print("THIS IS NOT ALLOWED")
                return
            else:
                self.client.waiting_for_drawing = True  # We received an ALLOW message, so we set the state to waiting
                self.selected_cell = (row, column)
                self.drawing_area.fill(WHITE)
                self.drawing_area.blit(
                    pygame.transform.scale(grids_instance.grid[row][column]["drawing"], (WIDTH * 2, HEIGHT * 2)),
                    (0, 0))

        elif self.selected_cell and (WINDOW_SIZE[0] // 2 - WIDTH <= pos[0] <= WINDOW_SIZE[0] // 2 + WIDTH) and (
                WINDOW_SIZE[1] - HEIGHT * 4 <= pos[1]):
            self.mouse_pressed = True

    def handle_mouse_click(self, grid):
        self.mouse_pressed = False
        if self.selected_cell:
            row, column = self.selected_cell
            new_drawing = downsample_drawing(self.drawing_area, self.client)
            if is_half_filled(self.drawing_area, self.client):
                self.send_confirm_info(row, column)
                drawing_str = surface_to_base64(new_drawing)
                doodle_info = {
                    "Surface": 1,
                    "row": row,
                    "column": column,
                    "drawing": drawing_str
                }
                self.client.send_doodle(doodle_info)
            else:  # if less than 50% filled, clear the cell's drawing
                new_drawing.fill(WHITE)
            grid.set_cell_surface(row, column, new_drawing)  # update the grid in all cases
        self.client.waiting_for_drawing = False  # We finished the drawing, so we set the state back to normal

    # 在底部放大方框里面作画
    def draw_on_drawing_area(self, pos):
        if self.client.allow_move and self.mouse_pressed and self.selected_cell and (
                WINDOW_SIZE[0] // 2 - WIDTH <= pos[0] <= WINDOW_SIZE[0] // 2 + WIDTH) and (
                WINDOW_SIZE[1] - HEIGHT * 4 <= pos[1]):
            pygame.draw.circle(self.drawing_area, self.color,
                               (pos[0] - WINDOW_SIZE[0] // 2 + WIDTH, pos[1] - WINDOW_SIZE[1] + HEIGHT * 4), 5)

    def draw_info(self):
        self.info_area.fill(WHITE)
        font = pygame.font.Font(None, 20)
        for index, (id, name, color) in enumerate(self.client.player_list):
            self.info_area.blit(font.render(f'id:{id}, name:{name}, color:{COLOR[color]}', True, color),
                                (MARGIN, HEIGHT * index))

    # 画出每一个单元格
    def draw(self, screen, grids_instance):
        screen.fill(BLACK)
        grids_instance.draw_grid(screen)
        if self.selected_cell:
            grids_instance.draw_selected_cell(screen, self.drawing_area, self.selected_cell)
        self.draw_info()
        screen.blit(self.info_area, (WINDOW_SIZE[0] - MARGIN - 6 * WIDTH, MARGIN + 2 * HEIGHT))


class Game:
    def __init__(self, screen, player, grids_instance):
        self.screen = screen
        self.player = player
        self.grids_instance = grids_instance
        self.clock = pygame.time.Clock()

    def run(self):
        done = False
        while not done:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    done = True
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    pos = pygame.mouse.get_pos()
                    self.player.handle_mouse_down(pos, self.grids_instance)
                elif event.type == pygame.MOUSEBUTTONUP:
                    self.player.handle_mouse_click(self.grids_instance)
            pos = pygame.mouse.get_pos()
            self.player.draw_on_drawing_area(pos)
            self.player.draw(self.screen, self.grids_instance)
            pygame.display.flip()
            self.clock.tick(60)
        pygame.quit()


def run_game(grid, client=None):
    pygame.init()
    player = Player(client)
    screen = pygame.display.set_mode(WINDOW_SIZE)
    game = Game(screen, player, grid)
    msg = f"Initial,{client.player_id}"
    client.send_message(msg)
    game.run()