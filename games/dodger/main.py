"""
Dodger — a minimal pygame game structured for pygbag (browser/WASM) builds.

Run locally with a normal desktop Python + pygame install:
    pip install pygame-ce
    python main.py

Build for the browser with pygbag (from the repo root):
    pip install pygbag
    pygbag games/dodger
This produces games/dodger/build/web/, which is what the site links to.

The only things that differ from a normal pygame script are:
  - the main loop lives inside an `async def main()`
  - there's an `await asyncio.sleep(0)` once per frame, which hands control
    back to the browser so the page doesn't freeze
  - the script kicks off with `asyncio.run(main())`
"""

import asyncio
import math
import random

import pygame

WIDTH, HEIGHT = 480, 640
PLAYER_SIZE = 28
PLAYER_SPEED = 320  # pixels per second
BLOCK_SIZE = 24
SPAWN_EVERY = 0.5   # seconds between new falling blocks

WHITE = (237, 233, 223)
AMBER = (232, 163, 61)
TEAL = (79, 184, 166)
BG = (20, 23, 31)
PANEL = (27, 31, 42)


async def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Dodger")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("monospace", 20)
    big_font = pygame.font.SysFont("monospace", 36, bold=True)

    player = pygame.Rect(WIDTH // 2 - PLAYER_SIZE // 2, HEIGHT - 60, PLAYER_SIZE, PLAYER_SIZE)
    blocks = []
    spawn_timer = 0.0
    survived = 0.0
    game_over = False
    rng = random.Random()

    def spawn_block():
        x = rng.randint(0, WIDTH - BLOCK_SIZE)
        speed = rng.uniform(120, 260)
        blocks.append([pygame.Rect(x, -BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE), speed])

    def reset():
        nonlocal blocks, spawn_timer, survived, game_over, player
        blocks = []
        spawn_timer = 0.0
        survived = 0.0
        game_over = False
        player.x = WIDTH // 2 - PLAYER_SIZE // 2
        player.y = HEIGHT - 60

    running = True
    while running:
        dt = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and game_over and event.key == pygame.K_SPACE:
                reset()

        keys = pygame.key.get_pressed()
        if not game_over:
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                player.x -= PLAYER_SPEED * dt
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                player.x += PLAYER_SPEED * dt
            player.x = max(0, min(WIDTH - PLAYER_SIZE, player.x))

            spawn_timer += dt
            if spawn_timer >= SPAWN_EVERY:
                spawn_timer = 0.0
                spawn_block()

            for block in blocks:
                block[0].y += block[1] * dt
            blocks = [b for b in blocks if b[0].y < HEIGHT + BLOCK_SIZE]

            for block in blocks:
                if player.colliderect(block[0]):
                    game_over = True

            survived += dt

        # --- draw ---
        screen.fill(BG)
        pygame.draw.rect(screen, PANEL, (0, 0, WIDTH, 44))
        timer_surf = font.render(f"survived: {survived:5.1f}s", True, TEAL)
        screen.blit(timer_surf, (12, 12))

        pygame.draw.rect(screen, AMBER, player, border_radius=6)
        for block in blocks:
            pygame.draw.rect(screen, WHITE, block[0], border_radius=4)

        if game_over:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((20, 23, 31, 200))
            screen.blit(overlay, (0, 0))
            msg = big_font.render("game over", True, AMBER)
            hint = font.render("press space to retry", True, WHITE)
            screen.blit(msg, msg.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 20)))
            screen.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 24)))

        pygame.display.flip()

        # hand control back to the browser event loop each frame
        await asyncio.sleep(0)

    pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())
