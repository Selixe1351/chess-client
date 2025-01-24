from enum import Enum, auto

from uuid import uuid1
from settings.Settings import screen_size, max_fps

import pygame

class GameClient:
    def __init__(self, name: str):
        self.id = uuid1
        self.name = name
        self.pieces = []

class AIGameClient(GameClient):
    def __init__(self):

        super().__init__("Stockfish")

class Game:
    def __init__(self, one: GameClient, two: GameClient):
        self.id = uuid1
        self.one = one
        self.two = two

class GameState(Enum):
    WAITING = auto()
    STARTED = auto()
    QUIT = auto()

class Client:
    def __init__(self) -> None:
        self.load()
        self.name = None
        self.game = None
        self.state = GameState.WAITING

        self.screen = pygame.display.set_mode(screen_size)

    def load(self):
        pygame.init()

        pygame.display.set_caption("Chess")

    def quit(self):
        pygame.quit()

    def active(self) -> bool:
        return self.state != GameState.QUIT

    def run(self):

        while self.state == GameState.QUIT:
            self.quit()

        while self.state == GameState.WAITING:
            self.draw_waiting()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.state = GameState.QUIT

            pressed = pygame.key.get_pressed()

            if pressed[pygame.K_SPACE]:
                self.game = Game(GameClient("User"), AIGameClient())

                self.state = GameState.STARTED

            pygame.display.update()

        while self.state == GameState.STARTED:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.state = GameState.QUIT

            self.draw_board()

            pygame.display.update()

    def draw_waiting(self):
        temp: pygame.Surface = pygame.Surface([screen_size[0], screen_size[1]])
        temp.fill("#333333")

        self.screen.blit(temp, [0,0])

    def draw_board(self):
        temp: pygame.Surface = pygame.Surface([screen_size[0], screen_size[1]])
        temp.fill("#222222")

        self.screen.blit(temp, [0,0])

        square_size = min(screen_size[0] // 10, screen_size[1] // 10)

        actual_board_width = square_size * 8
        actual_board_height = square_size * 8

        board_x = (screen_size[0] - actual_board_width) // 2
        board_y = (screen_size[1] - actual_board_height) // 2

        for row in range(8):
            for col in range(8):

                if (row + col) % 2 == 0:
                    color = "#ebebeb"  # White
                else:
                    color = "#1a1a1a"  # Black

                square_x = board_x + col * square_size
                square_y = board_y + row * square_size

                square_rect = pygame.Rect(square_x, square_y, square_size, square_size)
                pygame.draw.rect(self.screen, color, square_rect)


client = Client()

while client.active():
    client.run()