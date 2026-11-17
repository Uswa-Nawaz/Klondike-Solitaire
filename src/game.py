"""
Klondike Solitaire game logic (no graphics here).

Stage 3: game setup - creating the piles and dealing the cards.

Data structures used in this file:
    Array/List  - the shuffled deck (from card.py), read by position while dealing
    Stack       - 7 tableau columns, 4 foundations, the waste pile
    Queue       - the stock (draw pile)
    HashMap     - two dictionaries: 'piles' and 'card_locations' (see below)
"""

from card import create_deck, shuffle_deck
from data_structures import Queue, Stack

TABLEAU_COUNT = 7
FOUNDATION_COUNT = 4


class KlondikeGame:
    """Holds the whole game state and (in later stages) all the rules."""

    def __init__(self, rng=None):
        # How many cards one click on the stock draws. Draw 1 for now;
        # kept as a setting so Draw 3 can be added later.
        self.draw_count = 1

        # Both dictionaries are filled in by new_game().
        self.piles = {}
        self.card_locations = {}

        self.new_game(rng)

    def new_game(self, rng=None):
        """Start a fresh game: new empty piles, then shuffle and deal.

        rng is an optional pseudo-random number generator, passed on to
        shuffle_deck(). Tests pass random.Random(seed) so the deal is
        repeatable; the real game passes nothing.
        """
        # ---- Dictionary 1: piles ------------------------------------
        # Key:   pile name (a string), e.g. "tableau_3"
        # Value: the pile object itself (a Stack or the stock Queue)
        # Lets the game turn a name into the real pile in one O(1) step.
        # A brand-new dictionary with brand-new empty piles is created on
        # every new game, so nothing from the previous game can remain.
        self.piles = {}
        for column in range(TABLEAU_COUNT):
            self.piles[f"tableau_{column}"] = Stack()
        for number in range(FOUNDATION_COUNT):
            self.piles[f"foundation_{number}"] = Stack()
        self.piles["waste"] = Stack()
        self.piles["stock"] = Queue()

        # ---- Dictionary 2: card_locations ---------------------------
        # Key:   card id (a string), e.g. "10H"
        # Value: {"card": <the Card object>, "pile": "tableau_3"}
        # Example: card_locations["10H"] -> {"card": 10H(up), "pile": "tableau_3"}
        # The face-up state is read from the Card object itself. That is
        # the SAME object that sits inside the pile (a reference, not a
        # copy), so the state is never stored twice.
        self.card_locations = {}

        # ---- Array/List: create and shuffle the 52-card deck --------
        deck = create_deck()
        shuffle_deck(deck, rng)

        # ---- Deal the tableau: column c gets c + 1 cards ------------
        # 'next_card' is the position in the deck list of the next card
        # to deal (array access by index).
        next_card = 0
        for column in range(TABLEAU_COUNT):
            pile_name = f"tableau_{column}"
            for _ in range(column + 1):
                self._place(deck[next_card], pile_name)
                next_card += 1

            # Only the last card dealt to each column is turned face up.
            # peek() returns the top card of the Stack without removing it.
            self.piles[pile_name].peek().flip_face_up()

        # ---- The remaining 24 cards go into the stock Queue ---------
        # They stay face down. The first one enqueued is the first one
        # that will be drawn (FIFO).
        while next_card < len(deck):
            self._place(deck[next_card], "stock")
            next_card += 1

        # 'deck' is a local variable, so the list is discarded when this
        # method ends. From now on every card lives in exactly one pile.

    def _place(self, card, pile_name):
        """Put a card on top of a pile AND record where it is.

        This is the ONLY place where dealing puts cards into piles, so the
        card_locations dictionary can never be forgotten or get out of date.
        (The leading underscore means "for use inside this class only".)
        """
        pile = self.piles[pile_name]
        if pile_name == "stock":
            pile.enqueue(card)   # the stock is a Queue
        else:
            pile.push(card)      # every other pile is a Stack

        self.card_locations[card.card_id] = {"card": card, "pile": pile_name}
