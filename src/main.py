"""
Start Klondike Solitaire.

Run from the project folder with:
    .venv\\Scripts\\python.exe src\\main.py
"""

from game import KlondikeGame
from ui import SolitaireUI


def main():
    game = KlondikeGame()        # game logic: piles, rules, undo/redo
    ui = SolitaireUI(game)       # window: draws the game, turns clicks into calls
    ui.run()                     # loop until the window is closed


if __name__ == "__main__":
    main()
