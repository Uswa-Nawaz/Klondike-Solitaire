"""
Klondike Solitaire game logic (no graphics here).

Stage 3: game setup - creating the piles and dealing the cards.
Stage 4: moves and rules - moving cards, drawing, recycling, flipping, win.

Data structures used in this file:
    Array/List  - the shuffled deck (from card.py), read by position while dealing
    Stack       - 7 tableau columns, 4 foundations, the waste pile
    Queue       - the stock (draw pile)
    LinkedList  - inside every Stack/Queue; pop_many/push_many move a run
                  of tableau cards by relinking nodes
    HashMap     - two dictionaries: 'piles' and 'card_locations' (see new_game)

Rule for every move: CHECK FIRST, CHANGE SECOND. All checks only read the
piles; nothing is modified unless every check has passed, so an illegal
move leaves the whole game exactly as it was.
"""

from card import ACE, KING, create_deck, shuffle_deck
from data_structures import Queue, Stack

TABLEAU_COUNT = 7
FOUNDATION_COUNT = 4


class KlondikeGame:
    """Holds the whole game state and all the rules."""

    def __init__(self, rng=None):
        # How many cards one click on the stock draws: 1 (Draw 1) or 3 (Draw 3).
        self.draw_count = 1

        # Both dictionaries are filled in by new_game().
        self.piles = {}
        self.card_locations = {}

        self.new_game(rng)

    # ==================================================================
    # Setup
    # ==================================================================

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

    # ==================================================================
    # Public methods (used by the UI and the tests)
    # ==================================================================

    def move_cards(self, card_id, destination):
        """Move the chosen card, and every card on top of it, to 'destination'.

        Returns (True, "") if the move was made, or (False, reason) if it is
        illegal - in that case NOTHING in the game has changed.
        """
        # ---- Step 1: CHECK (only reads, never changes anything) -----
        # _check_pick_up finds the cards to move. For a tableau column it
        # WALKS the source pile from bottom to top (linked-list traversal)
        # until it reaches the chosen card, then collects that card and
        # every card above it. The number of cards to move is the length
        # of that collection. Cost: O(n), where n is the number of cards
        # in the source pile (at most 19 in a tableau column).
        error, source_name, moving_cards = self._check_pick_up(card_id)
        if error:
            return (False, error)

        error = self._check_destination(moving_cards, source_name, destination)
        if error:
            return (False, error)

        # ---- Step 2: CHANGE (all checks passed) ---------------------
        count = len(moving_cards)
        self._transfer(source_name, destination, count)
        flipped = self._flip_exposed_card(source_name)

        # Stage 5 (undo/redo) will record this move HERE, using:
        #   source_name, destination, count, flipped
        # 'flipped' tells undo whether to turn the source's top card
        # face down again after the cards are moved back.
        # (Until Stage 5 the variable is computed but not yet stored.)

        return (True, "")

    def draw_from_stock(self):
        """Draw from the stock, or recycle the waste if the stock is empty.

        Returns True if cards were drawn or recycled, False if both the
        stock and the waste are empty (nothing happens).
        """
        stock = self.piles["stock"]
        waste = self.piles["waste"]

        if stock.is_empty():
            if waste.is_empty():
                return False
            self._recycle_waste()
            # Stage 5 will record a "recycle" action HERE.
            return True

        # Draw up to draw_count cards (fewer if the stock runs out).
        drawn = 0
        while drawn < self.draw_count and not stock.is_empty():
            card = stock.dequeue()       # FIFO: the front card of the stock
            card.flip_face_up()
            self._place(card, "waste")   # push onto the waste + record location
            drawn += 1

        # Stage 5 will record a "draw" action of 'drawn' cards HERE.
        return True

    def can_pick_up(self, card_id):
        """True if the player may select this card (and the cards above it)."""
        error, _, _ = self._check_pick_up(card_id)
        return error == ""

    def is_won(self):
        """True when every foundation holds 13 cards (all 52 cards)."""
        for number in range(FOUNDATION_COUNT):
            if len(self.piles[f"foundation_{number}"]) != 13:
                return False
        return True

    # ==================================================================
    # Checks (these only READ the game; they never change it)
    # ==================================================================

    def _check_pick_up(self, card_id):
        """Can this card be picked up? Which cards would move with it?

        Returns (error, source_name, moving_cards):
            error        - "" if allowed, otherwise the reason
            source_name  - the pile the card is in
            moving_cards - a temporary Python list of the cards that would
                           move, from the chosen card up to the top. It only
                           holds references for checking and is thrown away.
        """
        if card_id not in self.card_locations:
            return ("Unknown card", None, [])

        # HashMap lookup, O(1): which card is this and which pile is it in?
        entry = self.card_locations[card_id]
        card = entry["card"]
        source_name = entry["pile"]
        source = self.piles[source_name]

        if source_name == "stock":
            return ("Cards in the stock cannot be moved", source_name, [])
        if not card.face_up:
            return ("Face-down cards cannot be moved", source_name, [])

        # Waste and foundations: only the top card may move.
        if not self._is_tableau(source_name):
            if source.peek() is not card:
                return ("Only the top card of this pile can be moved", source_name, [])
            return ("", source_name, [card])

        # Tableau: walk the column from bottom to top (O(n) traversal).
        # Once we reach the chosen card, collect it and everything above it.
        moving_cards = []
        found = False
        for pile_card in source:
            if pile_card is card:
                found = True
            if found:
                moving_cards.append(pile_card)

        # Every card in the group must sit legally on the one below it.
        for position in range(1, len(moving_cards)):
            lower = moving_cards[position - 1]
            upper = moving_cards[position]
            if not self._fits_on_tableau_card(upper, lower):
                return (
                    "The cards on top must go down by one and alternate colours",
                    source_name,
                    [],
                )

        return ("", source_name, moving_cards)

    def _check_destination(self, moving_cards, source_name, destination):
        """May these cards be placed on 'destination'? Returns "" or a reason."""
        if destination not in self.piles:
            return "Unknown destination"
        if destination == source_name:
            return "The cards are already in that pile"
        if destination in ("stock", "waste"):
            return "Cards cannot be placed on the stock or the waste"

        first = moving_cards[0]          # the bottom card of the moving group
        target = self.piles[destination]

        if self._is_tableau(destination):
            if target.is_empty():
                if first.rank != KING:
                    return "Only a King can go on an empty column"
                return ""
            top = target.peek()
            if first.colour == top.colour:
                return "Colours must alternate: red on black, black on red"
            if first.rank != top.rank - 1:
                return "The card must be exactly one rank lower"
            return ""

        # Otherwise the destination is a foundation.
        if self._is_foundation(source_name):
            return "Cards cannot move from one foundation to another"
        if len(moving_cards) != 1:
            return "Only one card at a time can go to a foundation"
        if target.is_empty():
            if first.rank != ACE:
                return "A foundation must start with an Ace"
            return ""
        top = target.peek()
        if first.suit != top.suit:
            return "A foundation must keep the same suit"
        if first.rank != top.rank + 1:
            return "The card must be exactly one rank higher"
        return ""

    def _fits_on_tableau_card(self, card, target):
        """Tableau rule: opposite colour and exactly one rank lower."""
        return card.colour != target.colour and card.rank == target.rank - 1

    def _is_tableau(self, pile_name):
        return pile_name.startswith("tableau_")

    def _is_foundation(self, pile_name):
        return pile_name.startswith("foundation_")

    # ==================================================================
    # Changes (the ONLY methods that put cards into piles)
    # ==================================================================

    def _place(self, card, pile_name):
        """Put ONE card on top of a pile AND record where it is.

        Used for dealing, drawing and recycling. Together with _transfer,
        this is the only code that puts cards into piles, so the
        card_locations dictionary can never be forgotten or get out of date.
        (The leading underscore means "for use inside this class only".)
        """
        pile = self.piles[pile_name]
        if pile_name == "stock":
            pile.enqueue(card)   # the stock is a Queue
        else:
            pile.push(card)      # every other pile is a Stack

        # HashMap update, O(1).
        self.card_locations[card.card_id] = {"card": card, "pile": pile_name}

    def _transfer(self, source_name, destination, count):
        """Move the top 'count' cards of one Stack onto another, keeping order.

        Uses the linked list underneath the Stacks: no card is copied,
        the existing nodes are unlinked from one list and linked to another.
        """
        # pop_many: walk 'count' nodes back from the top (O(count)) and cut
        # them off in O(1). 'group' is a LinkedList holding those nodes.
        group = self.piles[source_name].pop_many(count)

        # HashMap update for every moving card. This must happen BEFORE
        # push_many, because push_many hands the nodes over to the
        # destination and leaves 'group' empty.
        for card in group:
            self.card_locations[card.card_id]["pile"] = destination

        # push_many: link the group onto the destination's top in O(1).
        self.piles[destination].push_many(group)

    def _flip_exposed_card(self, pile_name):
        """After cards leave a tableau column, turn its new top card face up.

        Returns True if a card was flipped, False otherwise. The dictionary
        needs no update: it refers to the same Card object.
        """
        if not self._is_tableau(pile_name):
            return False
        column = self.piles[pile_name]
        if column.is_empty():
            return False
        top = column.peek()
        if top.face_up:
            return False
        top.flip_face_up()
        return True

    def _recycle_waste(self):
        """Move every waste card back into the stock in the ORIGINAL draw order.

        If cards were drawn in the order c1, c2, ... cN, the waste Stack holds
        c1 at the bottom and cN on top. Popping alone would give cN first
        (the wrong order), so we reverse twice:

          1. pop every card from the waste and push it onto a temporary
             Stack. Each pop/push reverses the order, so c1 ends up on top.
          2. pop from the temporary Stack (c1, c2, ... cN) and enqueue each
             card into the stock. c1 is at the front again, as originally.
        """
        waste = self.piles["waste"]
        temporary = Stack()

        # Step 1: waste -> temporary stack (reverses the order).
        while not waste.is_empty():
            temporary.push(waste.pop())

        # Step 2: temporary stack -> stock queue, face down.
        while not temporary.is_empty():
            card = temporary.pop()
            card.flip_face_down()
            self._place(card, "stock")   # enqueue + record location
