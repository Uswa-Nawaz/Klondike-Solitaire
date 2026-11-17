"""
Smoke test for src/ui.py: draw frames and simulate clicks on a HIDDEN window.

A smoke test only checks that nothing crashes; the rules themselves are
tested in test_game.py, and the look is checked by playing the game.

Run all tests from the project root with:
    .venv\\Scripts\\python.exe -m unittest discover -s tests -v
"""

import os
import random
import sys
import unittest

# "dummy" makes pygame draw into memory instead of opening a real window.
# These must be set BEFORE pygame creates the window.
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pygame  # noqa: E402

from card import SUITS  # noqa: E402
from data_structures import Queue, Stack  # noqa: E402
from game import KlondikeGame  # noqa: E402
from ui import SolitaireUI  # noqa: E402


def make_winning_position(game):
    """Test-only: move all 52 of the game's own cards onto the foundations.

    Uses only the existing game attributes and its _place helper;
    game.py itself is not changed.
    """
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


def rect_of_card(ui, card_id):
    """The click rectangle of a card in the frame that was just drawn."""
    for rect, kind, value in ui.click_targets:
        if kind == "card" and value == card_id:
            return rect
    return None


class UISmokeTests(unittest.TestCase):

    def setUp(self):
        self.game = KlondikeGame(random.Random(1))
        self.ui = SolitaireUI(self.game)

    def tearDown(self):
        pygame.quit()

    def test_draws_a_frame(self):
        self.ui.draw()
        self.assertGreater(len(self.ui.click_targets), 0)

    def test_clicks_call_the_game_and_clear_the_selection(self):
        ui = self.ui
        game = self.game
        ui.draw()

        ui.handle_click(ui.stock_rect.center)               # draw a card
        self.assertEqual(len(game.piles["waste"]), 1)
        ui.draw()

        top_card = game.piles["tableau_6"].peek()
        ui.handle_click(rect_of_card(ui, top_card.card_id).center)
        self.assertEqual(ui.selected_card_id, top_card.card_id)

        ui.handle_click(ui.buttons["undo"].center)          # undo the draw
        self.assertIsNone(ui.selected_card_id)
        self.assertEqual(len(game.piles["waste"]), 0)

        ui.handle_click(ui.buttons["draw_mode"].center)     # Draw 3 + new game
        self.assertEqual(game.draw_count, 3)
        self.assertEqual(game.move_count(), 0)

        ui.handle_click(ui.buttons["new_game"].center)
        ui.handle_click((5, 600))                           # bare felt
        ui.draw()

    def test_win_overlay_draws_and_play_again_starts_a_new_game(self):
        make_winning_position(self.game)
        self.assertTrue(self.game.is_won())
        self.ui.draw()                                      # overlay must not crash

        self.ui.handle_click(self.ui.play_again_rect.center)
        self.assertFalse(self.game.is_won())
        self.ui.draw()


if __name__ == "__main__":
    unittest.main()
