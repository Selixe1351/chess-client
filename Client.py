from enum import Enum, auto

import random
import os
from uuid import uuid1
from settings.Settings import screen_size, max_fps
from stockfish import Stockfish

import pygame
import chess
import sys
import glob
import chess.engine
import asyncio
import threading

from util.Button import ButtonGroup

class GameColor(Enum):
    WHITE = auto()
    BLACK = auto()

class ChessPiece(Enum):
    PAWN = ""
    BISHOP = "B"
    KNIGHT = "N"
    ROOK = "R"
    KING = "K"
    QUEEN = "Q"

class GamePiece:

    def __init__(self, color: GameColor, piece: ChessPiece, location: tuple):
        self.color = color
        self.piece = piece
        self.location = location

        self.image = self.load_image()

        square_size = min(screen_size[0] // 10, screen_size[1] // 10)

        self.image = pygame.transform.smoothscale(self.image, (square_size, square_size))

    def load_image(self):
        color_folder = self.color.name.lower()
        piece_name = self.piece.name.lower()
        
        image_path = f"images/static/{color_folder}/{piece_name}.png"

        if os.path.exists(image_path):
            return pygame.image.load(image_path)
        else:
            raise FileNotFoundError(f"Image for {self.color.name} {self.piece.name} not found.")

    def get_possible_moves(self, board: dict) -> list:
        possible_moves = []
        for row in range(8):
            for col in range(8):
                if self.can_move((row, col), board):
                    possible_moves.append((row, col))
        return possible_moves

    def can_move(self, new_pos: tuple, board: list) -> bool:
        new_row, new_col = new_pos

        if not (0 <= new_row < 8 and 0 <= new_col < 8):
            return False

        # Convert board to dictionary for faster lookups
        board_dict = {piece.location: piece for piece in board}

        if self.piece == ChessPiece.PAWN:
            return self._pawn_move(GameColor.WHITE, new_pos, board_dict)
        elif self.piece == ChessPiece.ROOK:
            return self._rook_move(new_pos, board_dict)
        elif self.piece == ChessPiece.BISHOP:
            return self._bishop_move(new_pos, board_dict)
        elif self.piece == ChessPiece.KNIGHT:
            return self._knight_move(new_pos, board_dict)
        elif self.piece == ChessPiece.QUEEN:
            return self._queen_move(new_pos, board_dict)
        elif self.piece == ChessPiece.KING:
            return self._king_move(new_pos, board_dict)

        return False

    def _pawn_move(self, player_color: GameColor, new_pos, board):
        current_row, current_col = self.location
        new_row, new_col = new_pos

        perspective_flipped = player_color == GameColor.BLACK
        if perspective_flipped:
            direction = -1 if self.color == GameColor.WHITE else 1
        else:
            direction = 1 if self.color == GameColor.WHITE else -1

        # Regular move
        if new_col == current_col:
            if new_row == current_row + direction and (new_row, new_col) not in board:
                return True

            # Double step from start row
            start_row = 1 if self.color == GameColor.WHITE else 6
            if current_row == start_row and new_row == current_row + (2 * direction):
                if (new_row, new_col) not in board and (current_row + direction, current_col) not in board:
                    return True

        # Capture
        if abs(new_col - current_col) == 1 and new_row == current_row + direction:
            if (new_row, new_col) in board and board[(new_row, new_col)].color != self.color:
                return True

        return False

    def _rook_move(self, new_pos, board):
        current_row, current_col = self.location
        new_row, new_col = new_pos

        if current_row != new_row and current_col != new_col:
            return False

        if current_row == new_row:
            step = 1 if new_col > current_col else -1
            for col in range(current_col + step, new_col, step):
                if (current_row, col) in board:
                    return False

        elif current_col == new_col:
            step = 1 if new_row > current_row else -1
            for row in range(current_row + step, new_row, step):
                if (row, current_col) in board:
                    return False

        if (new_row, new_col) in board and board[(new_row, new_col)].color == self.color:
            return False

        return True

    def _bishop_move(self, new_pos: tuple, board: dict) -> bool:
        current_row, current_col = self.location
        new_row, new_col = new_pos

        # Check if the move is diagonal
        if abs(new_row - current_row) != abs(new_col - current_col):
            return False

        # Determine the step direction for both row and column
        row_step = 1 if new_row > current_row else -1
        col_step = 1 if new_col > current_col else -1

        row, col = current_row + row_step, current_col + col_step
        while (row, col) != (new_row, new_col):
            if not (0 <= row < 8 and 0 <= col < 8):
                return False

            if (row, col) in board:
                return False

            row += row_step
            col += col_step

        if (new_row, new_col) in board and board[(new_row, new_col)].color == self.color:
            return False

        return True


    def _knight_move(self, new_pos, board):
        current_row, current_col = self.location
        new_row, new_col = new_pos

        if (abs(new_row - current_row), abs(new_col - current_col)) not in [(2, 1), (1, 2)]:
            return False

        if (new_row, new_col) in board and board[(new_row, new_col)].color == self.color:
            return False

        return True

    def _queen_move(self, new_pos, board):
        return self._rook_move(new_pos, board) or self._bishop_move(new_pos, board)

    def _king_move(self, new_pos, board):
        current_row, current_col = self.location
        new_row, new_col = new_pos

        if max(abs(new_row - current_row), abs(new_col - current_col)) > 1:
            return False

        if (new_row, new_col) in board and board[(new_row, new_col)].color == self.color:
            return False



        return True


class GameClient:
    def __init__(self, name: str, rating: int = 1000):
        self.id = uuid1
        self.client = None
        self.name = name
        self.rating = rating
        self.pieces = []
        self.king_moved = False
        self.left_rook_moved = False
        self.right_rook_moved = False
        self.color = None

    def set_client(self, client):
        self.client = client

    def can_castle(self, long: bool) -> bool:
        if self.king_moved:
            return False

        if long:
            if self.color == GameColor.WHITE:
                if self.left_rook_moved:
                    return False
            elif self.color == GameColor.BLACK:
                if self.left_rook_moved:
                    return False
        else:
            if self.color == GameColor.WHITE:
                if self.right_rook_moved:
                    return False
            elif self.color == GameColor.BLACK:
                if self.right_rook_moved:
                    return False

        return True
    
    def get_piece(self, pos: tuple) -> GamePiece | None:
        for piece in self.pieces:
            if piece.location == pos:
                return piece
            
        return None
    
    def play_sound(self, key: str):
        if self.client:
            sound = self.client.get_sound(key)
            if sound:
                sound.play()

class AIGameClient(GameClient):
    def __init__(self):
        self.difficulty = 20
        self.stockfish_path = "engine\stockfish-windows-x86-64.exe"

        super().__init__("Engine", 3000)

    def get_stockfish_move(self, board: chess.Board):
        """
        Requests a move from Stockfish based on the current game board.
        """
        with chess.engine.SimpleEngine.popen_uci(self.stockfish_path) as engine:
            # Request the best move from Stockfish (with a time limit)
            result = engine.play(board, chess.engine.Limit(time=2.0))  # Stockfish move with 2 seconds thinking time
            return result.move

class Game:
    def __init__(self, one: GameClient, two: GameClient):
        self.id = uuid1
        self.one: GameClient = one
        self.two: GameClient = two
        self.next_move = GameColor.WHITE
        self.board = chess.Board()
        self.squares = {}
        self.moves = []
        self.clock = pygame.time.Clock()
        self.prev = None
        self.last = None

        self.one.color = GameColor.WHITE
        self.two.color = GameColor.BLACK
    
        if isinstance(self.two, AIGameClient):
            self.ai_client = self.two  # AI player is the second player
        else:
            self.ai_client = None  # No AI, two human players

        square_size = min(screen_size[0] // 10, screen_size[1] // 10)
        actual_board_width = square_size * 8
        padding = (screen_size[0] - actual_board_width) // 4
        controls_width = screen_size[0] // 10 * 4 - (padding)
        controls_height = screen_size[1] // 10 * 8
        controls_rect = pygame.Rect(padding + actual_board_width, (screen_size[1] - controls_height) // 2, controls_width, controls_height)

        self.side_buttons = ButtonGroup(controls_rect, background_color="#222222")

        self.side_buttons.add_button('previous', '<', "Previous Move")
        self.side_buttons.add_button('next', '>', "Next Move")

        self.setup()

    def get_moves(self, color: GameColor) -> list:
        filtered_moves = []
        
        for i, move in enumerate(self.moves):
            if (i % 2 == 0 and color == GameColor.WHITE) or (i % 2 == 1 and color == GameColor.BLACK):
                filtered_moves.append(move)

        return filtered_moves

    def setup(self):

        self.one.pieces = [
            GamePiece(self.one.color, ChessPiece.ROOK, (0, 0)),
            GamePiece(self.one.color, ChessPiece.KNIGHT, (0, 1)),
            GamePiece(self.one.color, ChessPiece.BISHOP, (0, 2)),
            GamePiece(self.one.color, ChessPiece.QUEEN, (0, 3)),
            GamePiece(self.one.color, ChessPiece.KING, (0, 4)),
            GamePiece(self.one.color, ChessPiece.BISHOP, (0, 5)),
            GamePiece(self.one.color, ChessPiece.KNIGHT, (0, 6)),
            GamePiece(self.one.color, ChessPiece.ROOK, (0, 7)),
            *[GamePiece(self.one.color, ChessPiece.PAWN, (1, i)) for i in range(8)]
        ]

        self.two.pieces = [
            GamePiece(self.two.color, ChessPiece.ROOK, (7, 0)),
            GamePiece(self.two.color, ChessPiece.KNIGHT, (7, 1)),
            GamePiece(self.two.color, ChessPiece.BISHOP, (7, 2)),
            GamePiece(self.two.color, ChessPiece.QUEEN, (7, 3)),
            GamePiece(self.two.color, ChessPiece.KING, (7, 4)),
            GamePiece(self.two.color, ChessPiece.BISHOP, (7, 5)),
            GamePiece(self.two.color, ChessPiece.KNIGHT, (7, 6)),
            GamePiece(self.two.color, ChessPiece.ROOK, (7, 7)),
            *[GamePiece(self.two.color, ChessPiece.PAWN, (6, i)) for i in range(8)]
        ]


    def get_square_at(self, pos: tuple) -> str:
        row, col = pos
        rank = 8 - row
        file = chr(col + ord('a'))
        return f"{file}{rank}"
    
    def get_piece_at(self, pos: tuple) -> GamePiece | None:
        if not isinstance(pos, tuple) or len(pos) != 2:
            return None

        for piece in self.one.pieces + self.two.pieces:
            if piece.location == pos:
                return piece

        return None
    
    def handle_move(self, client: GameClient, piece: GamePiece, old: tuple, new: tuple) -> str | None:
        if not client.get_piece(old).can_move(new, self.one.pieces + self.two.pieces):
            return None
        
        self.move_piece(client, old, new)
        
        self.run_ai_move_async(client, piece, old, new)
    
    def run_async(self, func, *args):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(func(*args))

    def move_piece(self, client: GameClient, old: tuple, new: tuple) -> bool:
        piece = self.get_piece_at(old)
        if piece:
            if piece.piece == ChessPiece.KING:
                self.get_client(piece.color).king_moved = True

            if piece.piece == ChessPiece.ROOK:
                if old[0] == 0:
                    self.get_client(piece.color).left_rook_moved = True

                if old[0] == 7:
                    self.get_client(piece.color).right_rook_moved = True

            captured_piece = self.get_piece_at(new)
            if captured_piece is not None and captured_piece.color != piece.color:
                self.capture_piece(captured_piece)

            piece.location = new

            self.moves.append(self.get_notation(piece.piece, old, new, captured_piece is not None))

            from_square = chess.square(old[1], old[0])
            to_square = chess.square(new[1], new[0])

            move = chess.Move(from_square, to_square)

            if move in self.board.legal_moves:
                self.board.push(move)

            self.prev = old
            self.last = new

            self.next_move = GameColor.BLACK if self.next_move == GameColor.WHITE else GameColor.WHITE

            if self.board.is_check():
                client.play_sound("move-check.mp3")
            elif captured_piece:
                client.play_sound("move-capture.mp3")
            else:
                client.play_sound("move-self.mp3")

    def run_ai_move_async(self, client: GameClient, piece: GamePiece, old: tuple, new: tuple):
        ai_thread = threading.Thread(target=self.handle_ai_move, args=(client, piece, old, new))
        ai_thread.daemon = True
        ai_thread.start()

    def handle_ai_move(self, client: GameClient, piece: GamePiece, old: tuple, new: tuple):
        if self.next_move != self.get_client(piece.color):
            if self.ai_client and self.next_move == self.ai_client.color:
                if self.board.turn == chess.BLACK:
                    ai_move = self.ai_client.get_stockfish_move(self.board)
                    self.board.push(ai_move)

                    from_square = ai_move.from_square
                    to_square = ai_move.to_square

                    from_row, from_col = chess.square_rank(from_square), chess.square_file(from_square)
                    to_row, to_col = chess.square_rank(to_square), chess.square_file(to_square)

                    self.move_piece(client, (from_row, from_col), (to_row, to_col)) 

    def capture_piece(self, piece: GamePiece):
        self.get_client(piece.color).pieces.remove(piece)

    def get_board(self):

        board = {}
        for piece in self.one.pieces + self.two.pieces:
            board[piece.location] = piece
        return board

    def convert_to_uci(self, algebraic_notation: str) -> str:
        board = chess.Board()

        move = board.parse_san(algebraic_notation)

        return move.uci()

    def get_notation(self, piece: ChessPiece, old: tuple, new: tuple, capture: bool) -> str:
        old_row, old_col = old
        new_row, new_col = new
    
        piece_notation = piece.value
        
        if capture:
            capture_notation = 'x'
        else:
            capture_notation = ''
        
        old_col_letter = chr(ord('a') + old_col)
        new_col_letter = chr(ord('a') + new_col)
        
        if piece == ChessPiece.PAWN:
            if capture:
                move_notation = f"{old_col_letter}x{new_col_letter}{new_row + 1}"
            else:
                move_notation = f"{new_col_letter}{new_row + 1}"
        else:
            move_notation = f"{piece_notation}{capture_notation}{new_col_letter}{new_row + 1}"
        
        return move_notation


    def get_client(self, color: GameColor) -> GameClient:
        team: GameClient = self.one if self.one.color == color else self.two

        return team

class GameState(Enum):
    WAITING = auto()
    STARTED = auto()
    QUIT = auto()

class Client:
    def __init__(self) -> None:
        self.audios = {}

        self.load()
        self.name = None
        self.client = None
        self.game = None
        self.arrows = []
        self.selected_squares = []
        self.selected = None
        self.dragged_piece = None
        self.dragged_piece_pos = None
        self.state = GameState.WAITING
        self.current_cursor = pygame.SYSTEM_CURSOR_ARROW

        flags = pygame.DOUBLEBUF

        self.screen = pygame.display.set_mode(screen_size, flags, 16)
        self.primary_font = pygame.font.Font(None, 24)
        self.secondary_font = pygame.font.Font(None, 16)

    def load(self):
        pygame.init()
        pygame.mixer.init()

        pygame.display.set_caption("Chess")

        logo = pygame.image.load("images/static/logo.png")

        pygame.display.set_icon(logo)

        for sound_path in glob.glob("assets/audio/*.mp3"):
            try:
                sound = pygame.mixer.Sound(sound_path)
                self.audios[sound_path] = sound
            except pygame.error as e:
                print(f"Failed to load sound {sound_path}: {e}")

    def get_sound(self, key: str) -> pygame.mixer.Sound | None:
        for sound_path, sound in self.audios.items():
            sound_name = os.path.basename(sound_path)
            if sound_name == key:
                return sound
        return None

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

                self.client = self.game.one
                self.game.one.set_client(self)
                self.state = GameState.STARTED

            pygame.display.update()

        while self.state == GameState.STARTED:

            print(self.game.clock.get_fps())
            self.game.clock.tick(max_fps)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.state = GameState.QUIT

                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 3:
                        self.dragged_piece = None
                        self.dragged_piece_pos = None
                    if event.button == 1:  # Left click
                        self.selected_squares.clear()
                        mouse_x, mouse_y = event.pos
                        if self.game is not None:
                            # Check if clicking on a square
                            for square in self.game.squares.keys():
                                if self.game.squares.get(square).collidepoint((mouse_x, mouse_y)):
                                    piece = self.game.get_piece_at(square)
                                    
                                    if self.selected is None:  # No piece selected yet
                                        # Select the piece if it matches the player's turn
                                        if piece is not None and piece.color == self.game.next_move:
                                            self.selected = square
                                            self.dragged_piece = piece
                                            self.dragged_piece_pos = event.pos
                                    else:  # A piece is already selected
                                        # Attempt to move to the clicked square
                                        selected_piece = self.game.get_piece_at(self.selected)
                                        if selected_piece and selected_piece.can_move(square, self.game.one.pieces + self.game.two.pieces):
                                            self.game.handle_move(
                                                self.game.get_client(selected_piece.color),
                                                selected_piece,
                                                self.selected,
                                                square
                                            )
                                            self.selected = None
                                            self.dragged_piece = None
                                            self.dragged_piece_pos = None
                                        else:
                                            # Invalid move, deselect
                                            self.selected = None
                                            self.dragged_piece = None
                                            self.dragged_piece_pos = None

                if event.type == pygame.MOUSEMOTION:
                    if self.dragged_piece is not None:
                        self.dragged_piece_pos = event.pos  # Update dragged piece position

                if event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1 and self.dragged_piece is not None:  # Left button release
                        mouse_x, mouse_y = event.pos
                        for square in self.game.squares.keys():
                            if self.game.squares.get(square).collidepoint((mouse_x, mouse_y)):
                                # Release the piece on the square if it's a valid move
                                selected_piece = self.game.get_piece_at(self.selected)
                                if selected_piece and selected_piece.can_move(square, self.game.one.pieces + self.game.two.pieces):
                                    self.game.handle_move(
                                        self.game.get_client(selected_piece.color),
                                        selected_piece,
                                        self.selected,
                                        square
                                    )
                                # Deselect in either case
                                self.selected = None
                                self.dragged_piece = None
                                self.dragged_piece_pos = None
                                break

                    if event.button == 3:  # Right button to toggle square selection
                        mouse_x, mouse_y = event.pos
                        if self.game is not None:
                            for square in self.game.squares.keys():
                                if self.game.squares.get(square).collidepoint((mouse_x, mouse_y)):
                                    if square in self.selected_squares:
                                        self.selected_squares.remove(square)
                                    else:
                                        self.selected_squares.append(square)


            self.draw_board()
            self.draw_controls()

            pygame.display.update()

    def draw_waiting(self):
        temp: pygame.Surface = pygame.Surface([screen_size[0], screen_size[1]])
        temp.fill("#111111")

        self.screen.blit(temp, [0,0])

    def draw_board(self):
        temp: pygame.Surface = pygame.Surface([screen_size[0], screen_size[1]])
        temp.fill("#302e2b")

        self.screen.blit(temp, [0,0])

        square_size = min(screen_size[0] // 10, screen_size[1] // 10)

        actual_board_width = square_size * 8
        actual_board_height = square_size * 8

        board_x = (screen_size[0] - actual_board_width) // 8
        board_y = (screen_size[1] - actual_board_height) // 2

        for row in range(8):
            for col in range(8):
                reversed_row = 7 - row

                if (reversed_row + col) % 2 == 0:
                    # White square
                    if self.selected_squares.__contains__((reversed_row, col)):
                        color = "#e26f5a"
                    else:
                        color = "#ba9f7a"
                else:
                    # Black square
                    if self.selected_squares.__contains__((reversed_row, col)):
                        color = "#d5604d"
                    else:
                        color = "#6f5038"


                if self.selected is not None and self.selected == (reversed_row, col):
                    color = "#c7a355"

                if self.game.prev == (reversed_row, col):
                    color = "#a07b32"

                if self.game.last == (reversed_row, col):
                    color = "#c7a355"

                square_x = board_x + col * square_size
                square_y = board_y + row * square_size
                square_rect = pygame.Rect(square_x, square_y, square_size, square_size)

                pygame.draw.rect(self.screen, color, square_rect)
        
                if self.selected is not None and isinstance(self.selected, tuple):
                    piece = self.game.get_piece_at(self.selected)
                    if piece is not None:
                        if piece.can_move((reversed_row, col), self.game.one.pieces + self.game.two.pieces):
                            transparent_surface = pygame.Surface((square_size, square_size), pygame.SRCALPHA)
                            pygame.draw.circle(transparent_surface, (0, 0, 0, 50), (square_size // 2, square_size // 2), square_size // 6)
                            self.screen.blit(transparent_surface, (square_x, square_y))

                if self.game is not None:
                    self.game.squares[(reversed_row, col)] = square_rect

                for piece in self.game.one.pieces + self.game.two.pieces:
                    if piece.location == (reversed_row, col): 

                        scaled_rect = piece.image.get_rect()

                        center_x = square_x + square_size // 2
                        center_y = square_y + square_size // 2

                        offset_x = center_x - scaled_rect.width // 2
                        offset_y = center_y - scaled_rect.height // 2

                        if self.dragged_piece is not None and self.dragged_piece.location == (reversed_row, col):
                            offset_x = self.dragged_piece_pos[0] - scaled_rect.width // 2
                            offset_y = self.dragged_piece_pos[1] - scaled_rect.height // 2

                        self.screen.blit(piece.image, (offset_x, offset_y))

        self.render_names(board_x, board_y, square_size)

    def render_names(self, board_x, board_y, square_size):
        user_name_text = self.primary_font.render(self.game.one.name, True, (255, 255, 255))
        user_name_rect = user_name_text.get_rect(left=board_x, top=board_y + (square_size * 8) + 10)
        self.screen.blit(user_name_text, user_name_rect)

        user_name_width = user_name_text.get_width()

        user_rating_text = self.secondary_font.render("(" + str(self.game.one.rating) + ")", True, (200, 200, 200))
        user_rating_rect = user_rating_text.get_rect(left=board_x + user_name_width + 5, top=board_y + (square_size * 8) + 12.5)
        self.screen.blit(user_rating_text, user_rating_rect)

        enemy_name_text = self.primary_font.render(self.game.two.name, True, (255, 255, 255))
        enemy_name_rect = enemy_name_text.get_rect(left=board_x, top=board_y - 30)
        self.screen.blit(enemy_name_text, enemy_name_rect)

        enemy_name_width = enemy_name_text.get_width()

        enemy_rating_text = self.secondary_font.render("(" + str(self.game.two.rating) + ")", True, (200, 200, 200))
        enemy_rating_rect = enemy_rating_text.get_rect(left=board_x + enemy_name_width + 5, top=board_y - 27.5)
        self.screen.blit(enemy_rating_text, enemy_rating_rect)

        for row in range(8):
            rank_text = self.secondary_font.render(str(8 - row), True, (255, 255, 255))
            rank_rect = rank_text.get_rect(center=(board_x - 20, board_y + row * square_size + square_size // 2))
            self.screen.blit(rank_text, rank_rect)

        for col in range(8):
            file_text = self.secondary_font.render(chr(ord('a') + col), True, (255, 255, 255))
            file_rect = file_text.get_rect(center=(board_x + col * square_size + square_size // 2, board_y + 8 * square_size + 20))
            self.screen.blit(file_text, file_rect)

    def draw_controls(self):
        square_size = min(screen_size[0] // 10, screen_size[1] // 10)
        actual_board_width = square_size * 8

        padding = (screen_size[0] - actual_board_width) // 4
        controls_width = screen_size[0] // 10 * 4 - (padding)
        controls_height = screen_size[1] // 10 * 8

        controls_x = padding + actual_board_width
        controls_y = (screen_size[1] - controls_height) // 2

        controls_rect = pygame.Rect(controls_x, controls_y, controls_width, controls_height)
        pygame.draw.rect(self.screen, "#222222", controls_rect)

        if self.game is None:
            return

        move_padding = 16
        font = pygame.font.SysFont(None, 22)
        
        max_lines = controls_height // (font.get_height() + move_padding)
        
        scrollable_area_height = controls_height - 20
        scroll_position = self.scroll_position if hasattr(self, "scroll_position") else 0

        start_move = scroll_position
        end_move = min(start_move + max_lines * 2, len(self.game.moves))
        
        move_index = start_move

        for i in range(start_move, end_move, 2):
            move_text = f"{i//2 + 1}. {self.game.moves[i]} "
            if i + 1 < len(self.game.moves):
                move_text += self.game.moves[i + 1]

            row_color = "#262522" if (i // 2) % 2 == 0 else "#2b2927"
            
            row_rect = pygame.Rect(controls_x, controls_y, controls_width, font.get_height() + move_padding)
            pygame.draw.rect(self.screen, row_color, row_rect)

            move_surface = font.render(move_text, True, (200, 200, 200))
            self.screen.blit(move_surface, (controls_x + 20, controls_y + 8))

            controls_y += font.get_height() + move_padding
            move_index += 2

        if len(self.game.moves) > max_lines * 2:
            scrollbar_height = (scrollable_area_height / len(self.game.moves)) * max_lines * 2
            scrollbar_rect = pygame.Rect(controls_x + controls_width - 20, controls_y + 10 + scroll_position, 10, scrollbar_height)
            pygame.draw.rect(self.screen, "#333333", scrollbar_rect)

        if pygame.mouse.get_pressed()[0]:
            mouse_y = pygame.mouse.get_pos()[1]
            if controls_rect.collidepoint(pygame.mouse.get_pos()):
                if mouse_y < controls_y + 10:
                    scroll_position = max(0, scroll_position - 10)
                elif mouse_y > controls_y + controls_height - 10:
                    scroll_position = min(len(self.game.moves) - max_lines * 2, scroll_position + 10)

        self.scroll_position = max(0, min(scroll_position, len(self.game.moves) - max_lines * 2))

        self.game.side_buttons.update_buttons()
        self.game.side_buttons.draw(self.screen, pygame.mouse.get_pos())


    def update_cursor(self, mouse_pos):
        should_use_hand_cursor = any(button.is_hovered(mouse_pos) for button in self.game.side_buttons.buttons)

        new_cursor = pygame.SYSTEM_CURSOR_HAND if should_use_hand_cursor else pygame.SYSTEM_CURSOR_ARROW

        if new_cursor != self.current_cursor:
            pygame.mouse.set_cursor(new_cursor)
            self.current_cursor = new_cursor



client = Client()

while client.active():
    client.run()