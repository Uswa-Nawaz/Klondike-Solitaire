"""
Preview the win page without playing a whole game.

This is a separate developer script; the real game (src/main.py) has no
cheat or shortcut. It builds a won position and opens the window on the
win page.

Run from the project folder with:
    python scripts\\preview_win.py

How the winning position is built (game.py is NOT changed):
  1. Create a normal KlondikeGame, which deals 52 Card objects.
  2. Collect those 52 Card objects from game.card_locations.
  3. Replace every pile with a new, empty Stack (the stock: an empty Queue)
     and empty card_locations.
  4. Place the cards suit by suit, Ace to King, face up, onto the four
     foundations with the game's own _place helper, which also records
     each card in card_locations.
"""

import os
import sys

# Let Python find the modules in src/.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from PyQt6.QtWidgets import QApplication  # noqa: E402

from card import SUITS  # noqa: E402
from data_structures import Queue, Stack  # noqa: E402
from game import KlondikeGame  # noqa: E402
from ui import MainWindow  # noqa: E402


def make_winning_position(game):
    """Move all 52 of the game's own cards onto the foundations, in order."""
    cards = [entry["card"] for entry in game.card_locations.values()]
    for pile_name in list(game.piles):
        if pile_name == "stock":
            game.piles[pile_name] = Queue()
        else:
            game.piles[pile_name] = Stack()
    game.card_locations = {}
    for number, suit in enumerate(SUITS):
        for rank in range(1, 14):
            for card in cards:
                if card.suit == suit and card.rank == rank:
                    card.flip_face_up()
                    game._place(card, f"foundation_{number}")


def main():
    app = QApplication(sys.argv)
    game = KlondikeGame()
    make_winning_position(game)
    window = MainWindow(game)
    window.show_win()        # Play Again starts a normal game
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
