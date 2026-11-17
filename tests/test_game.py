"""
Unit tests for src/game.py.

    Stage 3: game setup and dealing
    Stage 4: moves, rules, drawing, recycling, flipping, win detection

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

from card import SUITS, Card  # noqa: E402
from data_structures import Queue, Stack  # noqa: E402
from game import KlondikeGame  # noqa: E402


# ======================================================================
# Test helpers (they exist only in this file, not in the game)
# ======================================================================

LABEL_TO_RANK = {"A": 1, "J": 11, "Q": 12, "K": 13}
LETTER_TO_SUIT = {"H": "hearts", "D": "diamonds", "C": "clubs", "S": "spades"}


def seeded_game(seed=42):
    """A game dealt from a fixed seed, so every run is identical."""
    return KlondikeGame(random.Random(seed))


def empty_table():
    """A game whose piles and dictionary are all empty.

    Tests use it to build small hand-made positions with place().
    """
    game = seeded_game()
    for pile_name in list(game.piles):
        if pile_name == "stock":
            game.piles[pile_name] = Queue()
        else:
            game.piles[pile_name] = Stack()
    game.card_locations = {}
    return game


def place(game, pile_name, card_id, face_up=True):
    """Put a new card such as "7S" or "10H" on a pile, face up by default.

    Uses the game's own _place, so card_locations is updated correctly.
    """
    label = card_id[:-1]
    letter = card_id[-1]
    if label in LABEL_TO_RANK:
        rank = LABEL_TO_RANK[label]
    else:
        rank = int(label)
    card = Card(rank, LETTER_TO_SUIT[letter])
    if face_up:
        card.flip_face_up()
    game._place(card, pile_name)
    return card


def ids(game, pile_name):
    """Card ids in a pile, bottom (or front) first."""
    return [card.card_id for card in game.piles[pile_name]]


def layout(game):
    """{pile name: [card ids]} for the whole game."""
    result = {}
    for pile_name in game.piles:
        result[pile_name] = ids(game, pile_name)
    return result


def snapshot(game):
    """The COMPLETE game state: every pile, every face state, every location.

    Used to prove that an illegal move changed nothing at all.
    """
    piles = {}
    for pile_name, pile in game.piles.items():
        piles[pile_name] = [(card.card_id, card.face_up) for card in pile]
    locations = {}
    for card_id, entry in game.card_locations.items():
        locations[card_id] = (entry["pile"], entry["card"].face_up)
    return piles, locations


def assert_consistent(test, game, expected_count=52):
    """The 'consistency check' (a testing helper, not part of the game).

    Walks through every pile and checks that each card appears exactly
    once, and that each card's card_locations entry names the pile the
    card is really in and refers to that very Card object.
    """
    seen_ids = []
    for pile_name, pile in game.piles.items():
        for card in pile:
            seen_ids.append(card.card_id)
            entry = game.card_locations[card.card_id]
            test.assertEqual(entry["pile"], pile_name)
            test.assertIs(entry["card"], card)

    test.assertEqual(len(seen_ids), expected_count)
    test.assertEqual(len(set(seen_ids)), expected_count)  # no card twice
    test.assertEqual(len(game.card_locations), expected_count)


# ======================================================================
# Stage 3: setup and dealing
# ======================================================================

class GameSetupTests(unittest.TestCase):

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
        assert_consistent(self, seeded_game())

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
        assert_consistent(self, game)

    def test_same_seed_gives_identical_deals(self):
        first = seeded_game(7)
        second = seeded_game(7)
        # Same card id in every position of every pile...
        self.assertEqual(layout(first), layout(second))
        # ...and the two games share no Card objects (separate decks).
        for card_id, entry in first.card_locations.items():
            self.assertIsNot(entry["card"], second.card_locations[card_id]["card"])


# ======================================================================
# Stage 4: moves between tableau columns
# ======================================================================

class TableauMoveTests(unittest.TestCase):

    def assert_illegal(self, game, card_id, destination):
        """The move must fail AND leave the complete game state unchanged."""
        before = snapshot(game)
        ok, reason = game.move_cards(card_id, destination)
        self.assertFalse(ok)
        self.assertNotEqual(reason, "")
        self.assertEqual(snapshot(game), before)

    def test_single_card_legal_move(self):
        game = empty_table()
        place(game, "tableau_0", "7S")
        place(game, "tableau_1", "6H")

        ok, reason = game.move_cards("6H", "tableau_0")

        self.assertTrue(ok)
        self.assertEqual(reason, "")
        self.assertEqual(ids(game, "tableau_0"), ["7S", "6H"])
        self.assertTrue(game.piles["tableau_1"].is_empty())
        self.assertEqual(game.card_locations["6H"]["pile"], "tableau_0")
        assert_consistent(self, game, 2)

    def test_same_colour_is_illegal(self):
        game = empty_table()
        place(game, "tableau_0", "7S")
        place(game, "tableau_1", "6C")
        self.assert_illegal(game, "6C", "tableau_0")

    def test_wrong_rank_is_illegal(self):
        game = empty_table()
        place(game, "tableau_0", "7S")
        place(game, "tableau_1", "5H")
        self.assert_illegal(game, "5H", "tableau_0")

    def test_king_can_go_on_empty_column(self):
        game = empty_table()
        place(game, "tableau_1", "KH")
        ok, _ = game.move_cards("KH", "tableau_0")
        self.assertTrue(ok)
        self.assertEqual(ids(game, "tableau_0"), ["KH"])

    def test_non_king_cannot_go_on_empty_column(self):
        game = empty_table()
        place(game, "tableau_1", "QH")
        self.assert_illegal(game, "QH", "tableau_0")

    def test_run_moves_together_in_order_and_exposed_card_flips(self):
        game = empty_table()
        place(game, "tableau_0", "8H")
        place(game, "tableau_1", "9C", face_up=False)
        place(game, "tableau_1", "7C")
        place(game, "tableau_1", "6H")
        place(game, "tableau_1", "5S")

        ok, _ = game.move_cards("7C", "tableau_0")

        self.assertTrue(ok)
        self.assertEqual(ids(game, "tableau_0"), ["8H", "7C", "6H", "5S"])
        self.assertEqual(ids(game, "tableau_1"), ["9C"])
        # The newly exposed face-down card has been turned face up.
        self.assertTrue(game.piles["tableau_1"].peek().face_up)
        for card_id in ["7C", "6H", "5S"]:
            self.assertEqual(game.card_locations[card_id]["pile"], "tableau_0")
        assert_consistent(self, game, 5)

    def test_already_face_up_card_is_left_as_it_is(self):
        game = empty_table()
        place(game, "tableau_0", "8H")
        place(game, "tableau_1", "8D")
        place(game, "tableau_1", "7C")

        ok, _ = game.move_cards("7C", "tableau_0")

        self.assertTrue(ok)
        self.assertTrue(game.piles["tableau_1"].peek().face_up)

    def test_face_down_card_cannot_be_picked_up(self):
        game = empty_table()
        place(game, "tableau_0", "KH")
        place(game, "tableau_1", "QS", face_up=False)
        place(game, "tableau_1", "4D")
        self.assertFalse(game.can_pick_up("QS"))
        self.assert_illegal(game, "QS", "tableau_0")

    def test_invalid_multi_card_run_is_illegal_and_changes_nothing(self):
        # 7C with 6C on top is NOT a valid run (same colour), so picking up
        # 7C must fail - even though 7C itself would fit on 8H.
        game = empty_table()
        place(game, "tableau_0", "8H")
        place(game, "tableau_1", "9D", face_up=False)
        place(game, "tableau_1", "7C")
        place(game, "tableau_1", "6C")

        self.assertFalse(game.can_pick_up("7C"))
        self.assert_illegal(game, "7C", "tableau_0")
        # The face-down card underneath was NOT flipped.
        self.assertFalse(game.card_locations["9D"]["card"].face_up)

    def test_other_illegal_destinations(self):
        game = empty_table()
        place(game, "tableau_0", "5H")
        place(game, "waste", "9S")
        self.assert_illegal(game, "5H", "tableau_0")   # same pile
        self.assert_illegal(game, "5H", "waste")       # onto the waste
        self.assert_illegal(game, "5H", "stock")       # onto the stock
        self.assert_illegal(game, "5H", "nowhere")     # unknown pile
        self.assert_illegal(game, "XX", "tableau_1")   # unknown card

    def test_stock_card_cannot_be_moved(self):
        game = empty_table()
        place(game, "stock", "KS", face_up=False)
        self.assertFalse(game.can_pick_up("KS"))
        self.assert_illegal(game, "KS", "tableau_0")


# ======================================================================
# Stage 4: foundations and the waste
# ======================================================================

class FoundationAndWasteTests(unittest.TestCase):

    def assert_illegal(self, game, card_id, destination):
        before = snapshot(game)
        ok, _ = game.move_cards(card_id, destination)
        self.assertFalse(ok)
        self.assertEqual(snapshot(game), before)

    def test_ace_can_start_a_foundation(self):
        game = empty_table()
        place(game, "tableau_0", "AH")
        ok, _ = game.move_cards("AH", "foundation_0")
        self.assertTrue(ok)
        self.assertEqual(ids(game, "foundation_0"), ["AH"])

    def test_non_ace_cannot_start_a_foundation(self):
        game = empty_table()
        place(game, "tableau_0", "2H")
        self.assert_illegal(game, "2H", "foundation_0")

    def test_same_suit_next_rank_is_legal(self):
        game = empty_table()
        place(game, "foundation_0", "AH")
        place(game, "tableau_0", "2H")
        ok, _ = game.move_cards("2H", "foundation_0")
        self.assertTrue(ok)
        self.assertEqual(ids(game, "foundation_0"), ["AH", "2H"])

    def test_different_suit_is_illegal(self):
        game = empty_table()
        place(game, "foundation_0", "AH")
        place(game, "tableau_0", "2D")
        self.assert_illegal(game, "2D", "foundation_0")

    def test_wrong_rank_on_foundation_is_illegal(self):
        game = empty_table()
        place(game, "foundation_0", "AH")
        place(game, "tableau_0", "3H")
        self.assert_illegal(game, "3H", "foundation_0")

    def test_two_card_run_cannot_go_to_a_foundation(self):
        game = empty_table()
        place(game, "foundation_0", "AH")
        place(game, "tableau_0", "2H")
        place(game, "tableau_0", "AS")   # 2H + AS form a valid tableau run
        self.assert_illegal(game, "2H", "foundation_0")

    def test_waste_top_card_to_tableau(self):
        game = empty_table()
        place(game, "tableau_0", "8S")
        place(game, "waste", "7H")
        ok, _ = game.move_cards("7H", "tableau_0")
        self.assertTrue(ok)
        self.assertEqual(ids(game, "tableau_0"), ["8S", "7H"])
        self.assertTrue(game.piles["waste"].is_empty())

    def test_waste_top_card_to_foundation(self):
        game = empty_table()
        place(game, "waste", "AC")
        ok, _ = game.move_cards("AC", "foundation_2")
        self.assertTrue(ok)
        self.assertEqual(ids(game, "foundation_2"), ["AC"])

    def test_card_below_waste_top_cannot_move(self):
        game = empty_table()
        place(game, "waste", "AD")
        place(game, "waste", "9S")
        self.assertFalse(game.can_pick_up("AD"))
        self.assert_illegal(game, "AD", "foundation_0")

    def test_card_under_waste_top_becomes_playable(self):
        game = empty_table()
        place(game, "waste", "3D")
        place(game, "waste", "AS")
        self.assertFalse(game.can_pick_up("3D"))

        ok, _ = game.move_cards("AS", "foundation_0")

        self.assertTrue(ok)
        self.assertEqual(game.piles["waste"].peek().card_id, "3D")
        self.assertTrue(game.can_pick_up("3D"))

    def test_foundation_card_back_to_tableau(self):
        game = empty_table()
        place(game, "foundation_0", "AH")
        place(game, "foundation_0", "2H")
        place(game, "tableau_0", "3S")

        ok, _ = game.move_cards("2H", "tableau_0")

        self.assertTrue(ok)
        self.assertEqual(ids(game, "tableau_0"), ["3S", "2H"])
        # The card underneath is now the foundation's top card.
        self.assertEqual(game.piles["foundation_0"].peek().card_id, "AH")
        self.assertTrue(game.can_pick_up("AH"))
        assert_consistent(self, game, 3)

    def test_foundation_card_to_tableau_must_follow_tableau_rules(self):
        game = empty_table()
        place(game, "foundation_0", "AH")
        place(game, "foundation_0", "2H")
        place(game, "tableau_0", "3D")   # red on red is not allowed
        self.assert_illegal(game, "2H", "tableau_0")

    def test_foundation_to_foundation_is_illegal(self):
        game = empty_table()
        place(game, "foundation_0", "AH")
        self.assert_illegal(game, "AH", "foundation_1")


# ======================================================================
# Stage 4: drawing and recycling
# ======================================================================

class StockTests(unittest.TestCase):

    def test_draw_one_moves_front_card_to_waste_face_up(self):
        game = seeded_game()
        front_card = game.piles["stock"].peek()

        self.assertTrue(game.draw_from_stock())

        self.assertIs(game.piles["waste"].peek(), front_card)
        self.assertTrue(front_card.face_up)
        self.assertEqual(len(game.piles["stock"]), 23)
        self.assertEqual(game.card_locations[front_card.card_id]["pile"], "waste")
        assert_consistent(self, game)

    def test_draw_three_moves_three_cards_with_third_on_top(self):
        game = seeded_game()
        game.draw_count = 3
        first_three = ids(game, "stock")[:3]

        game.draw_from_stock()

        self.assertEqual(ids(game, "waste"), first_three)
        self.assertEqual(game.piles["waste"].peek().card_id, first_three[2])
        for card in game.piles["waste"]:
            self.assertTrue(card.face_up)
        self.assertEqual(len(game.piles["stock"]), 21)
        # Only the top waste card can be played.
        self.assertTrue(game.can_pick_up(first_three[2]))
        self.assertFalse(game.can_pick_up(first_three[0]))
        assert_consistent(self, game)

    def test_draw_three_with_fewer_cards_left(self):
        game = empty_table()
        game.draw_count = 3
        place(game, "stock", "4C", face_up=False)
        place(game, "stock", "9H", face_up=False)

        game.draw_from_stock()

        self.assertEqual(ids(game, "waste"), ["4C", "9H"])
        self.assertTrue(game.piles["stock"].is_empty())

    def test_recycle_restores_original_order_face_down(self):
        game = seeded_game()
        original_order = ids(game, "stock")
        for _ in range(24):
            game.draw_from_stock()
        self.assertTrue(game.piles["stock"].is_empty())

        recycled = game.draw_from_stock()   # empty stock -> recycle

        self.assertTrue(recycled)
        self.assertEqual(ids(game, "stock"), original_order)
        for card in game.piles["stock"]:
            self.assertFalse(card.face_up)
        self.assertTrue(game.piles["waste"].is_empty())
        assert_consistent(self, game)

    def test_recycle_with_draw_three_restores_original_order(self):
        game = seeded_game()
        game.draw_count = 3
        original_order = ids(game, "stock")
        for _ in range(8):                  # 8 draws x 3 cards = 24 cards
            game.draw_from_stock()
        game.draw_from_stock()              # recycle
        self.assertEqual(ids(game, "stock"), original_order)

    def test_draw_with_empty_stock_and_empty_waste_does_nothing(self):
        game = empty_table()
        before = snapshot(game)
        self.assertFalse(game.draw_from_stock())
        self.assertEqual(snapshot(game), before)


# ======================================================================
# Stage 4: win detection and the dictionary after many moves
# ======================================================================

class WinAndConsistencyTests(unittest.TestCase):

    def test_new_game_is_not_won(self):
        self.assertFalse(seeded_game().is_won())

    def test_win_is_detected_when_the_last_card_reaches_a_foundation(self):
        game = empty_table()
        rank_labels = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
        for number, suit in enumerate(SUITS):
            letter = suit[0].upper()
            for label in rank_labels:
                if label == "K" and letter == "S":
                    continue              # keep the King of spades back
                place(game, f"foundation_{number}", label + letter)
        place(game, "tableau_0", "KS")
        self.assertFalse(game.is_won())   # 51 cards are not enough

        ok, _ = game.move_cards("KS", "foundation_3")

        self.assertTrue(ok)
        self.assertTrue(game.is_won())
        assert_consistent(self, game)

    def test_dictionary_matches_piles_after_many_actions(self):
        # Play a seeded game by trying every possible move again and again,
        # with draws and recycles in between. After every step, all 52 cards
        # must still be present exactly once and the dictionary must match.
        game = seeded_game(3)
        moves_made = 0
        for _ in range(40):
            game.draw_from_stock()
            assert_consistent(self, game)
            for card_id in list(game.card_locations):
                for destination in list(game.piles):
                    ok, _ = game.move_cards(card_id, destination)
                    if ok:
                        moves_made += 1
                        assert_consistent(self, game)
                        break
        self.assertGreater(moves_made, 0)   # the test really moved cards


# ======================================================================
# Stage 5: undo and redo
# ======================================================================

def play_many_actions(game, rounds=40):
    """Helper: draw, then make the first legal move found, again and again.

    With 40 draws and only 24 stock cards, the stock is recycled at least
    once, so moves, draws and recycles all happen.
    """
    for _ in range(rounds):
        game.draw_from_stock()
        for card_id in list(game.card_locations):
            moved = False
            for destination in list(game.piles):
                ok, _ = game.move_cards(card_id, destination)
                if ok:
                    moved = True
                    break
            if moved:
                break


class UndoRedoTests(unittest.TestCase):

    def test_undo_and_redo_a_move(self):
        game = empty_table()
        place(game, "tableau_0", "7S")
        place(game, "tableau_1", "6H")
        before = snapshot(game)
        game.move_cards("6H", "tableau_0")
        after = snapshot(game)

        self.assertTrue(game.undo())
        self.assertEqual(snapshot(game), before)
        self.assertEqual(game.card_locations["6H"]["pile"], "tableau_1")

        self.assertTrue(game.redo())
        self.assertEqual(snapshot(game), after)
        assert_consistent(self, game, 2)

    def test_undo_turns_the_flipped_card_face_down_again(self):
        game = empty_table()
        place(game, "tableau_0", "8H")
        place(game, "tableau_1", "9C", face_up=False)
        place(game, "tableau_1", "7C")
        before = snapshot(game)

        game.move_cards("7C", "tableau_0")
        nine_of_clubs = game.card_locations["9C"]["card"]
        self.assertTrue(nine_of_clubs.face_up)          # flipped by the move

        game.undo()
        self.assertFalse(nine_of_clubs.face_up)         # hidden again
        self.assertEqual(ids(game, "tableau_1"), ["9C", "7C"])
        self.assertEqual(snapshot(game), before)

        game.redo()
        self.assertTrue(nine_of_clubs.face_up)          # flipped again
        self.assertEqual(ids(game, "tableau_0"), ["8H", "7C"])
        assert_consistent(self, game, 3)

    def test_undo_and_redo_draw_one(self):
        game = seeded_game()
        before = snapshot(game)
        game.draw_from_stock()
        after = snapshot(game)

        game.undo()
        self.assertEqual(snapshot(game), before)   # same stock order, face down

        game.redo()
        self.assertEqual(snapshot(game), after)    # the same card is drawn
        assert_consistent(self, game)

    def test_undo_and_redo_draw_three(self):
        game = seeded_game()
        game.draw_count = 3
        game.draw_from_stock()                     # 3 cards already on the waste
        before = snapshot(game)
        game.draw_from_stock()                     # 3 more (queue rotation needed)
        after = snapshot(game)

        game.undo()
        self.assertEqual(snapshot(game), before)

        game.redo()
        self.assertEqual(snapshot(game), after)
        assert_consistent(self, game)

    def test_undo_draw_three_when_fewer_cards_were_drawn(self):
        game = empty_table()
        game.draw_count = 3
        place(game, "stock", "4C", face_up=False)
        place(game, "stock", "9H", face_up=False)
        before = snapshot(game)

        game.draw_from_stock()                     # only 2 cards drawn
        game.undo()

        self.assertEqual(snapshot(game), before)
        self.assertEqual(ids(game, "stock"), ["4C", "9H"])

    def test_undo_and_redo_recycle(self):
        game = seeded_game()
        for _ in range(24):
            game.draw_from_stock()
        before = snapshot(game)
        game.draw_from_stock()                     # recycle
        after = snapshot(game)

        game.undo()
        self.assertEqual(snapshot(game), before)   # waste rebuilt, face up

        game.redo()
        self.assertEqual(snapshot(game), after)
        assert_consistent(self, game)

    def test_several_undos_and_redos_in_a_row(self):
        game = seeded_game()
        states = [snapshot(game)]
        for _ in range(6):
            game.draw_from_stock()
            states.append(snapshot(game))

        for _ in range(3):
            game.undo()
        self.assertEqual(snapshot(game), states[3])

        game.redo()
        game.redo()
        self.assertEqual(snapshot(game), states[5])
        assert_consistent(self, game)

    def test_new_action_clears_redo(self):
        game = seeded_game()
        game.draw_from_stock()
        game.draw_from_stock()
        game.undo()
        self.assertTrue(game.can_redo())

        game.draw_from_stock()                     # a NEW action

        self.assertFalse(game.can_redo())
        self.assertFalse(game.redo())

    def test_undo_and_redo_with_empty_history_change_nothing(self):
        game = seeded_game()
        before = snapshot(game)
        self.assertFalse(game.can_undo())
        self.assertFalse(game.can_redo())
        self.assertFalse(game.undo())
        self.assertFalse(game.redo())
        self.assertEqual(snapshot(game), before)

    def test_move_count_follows_actions_undo_and_redo(self):
        game = empty_table()
        place(game, "tableau_0", "7S")
        place(game, "tableau_1", "6H")
        place(game, "stock", "2D", face_up=False)
        self.assertEqual(game.move_count(), 0)

        game.draw_from_stock()
        self.assertEqual(game.move_count(), 1)
        game.move_cards("6H", "tableau_0")
        self.assertEqual(game.move_count(), 2)
        game.move_cards("2D", "tableau_5")         # illegal: not counted
        self.assertEqual(game.move_count(), 2)

        game.undo()
        self.assertEqual(game.move_count(), 1)
        game.redo()
        self.assertEqual(game.move_count(), 2)

    def test_new_game_empties_both_history_stacks(self):
        game = seeded_game()
        game.draw_from_stock()
        game.draw_from_stock()
        game.undo()

        game.new_game(random.Random(5))

        self.assertFalse(game.can_undo())
        self.assertFalse(game.can_redo())
        self.assertEqual(game.move_count(), 0)

    def test_undo_everything_returns_to_the_starting_deal_exactly(self):
        game = seeded_game(3)
        start = snapshot(game)
        play_many_actions(game)
        end = snapshot(game)

        # The history must contain all three kinds of action.
        kinds = set(record["action"] for record in game.undo_stack)
        self.assertEqual(kinds, {"move", "draw", "recycle"})
        total_actions = game.move_count()

        undone = 0
        while game.undo():
            undone += 1
            assert_consistent(self, game)
        self.assertEqual(undone, total_actions)
        self.assertEqual(snapshot(game), start)    # identical to the deal

        while game.redo():
            assert_consistent(self, game)
        self.assertEqual(snapshot(game), end)      # identical to the end


if __name__ == "__main__":
    unittest.main()
