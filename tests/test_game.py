"""
Unit tests for src/game.py (Stage 3: game setup and dealing).

Run all tests from the project root with:
    .venv\\Scripts\\python.exe -m unittest discover -s tests -v
"""

import os
import random
import sys
import unittest

# Python does not look inside src/ automatically, so we add it to the
# list of folders Python searches when importing modules.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from data_structures import Queue, Stack  # noqa: E402
from game import KlondikeGame  # noqa: E402


def seeded_game(seed=42):
    """Helper: a game dealt from a fixed seed, so every run is identical."""
    return KlondikeGame(random.Random(seed))


def layout(game):
    """Helper: {pile name: [card ids, bottom/front first]} for the whole game."""
    result = {}
    for pile_name, pile in game.piles.items():
        result[pile_name] = [card.card_id for card in pile]
    return result


class GameSetupTests(unittest.TestCase):

    def assert_consistent(self, game):
        """Testing helper (not part of the game): the 'consistency check'.

        Walks through every pile and checks that all 52 cards appear exactly
        once, and that each card's card_locations entry names the pile the
        card is really in and refers to that very Card object.
        """
        seen_ids = []
        for pile_name, pile in game.piles.items():
            for card in pile:
                seen_ids.append(card.card_id)
                entry = game.card_locations[card.card_id]
                self.assertEqual(entry["pile"], pile_name)
                self.assertIs(entry["card"], card)

        self.assertEqual(len(seen_ids), 52)
        self.assertEqual(len(set(seen_ids)), 52)  # no card appears twice
        self.assertEqual(len(game.card_locations), 52)

    def test_game_has_the_expected_piles_and_types(self):
        game = seeded_game()
        self.assertEqual(len(game.piles), 13)
        for column in range(7):
            self.assertIsInstance(game.piles[f"tableau_{column}"], Stack)
        for number in range(4):
            self.assertIsInstance(game.piles[f"foundation_{number}"], Stack)
        self.assertIsInstance(game.piles["waste"], Stack)
        self.assertIsInstance(game.piles["stock"], Queue)
        self.assertEqual(game.draw_count, 1)

    def test_tableau_columns_hold_1_to_7_cards(self):
        game = seeded_game()
        for column in range(7):
            with self.subTest(column=column):
                self.assertEqual(len(game.piles[f"tableau_{column}"]), column + 1)

    def test_only_top_card_of_each_column_is_face_up(self):
        game = seeded_game()
        for column in range(7):
            cards = list(game.piles[f"tableau_{column}"])  # bottom to top
            with self.subTest(column=column):
                self.assertTrue(cards[-1].face_up)
                for card in cards[:-1]:
                    self.assertFalse(card.face_up)

    def test_stock_has_24_face_down_cards_and_other_piles_are_empty(self):
        game = seeded_game()
        stock = game.piles["stock"]
        self.assertEqual(len(stock), 24)
        for card in stock:
            self.assertFalse(card.face_up)

        self.assertTrue(game.piles["waste"].is_empty())
        for number in range(4):
            self.assertTrue(game.piles[f"foundation_{number}"].is_empty())

    def test_all_52_cards_present_exactly_once_and_dictionary_matches(self):
        self.assert_consistent(seeded_game())

    def test_dictionary_example_entry(self):
        game = seeded_game()
        top_card = game.piles["tableau_6"].peek()
        entry = game.card_locations[top_card.card_id]
        self.assertEqual(entry["pile"], "tableau_6")
        self.assertIs(entry["card"], top_card)
        # The face-up state seen through the dictionary is the card's own state.
        self.assertTrue(entry["card"].face_up)

    def test_new_game_resets_everything(self):
        game = seeded_game(1)
        old_piles = game.piles
        # Change the state by hand: move one stock card to the waste.
        game.piles["waste"].push(game.piles["stock"].dequeue())

        game.new_game(random.Random(2))

        self.assertIsNot(game.piles, old_piles)  # brand-new piles
        self.assertTrue(game.piles["waste"].is_empty())
        self.assertEqual(len(game.piles["stock"]), 24)
        for column in range(7):
            self.assertEqual(len(game.piles[f"tableau_{column}"]), column + 1)
        self.assert_consistent(game)

    def test_same_seed_gives_identical_deals(self):
        first = seeded_game(7)
        second = seeded_game(7)
        # Same card id in every position of every pile...
        self.assertEqual(layout(first), layout(second))
        # ...and the two games share no Card objects (separate decks).
        for card_id, entry in first.card_locations.items():
            self.assertIsNot(entry["card"], second.card_locations[card_id]["card"])


if __name__ == "__main__":
    unittest.main()
