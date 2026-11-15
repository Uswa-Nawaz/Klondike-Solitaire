"""
Unit tests for src/card.py: the Card class, create_deck() and shuffle_deck().

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

from card import SUITS, Card, create_deck, shuffle_deck  # noqa: E402


def card_ids(cards):
    """Helper: the list of card ids, in order."""
    return [card.card_id for card in cards]


class CardTests(unittest.TestCase):

    def test_stores_rank_and_suit(self):
        card = Card(7, "clubs")
        self.assertEqual(card.rank, 7)
        self.assertEqual(card.suit, "clubs")

    def test_new_card_is_face_down(self):
        self.assertFalse(Card(1, "hearts").face_up)

    def test_colour_for_each_suit(self):
        self.assertEqual(Card(5, "hearts").colour, "red")
        self.assertEqual(Card(5, "diamonds").colour, "red")
        self.assertEqual(Card(5, "clubs").colour, "black")
        self.assertEqual(Card(5, "spades").colour, "black")

    def test_card_id_uses_labels_and_suit_letters(self):
        self.assertEqual(Card(1, "hearts").card_id, "AH")
        self.assertEqual(Card(2, "clubs").card_id, "2C")
        self.assertEqual(Card(10, "spades").card_id, "10S")
        self.assertEqual(Card(11, "clubs").card_id, "JC")
        self.assertEqual(Card(12, "hearts").card_id, "QH")
        self.assertEqual(Card(13, "diamonds").card_id, "KD")

    def test_derived_properties_are_read_only(self):
        # colour and card_id are calculated, not stored, so they cannot
        # be set to a value that disagrees with the suit/rank.
        card = Card(5, "hearts")
        with self.assertRaises(AttributeError):
            card.colour = "black"
        with self.assertRaises(AttributeError):
            card.card_id = "5S"

    def test_flip_face_up_and_down(self):
        card = Card(9, "spades")
        card.flip_face_up()
        self.assertTrue(card.face_up)
        card.flip_face_down()
        self.assertFalse(card.face_up)

    def test_flipping_twice_in_same_direction_is_harmless(self):
        card = Card(9, "spades")
        card.flip_face_up()
        card.flip_face_up()
        self.assertTrue(card.face_up)
        card.flip_face_down()
        card.flip_face_down()
        self.assertFalse(card.face_up)

    def test_rank_out_of_range_raises(self):
        for bad_rank in [0, 14, -1, 100]:
            with self.subTest(rank=bad_rank):
                with self.assertRaises(ValueError):
                    Card(bad_rank, "hearts")

    def test_rank_that_is_not_an_int_raises(self):
        # "5" is text, 5.0 is a float, True is a bool (Python treats it as 1),
        # None is no value at all. None of them is a valid rank.
        for bad_rank in ["5", 5.0, True, False, None]:
            with self.subTest(rank=bad_rank):
                with self.assertRaises(ValueError):
                    Card(bad_rank, "hearts")

    def test_invalid_suit_raises(self):
        for bad_suit in ["stars", "Hearts", "H", "", None]:
            with self.subTest(suit=bad_suit):
                with self.assertRaises(ValueError):
                    Card(5, bad_suit)

    def test_repr_shows_id_and_face_state(self):
        card = Card(10, "hearts")
        self.assertEqual(repr(card), "10H(down)")
        card.flip_face_up()
        self.assertEqual(repr(card), "10H(up)")


class CreateDeckTests(unittest.TestCase):

    def test_deck_is_a_list_of_52_cards(self):
        deck = create_deck()
        self.assertIsInstance(deck, list)
        self.assertEqual(len(deck), 52)

    def test_all_52_cards_are_unique(self):
        self.assertEqual(len(set(card_ids(create_deck()))), 52)

    def test_13_cards_per_suit_and_4_per_rank(self):
        deck = create_deck()
        for suit in SUITS:
            with self.subTest(suit=suit):
                count = len([card for card in deck if card.suit == suit])
                self.assertEqual(count, 13)
        for rank in range(1, 14):
            with self.subTest(rank=rank):
                count = len([card for card in deck if card.rank == rank])
                self.assertEqual(count, 4)

    def test_all_cards_start_face_down(self):
        for card in create_deck():
            self.assertFalse(card.face_up)

    def test_deck_has_fixed_starting_order(self):
        ids = card_ids(create_deck())
        self.assertEqual(ids[0], "AH")
        self.assertEqual(ids[12], "KH")
        self.assertEqual(ids[13], "AD")
        self.assertEqual(ids[51], "KS")

    def test_each_call_creates_new_card_objects(self):
        first_deck = create_deck()
        second_deck = create_deck()
        for first_card, second_card in zip(first_deck, second_deck):
            self.assertIsNot(first_card, second_card)


class ShuffleDeckTests(unittest.TestCase):

    def test_shuffle_keeps_the_same_52_cards(self):
        deck = create_deck()
        shuffle_deck(deck, random.Random(42))
        self.assertEqual(len(deck), 52)
        self.assertEqual(sorted(card_ids(deck)), sorted(card_ids(create_deck())))

    def test_shuffle_is_in_place_and_does_not_copy_cards(self):
        deck = create_deck()
        list_before = deck
        objects_before = set(id(card) for card in deck)

        result = shuffle_deck(deck, random.Random(42))

        self.assertIsNone(result)          # returns nothing
        self.assertIs(deck, list_before)   # same list object
        # Exactly the same Card objects, only in a different order.
        self.assertEqual(set(id(card) for card in deck), objects_before)

    def test_shuffle_changes_the_order(self):
        deck = create_deck()
        shuffle_deck(deck, random.Random(42))
        self.assertNotEqual(card_ids(deck), card_ids(create_deck()))

    def test_same_seed_gives_same_order(self):
        first_deck = create_deck()
        second_deck = create_deck()
        shuffle_deck(first_deck, random.Random(123))
        shuffle_deck(second_deck, random.Random(123))
        self.assertEqual(card_ids(first_deck), card_ids(second_deck))

    def test_different_seeds_give_different_orders(self):
        first_deck = create_deck()
        second_deck = create_deck()
        shuffle_deck(first_deck, random.Random(1))
        shuffle_deck(second_deck, random.Random(2))
        self.assertNotEqual(card_ids(first_deck), card_ids(second_deck))

    def test_shuffle_without_rng_still_keeps_all_cards(self):
        deck = create_deck()
        shuffle_deck(deck)  # uses its own pseudo-random generator
        self.assertEqual(sorted(card_ids(deck)), sorted(card_ids(create_deck())))

    def test_shuffle_does_not_change_face_state(self):
        deck = create_deck()
        shuffle_deck(deck, random.Random(42))
        for card in deck:
            self.assertFalse(card.face_up)

    def test_shuffle_empty_and_single_card_lists(self):
        empty = []
        shuffle_deck(empty, random.Random(1))
        self.assertEqual(empty, [])

        single_card = Card(1, "spades")
        one = [single_card]
        shuffle_deck(one, random.Random(1))
        self.assertEqual(one, [single_card])

    def test_shuffle_is_fair(self):
        # Shuffle the 3-item list [0, 1, 2] 60,000 times. It has 6 possible
        # orders, so a fair shuffle should give each order about
        # 60,000 / 6 = 10,000 times.
        #
        # Tolerance: each order must appear between 9,500 and 10,500 times
        # (10,000 +/- 5%).
        #   - A fair shuffle varies by only about +/- 91 per order here,
        #     so a correct implementation passes with a wide safety margin.
        #   - The common buggy shuffle "swap EVERY position with ANY
        #     position" is off by about +/- 11% (roughly 8,900 or 11,100),
        #     so it falls outside the range and this test fails.
        #   - With fewer trials (6,000) and a looser range (+/- 15%) that
        #     bug slipped through, which is why both were tightened.
        # The seed is fixed, so the result is the same on every run.
        rng = random.Random(2026)
        counts = {}
        for _ in range(60000):
            items = [0, 1, 2]
            shuffle_deck(items, rng)
            order = tuple(items)
            counts[order] = counts.get(order, 0) + 1

        self.assertEqual(len(counts), 6, "every one of the 6 orders must appear")
        for order, count in counts.items():
            with self.subTest(order=order):
                self.assertGreaterEqual(count, 9500)
                self.assertLessEqual(count, 10500)


if __name__ == "__main__":
    unittest.main()
