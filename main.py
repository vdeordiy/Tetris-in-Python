import pygame
from pygame import Vector2
from pygame.locals import *
import sys
import enum
import random
import copy

# Constants
BLOCK_SIZE = 20
ROWS, COLS = 10, 20
SIZE = WIDTH, HEIGHT = ROWS*BLOCK_SIZE, COLS*BLOCK_SIZE
SPAWN_POINT = Vector2(ROWS//2, 2)

FPS = 24
FALL_EVENT = USEREVENT + 1
FALL_INTERVAL = 800

BLACK = Color("black")
WHITE = Color("white")


class Piece(enum.Enum):
    O = [
        Vector2(0, 1), Vector2(1, 1),
        Vector2(0, 0), Vector2(1, 0),
    ]
    I = [
        Vector2(0, 2),
        Vector2(0, 1),
        Vector2(0, 0),
        Vector2(0, -1),
    ]
    T = [
                        Vector2(0, 1),
        Vector2(-1, 0), Vector2(0, 0), Vector2(1, 0),
    ]
    L = [
        Vector2(0, 2),
        Vector2(0, 1),
        Vector2(0, 0), Vector2(1, 0),
    ]
    J = [
                        Vector2(0, 2),
                        Vector2(0, 1),
        Vector2(-1, 0), Vector2(0, 0),
    ]
    S = [
                         Vector2(0, 0), Vector2(1, 0),
        Vector2(-1, -1), Vector2(0, -1),
    ]
    Z = [
        Vector2(-1, 0), Vector2(0, 0),
                        Vector2(0, -1), Vector2(1, -1)
    ]


class BlockStatus(enum.StrEnum):
    falling = enum.auto()
    landed = enum.auto()


class Transformation(enum.Enum):
    rotate_clockwise = enum.auto()
    rotate_counterclockwise = enum.auto()
    move_left = enum.auto()
    move_right = enum.auto()


class InvalidationReason(enum.Enum):
    collision = enum.auto()
    out_of_boundaries = enum.auto()


piece_color_table = {
    Piece.O: Color("#53DA3F"), Piece.I: Color("#FD3F59"), Piece.J: Color("#FFC82E"),
    Piece.L: Color("#FEFB34"), Piece.S: Color("#01EDFA"), Piece.T: Color("#EA141C"),
    Piece.Z: Color("#FF910C")
}


class Block:
    def __init__(self, pos: Vector2, rot: Vector2, color=BLACK, status=BlockStatus.falling):
        self.pos = pos
        self.rot = rot
        self.color = color
        self.status = status

    def __hash__(self):
        coordinates = (self.coordinates.x, self.coordinates.y)
        return hash(coordinates)

    def __eq__(self, other):
        return hash(self) == hash(other)

    def __repr__(self):
        return f"<Block {self.coordinates}>"

    def add(self, coordinates):
        self.pos += coordinates
        return self

    @property
    def coordinates(self):
        return self.pos + self.rot


class Grid:
    def __init__(self):
        self.blocks: list[Block] = []
        self.current_piece = None
        self.score = 0

    def render(self):
        # Draw blocks
        for block in self.blocks:
            pygame.draw.rect(
                screen,
                block.color,
                Rect(
                    block.coordinates.x * BLOCK_SIZE,
                    block.coordinates.y * BLOCK_SIZE,
                    BLOCK_SIZE,
                    BLOCK_SIZE
                ),
                width=5
            )

        # Draw score
        score_surface = score_font.render(f"Score: {self.score}", True, WHITE)
        score_rect = score_surface.get_rect()
        score_rect.top = 0
        score_rect.left = 0

        screen.blit(score_surface, score_rect)

    def copy(self) -> list[Block]:
        return copy.deepcopy(self.blocks)

    def spawn(self) -> list[Block]:
        piece = random.choice(list(Piece))
        self.current_piece = piece

        blocks = self.copy()
        piece_color = piece_color_table[piece]

        for rotation_vec in piece.value:
            block = Block(pos=SPAWN_POINT.copy(), rot=rotation_vec.copy(), color=piece_color)
            blocks.append(block)

        return blocks

    def fall(self):
        blocks = self.copy()

        for block in blocks:
            if block.status == BlockStatus.falling:
                block.add(Vector2(0, 1))

        if grid.validate(blocks) is True:
            grid.accept(blocks)
        else:
            grid.land()
            self.current_piece = None

    @staticmethod
    def validate(next_blocks: list[Block]):
        for i, block in enumerate(next_blocks):
            # Boundaries
            if block.coordinates.x < 0 or block.coordinates.x >= ROWS:
                return InvalidationReason.out_of_boundaries

            if block.coordinates.y < 0 or block.coordinates.y >= COLS:
                return InvalidationReason.out_of_boundaries

            # Check for unique coordinates
            if block in next_blocks[:i] + next_blocks[i+1:]:
                return InvalidationReason.collision

        return True

    def accept(self, blocks: list[Block]):
        self.blocks = blocks

    def land(self):
        for block in self.blocks:
            block.status = BlockStatus.landed

    def transform(self, transformation):
        blocks = self.copy()

        # Prevent piece O rotation
        if (transformation in (Transformation.rotate_clockwise, Transformation.rotate_counterclockwise)
                and self.current_piece == Piece.O):
            return

        for block in blocks:
            if block.status == BlockStatus.falling:
                if transformation == Transformation.rotate_counterclockwise:
                    block.rot.x, block.rot.y = -block.rot.y, block.rot.x
                elif transformation == Transformation.rotate_clockwise:
                    block.rot.x, block.rot.y = block.rot.y, -block.rot.x

                elif transformation == Transformation.move_left:
                    block.pos.x -= 1
                elif transformation == Transformation.move_right:
                    block.pos.x += 1

        if grid.validate(blocks) is True:
            grid.accept(blocks)

    def check_score_condition(self):
        xs_by_y: dict[int, list[int]] = {}

        for block in self.blocks:
            # Falling block does not count
            if block.status == BlockStatus.falling:
                continue

            if block.coordinates.y not in xs_by_y:
                xs_by_y[block.coordinates.y] = []

            xs_by_y[block.coordinates.y].append(block.coordinates.x)

        score_factor = 0
        highest_y = 0
        ys = 0

        # Check for full rows
        for y, xs in xs_by_y.items():
            if len(xs) == ROWS:
                score_factor += 1

                # Remove row
                for x in xs:
                    self.blocks.remove(Block(Vector2(x, y), Vector2(0, 0)))

                if y > highest_y:
                    highest_y = y

                ys += 1

        # Move down upper blocks
        for block in self.blocks:
            if block.status == BlockStatus.landed and block.coordinates.y < highest_y:
                block.add(Vector2(0, ys))

        # Scoring
        self.score += score_factor ** 2 * 100

        if score_factor:
            # Speed up
            global FALL_INTERVAL
            FALL_INTERVAL = max(FALL_INTERVAL - 100 - (20 * score_factor), 10)


# Set up
pygame.init()
clock = pygame.time.Clock()
screen = pygame.display.set_mode(SIZE)
pygame.display.set_caption("Tetris")
grid = Grid()
pygame.time.set_timer(FALL_EVENT, FALL_INTERVAL)

run_flag = True
K_SPACE_flag = False

score_font = pygame.font.Font(pygame.font.get_default_font(), 15)
game_over_font = pygame.font.Font(pygame.font.get_default_font(), 30)

while run_flag:
    # Logic
    for event in pygame.event.get():
        if event.type == QUIT:
            pygame.quit()
            sys.exit(0)
        elif event.type == FALL_EVENT:
            # Fall
            grid.fall()
            pygame.time.set_timer(FALL_EVENT, FALL_INTERVAL)
        elif event.type == KEYDOWN:
            # Input
            match event.key:
                case pygame.K_ESCAPE:
                    pygame.event.post(pygame.event.Event(QUIT))
                case pygame.K_a | pygame.K_LEFT:
                    grid.transform(Transformation.move_left)
                case pygame.K_d | pygame.K_RIGHT:
                    grid.transform(Transformation.move_right)
                case pygame.K_w | pygame.K_UP:
                    grid.transform(Transformation.rotate_counterclockwise)
                # case pygame.K_s | pygame.K_DOWN:
                #     grid.transform(Transformation.rotate_clockwise)
                case pygame.K_SPACE | pygame.K_s | pygame.K_DOWN:
                    K_SPACE_flag = True
        elif event.type == KEYUP:
            # Input
            match event.key:
                case pygame.K_SPACE | pygame.K_s | pygame.K_DOWN:
                    K_SPACE_flag = False

    if K_SPACE_flag:
        grid.fall()

    # Spawn new piece and check losing condition
    if not grid.current_piece:
        next_grid = grid.spawn()

        if grid.validate(next_grid) == InvalidationReason.collision:
            run_flag = False
        else:
            grid.accept(next_grid)

    # Check score condition
    grid.check_score_condition()

    # Visual
    screen.fill(BLACK)
    grid.render()
    pygame.display.flip()
    clock.tick(FPS)

# Draw game over screen
game_over_surface = game_over_font.render("Game Over", True, Color("red"))
game_over_rect = game_over_surface.get_rect()
game_over_rect.center = WIDTH/2, HEIGHT/2

screen.blit(game_over_surface, game_over_rect)
pygame.display.flip()

pygame.time.delay(3000)
