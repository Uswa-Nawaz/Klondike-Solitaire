"""
Playing cards and the standard 52-card deck.

    Card            - one playing card: rank, suit, face-up/face-down state
    create_deck()   - builds the 52-card deck as a Python list
    shuffle_deck()  - shuffles that list in place (Fisher-Yates algorithm)

Data structure used here: Array/List
    The deck is a Python list because shuffling must jump to any position
    instantly: deck[j] takes O(1) time. In a linked list, reaching position j
    means walking j nodes, which would make shuffling O(n^2) instead of O(n).
    The deck list exists only until the cards are dealt into the piles.

A Card only describes itself. It knows no game rules ("can this card go on
that one?"); all rules live in game.py.
"""

import random

SUITS = ("hearts", "diamonds", "clubs", "spades")
RED_SUITS = ("hearts", "diamonds")

# One letter per suit, used to build short card ids such as "10H".
SUIT_LETTERS = {"hearts": "H", "diamonds": "D", "clubs": "C", "spades": "S"}

# Ranks are stored as numbers so rules can use arithmetic
# (e.g. "one lower" is rank - 1). These labels are only for display.
RANK_LABELS = {1: "A", 11: "J", 12: "Q", 13: "K"}

ACE = 1
KING = 13


class Card:
    """One playing card.

    rank    : int from 1 (Ace) to 13 (King)
    suit    : one of SUITS
    face_up : False when created; changed with flip_face_up()/flip_face_down()

    Each physical card in a game is exactly ONE Card object. Piles and the
    card index (a dictionary) hold references to that same object; the
    card itself is never copied.
    """

    def __init__(self, rank, suit):
        # In Python, True and False are a special kind of int (True == 1),
        # so we reject bool explicitly; otherwise Card(True, ...) would
        # silently become an Ace. Strings like "5" and floats like 5.0 are
        # rejected because they are not int at all.
        if isinstance(rank, bool) or not isinstance(rank, int):
            raise ValueError(f"rank must be an int, got {rank!r}")
        if rank < ACE or rank > KING:
            raise ValueError(f"rank must be between {ACE} and {KING}, got {rank}")
        if suit not in SUITS:
            raise ValueError(f"suit must be one of {SUITS}, got {suit!r}")

        self.rank = rank
        self.suit = suit
        self.face_up = False

    # ------------------------------------------------------------------
    # Derived information (properties)
    # ------------------------------------------------------------------
    # A "property" is a method that is used like an attribute: we write
    # card.colour (no brackets) and Python runs the method below.
    # The value is calculated from rank/suit every time it is read and
    # is never stored, so it can never disagree with the rank or suit.
    # Properties without a setter are read-only: card.colour = "red"
    # raises an AttributeError.

    @property
    def colour(self):
        """'red' for hearts and diamonds, 'black' for clubs and spades."""
        if self.suit in RED_SUITS:
            return "red"
        return "black"

    @property
    def card_id(self):
        """Short unique name such as 'AH', '10S' or 'KD'.

        Used later as the key in the card-location dictionary (HashMap).
        """
        # dict.get(key, default) returns the label for 1, 11, 12 and 13,
        # and for every other rank falls back to the number itself ("2".."10").
        label = RANK_LABELS.get(self.rank, str(self.rank))
        return label + SUIT_LETTERS[self.suit]

    # ------------------------------------------------------------------
    # Changing face state
    # ------------------------------------------------------------------
    # Two explicit methods instead of one toggling flip(): every caller
    # knows which state it wants, and calling either method twice is
    # harmless (a toggle called twice would silently undo itself).

    def flip_face_up(self):
        self.face_up = True

    def flip_face_down(self):
        self.face_up = False

    def __repr__(self):
        """Readable text for debugging and test failures, e.g. '10H(up)'."""
        if self.face_up:
            state = "up"
        else:
            state = "down"
        return f"{self.card_id}({state})"


def create_deck():
    """Return a new Python list of 52 face-down Cards in a fixed order.

    Order: hearts A..K, diamonds A..K, clubs A..K, spades A..K.
    Every call creates 52 NEW Card objects.
    """
    deck = []
    for suit in SUITS:
        for rank in range(ACE, KING + 1):
            deck.append(Card(rank, suit))
    return deck


def shuffle_deck(deck, rng=None):
    """Shuffle 'deck' in place using the Fisher-Yates algorithm.

    Algorithm: walk from the last position down to position 1. At each
    position i, pick a random position j between 0 and i (inclusive) and
    swap the two cards. After the swap, position i is final and is never
    touched again. Every possible order is equally likely.

        Time:  O(n)  - one pass, one swap per position
        Space: O(1)  - cards are swapped inside the same list

    rng (random-number generator) is optional:
      - The game passes nothing. We then create random.Random(), which is
        seeded from the operating system, giving a different pseudo-random
        order every game.
      - Tests pass random.Random(seed) with a fixed seed number. The same
        seed always produces the same sequence of pseudo-random numbers,
        so the shuffle result is repeatable and can be checked.

    Returns nothing: the list passed in is changed directly.
    """
    if rng is None:
        rng = random.Random()

    # range(start, stop, step): from the last index down to 1 (stop is excluded).
    for i in range(len(deck) - 1, 0, -1):
        # randint(0, i) includes BOTH ends. Choosing from the whole deck
        # instead of 0..i is a classic mistake that makes some orders
        # more likely than others.
        j = rng.randint(0, i)

        # Swap deck[i] and deck[j] using a temporary variable.
        temp = deck[i]
        deck[i] = deck[j]
        deck[j] = temp
