"""
Smoke test for the PyQt6 interface: pages, a few clicks and the win page,
all on Qt's hidden "offscreen" platform (no real window opens).

A smoke test only checks that nothing crashes and that clicks reach the
game; the rules themselves are tested in test_game.py.

Run all tests from the project root with:
    python -m unittest discover -s tests -v
"""

import os
import random
import sys
import unittest

# Must be set BEFORE the QApplication is created.
os.environ["QT_QPA_PLATFORM"] = "offscreen"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from PyQt6.QtWidgets import QApplication  # noqa: E402

from card import SUITS  # noqa: E402
from data_structures import Queue, Stack  # noqa: E402
from game import KlondikeGame  # noqa: E402
from ui import MainWindow  # noqa: E402

# A PyQt program has exactly one QApplication; reuse it if it exists.
app = QApplication.instance() or QApplication([])


def make_winning_position(game):
    """Test-only: move all 52 of the game's own cards onto the foundations."""
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


def rect_of(table, kind, value):
    """The click rectangle of a card or pile, from the table's own layout."""
    for rect, entry_kind, entry_value in table.compute_layout():
        if entry_kind == kind and entry_value == value:
            return rect
    return None


class UISmokeTests(unittest.TestCase):

    def setUp(self):
        self.game = KlondikeGame(random.Random(1))
        self.window = MainWindow(self.game)
        self.window.resize(1280, 800)
        self.window.show()
        app.processEvents()

    def tearDown(self):
        self.window.close()

    def test_pages_switch_with_the_buttons(self):
        window = self.window
        self.assertIs(window.stack.currentWidget(), window.menu_page)
        window.menu_page.instructions_button.click()
        self.assertIs(window.stack.currentWidget(), window.instructions_page)
        window.instructions_page.back_button.click()
        window.menu_page.play_button.click()
        self.assertIs(window.stack.currentWidget(), window.game_page)
        window.grab()                                  # paints every widget
        window.game_page.menu_button.click()
        self.assertIs(window.stack.currentWidget(), window.menu_page)

    def test_clicks_reach_the_game_and_clear_the_selection(self):
        page = self.window.game_page
        table = page.table
        self.window.menu_page.play_button.click()
        app.processEvents()

        table.handle_click(rect_of(table, "pile", "stock").center())
        self.assertEqual(len(self.game.piles["waste"]), 1)

        top_card_id = self.game.piles["tableau_6"].peek().card_id
        table.handle_click(rect_of(table, "card", top_card_id).center())
        self.assertEqual(table.selected_card_id, top_card_id)

        page.undo_button.click()
        self.assertIsNone(table.selected_card_id)
        self.assertEqual(len(self.game.piles["waste"]), 0)
        self.assertFalse(page.undo_button.isEnabled())

        page.mode_button.click()                       # Draw 3 + new game
        self.assertEqual(self.game.draw_count, 3)
        self.assertEqual(self.game.move_count(), 0)
        self.window.grab()

    def test_win_page_appears_and_play_again_starts_a_new_game(self):
        window = self.window
        window.menu_page.play_button.click()
        make_winning_position(self.game)
        window.game_page.after_change()                # the game page notices the win
        self.assertIs(window.stack.currentWidget(), window.win_page)
        window.grab()

        window.win_page.play_again_button.click()
        self.assertIs(window.stack.currentWidget(), window.game_page)
        self.assertFalse(self.game.is_won())


if __name__ == "__main__":
    unittest.main()
