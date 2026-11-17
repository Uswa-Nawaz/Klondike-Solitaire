"""
Pygame interface for Klondike Solitaire.

The interface contains NO game rules and keeps NO copy of the cards.
Every frame it reads the piles from KlondikeGame and draws them, and every
click is turned into a call to one of the game's public methods
(move_cards, draw_from_stock, can_pick_up, undo, redo, new_game, ...).

The only things the interface remembers are about the DISPLAY:
    selected_card_id  - the card the player has selected (or None)
    message, message_until - a short message and when it disappears
    start_ticks       - when the current game started (for the timer)
    finish_ticks      - when the game was won (stops the timer)
    click_targets     - the clickable rectangles of the frame just drawn
"""

import pygame

from card import RANK_LABELS

# ---------------------------------------------------------------------
# Sizes and positions (pixels)
# ---------------------------------------------------------------------
WINDOW_WIDTH = 900
WINDOW_HEIGHT = 700          # fits on 768-pixel-tall laptop screens
HEADER_HEIGHT = 48
MESSAGE_BAR_HEIGHT = 34

CARD_WIDTH = 80
CARD_HEIGHT = 112
CARD_RADIUS = 8
COLUMN_GAP = 28              # space between two columns
LEFT_MARGIN = (WINDOW_WIDTH - (7 * CARD_WIDTH + 6 * COLUMN_GAP)) // 2

TOP_ROW_Y = HEADER_HEIGHT + 16                 # stock, waste, foundations
TABLEAU_Y = TOP_ROW_Y + CARD_HEIGHT + 20       # the 7 columns
TABLEAU_BOTTOM = WINDOW_HEIGHT - MESSAGE_BAR_HEIGHT - 8

FACE_DOWN_GAP = 14           # how much of a face-down card shows in a column
FACE_UP_GAP = 28             # how much of a face-up card shows in a column
WASTE_FAN_GAP = 30           # Draw 3: sideways overlap (wide enough for "10♥")

MESSAGE_DURATION_MS = 3000   # how long an error message stays visible

# ---------------------------------------------------------------------
# Colours (red, green, blue)
# ---------------------------------------------------------------------
FELT = (22, 92, 54)
FELT_DARK = (14, 64, 38)
HEADER_COLOUR = (12, 48, 30)
SHADOW = (9, 45, 27)
SLOT_OUTLINE = (70, 140, 100)
CARD_FACE = (250, 249, 244)
CARD_BORDER = (170, 170, 165)
CARD_RED = (196, 32, 44)
CARD_BLACK = (28, 28, 34)
CARD_BACK = (38, 72, 140)
CARD_BACK_LINES = (78, 112, 180)
HIGHLIGHT = (255, 204, 64)
TEXT_LIGHT = (236, 240, 236)
TEXT_MUTED = (150, 185, 165)
TEXT_ERROR = (255, 140, 125)
BUTTON = (34, 96, 64)
BUTTON_DISABLED = (28, 64, 46)

SUIT_SYMBOLS = {"hearts": "♥", "diamonds": "♦",
                "clubs": "♣", "spades": "♠"}
SUIT_LETTERS = {"hearts": "H", "diamonds": "D", "clubs": "C", "spades": "S"}

BUTTON_NAMES = ["new_game", "undo", "redo", "draw_mode"]


class SolitaireUI:
    """Draws a KlondikeGame and turns mouse clicks into game method calls."""

    def __init__(self, game):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Klondike Solitaire")
        self.clock = pygame.time.Clock()
        self.game = game

        self.load_fonts()
        self.buttons = self.create_button_rects()
        self.stock_rect = pygame.Rect(self.column_x(0), TOP_ROW_Y, CARD_WIDTH, CARD_HEIGHT)
        self.play_again_rect = pygame.Rect(0, 0, 160, 40)
        self.play_again_rect.center = (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 50)

        # Display-only state (see the module docstring).
        self.selected_card_id = None
        self.message = ""
        self.message_until = 0
        self.start_ticks = pygame.time.get_ticks()
        self.finish_ticks = None
        self.click_targets = []

    # ==================================================================
    # Setup helpers
    # ==================================================================

    def load_fonts(self):
        """Use Segoe UI Symbol (it draws the suit symbols); otherwise letters.

        Pygame's built-in font shows empty boxes instead of suit symbols,
        so if Segoe UI Symbol is not installed we fall back to H, D, C, S.
        """
        path = pygame.font.match_font("segoeuisymbol")
        if path is None:
            self.suit_text = SUIT_LETTERS
        else:
            self.suit_text = SUIT_SYMBOLS
        # Font(None, size) means pygame's built-in font.
        self.title_font = pygame.font.Font(path, 22)
        self.small_font = pygame.font.Font(path, 16)
        self.corner_font = pygame.font.Font(path, 17)
        self.centre_font = pygame.font.Font(path, 40)
        self.big_font = pygame.font.Font(path, 40)

    def create_button_rects(self):
        """Fixed positions of the four header buttons."""
        return {
            "new_game": pygame.Rect(220, 10, 100, 28),
            "undo": pygame.Rect(330, 10, 64, 28),
            "redo": pygame.Rect(404, 10, 64, 28),
            "draw_mode": pygame.Rect(478, 10, 120, 28),
        }

    def column_x(self, column):
        """Left edge of column 0..6 (the top row uses the same columns)."""
        return LEFT_MARGIN + column * (CARD_WIDTH + COLUMN_GAP)

    # ==================================================================
    # Main loop
    # ==================================================================

    def run(self):
        """Handle events and redraw about 30 times per second until closed."""
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.handle_click(event.pos)
            self.draw()
            pygame.display.flip()
            self.clock.tick(30)
        pygame.quit()

    # ==================================================================
    # Turning clicks into game actions
    # ==================================================================

    def handle_click(self, position):
        """Decide what a left click means and call the right game method."""
        for name, rect in self.buttons.items():
            if rect.collidepoint(position):
                self.press_button(name)
                return

        if self.game.is_won():
            # While the win overlay is shown, only its button works.
            if self.play_again_rect.collidepoint(position):
                self.start_new_game()
            return

        target = self.find_target(position)
        if target is None:
            self.selected_card_id = None      # clicked on bare felt
        elif target == ("pile", "stock"):
            self.selected_card_id = None
            self.game.draw_from_stock()
        elif self.selected_card_id is None:
            self.try_select(target)
        else:
            self.try_move(target)

    def find_target(self, position):
        """Translate a mouse position into ("card", card_id) or ("pile", name).

        While drawing a frame, every card and every pile slot adds its
        rectangle to self.click_targets, in drawing order. A card that is
        drawn later lies ON TOP of the cards drawn before it. So we search
        the list BACKWARDS: the first rectangle that contains the mouse is
        the top-most thing under the pointer. In a column, that means a
        partly covered card is found only on its visible strip, because its
        lower part is covered by the next card's rectangle. The rectangles
        use exactly the positions used for drawing (including compressed
        columns), so what you see is what you click.
        Returns None if the click hit nothing (bare felt).
        """
        for rect, kind, value in reversed(self.click_targets):
            if rect.collidepoint(position):
                return (kind, value)
        return None

    def try_select(self, target):
        """Nothing is selected yet: ask the game whether this card may be picked up."""
        kind, value = target
        if kind != "card":
            return
        if self.game.can_pick_up(value):
            self.selected_card_id = value
        else:
            self.show_message("That card can't be picked up")

    def try_move(self, target):
        """A card is selected: try to move it to the clicked pile."""
        kind, value = target
        if kind == "card" and value == self.selected_card_id:
            self.selected_card_id = None       # clicked it again: deselect
            return

        if kind == "card":
            destination = self.game.card_locations[value]["pile"]
        else:
            destination = value

        selected_pile = self.game.card_locations[self.selected_card_id]["pile"]
        if destination == selected_pile:
            # Clicked another card in the same pile: select that one instead.
            self.selected_card_id = None
            self.try_select(target)
            return

        moved, reason = self.game.move_cards(self.selected_card_id, destination)
        self.selected_card_id = None
        if not moved:
            self.show_message(reason)

    def press_button(self, name):
        """Header buttons. Every one of them clears the selection."""
        self.selected_card_id = None
        if name == "new_game":
            self.start_new_game()
        elif name == "undo":
            self.game.undo()
        elif name == "redo":
            self.game.redo()
        elif name == "draw_mode":
            if self.game.draw_count == 1:
                self.game.draw_count = 3
            else:
                self.game.draw_count = 1
            self.start_new_game()

    def start_new_game(self):
        """Deal a new game and reset the display-only state and the timer."""
        self.game.new_game()
        self.selected_card_id = None
        self.message = ""
        self.start_ticks = pygame.time.get_ticks()
        self.finish_ticks = None

    def show_message(self, text):
        self.message = text
        self.message_until = pygame.time.get_ticks() + MESSAGE_DURATION_MS

    # ==================================================================
    # Timer
    # ==================================================================

    def update_timer(self):
        """Stop the clock when the game is won (undo/redo never reset it)."""
        if self.game.is_won():
            if self.finish_ticks is None:
                self.finish_ticks = pygame.time.get_ticks()
        else:
            self.finish_ticks = None

    def elapsed_text(self):
        """Time since the game started, as mm:ss."""
        if self.finish_ticks is None:
            end = pygame.time.get_ticks()
        else:
            end = self.finish_ticks
        seconds = (end - self.start_ticks) // 1000
        return f"{seconds // 60:02d}:{seconds % 60:02d}"

    # ==================================================================
    # Drawing a whole frame
    # ==================================================================

    def draw(self):
        """Draw everything from the game's current state.

        click_targets is rebuilt from scratch, so it always matches what
        is on the screen in this frame.
        """
        self.click_targets = []
        self.update_timer()
        self.screen.fill(FELT)
        self.draw_header()
        self.draw_stock()
        self.draw_waste()
        self.draw_foundations()
        for column in range(7):
            self.draw_tableau_column(column)
        self.draw_message_bar()
        if self.game.is_won():
            self.draw_win_overlay()

    def draw_header(self):
        pygame.draw.rect(self.screen, HEADER_COLOUR, (0, 0, WINDOW_WIDTH, HEADER_HEIGHT))
        title = self.title_font.render("Klondike Solitaire", True, TEXT_LIGHT)
        self.screen.blit(title, title.get_rect(midleft=(20, HEADER_HEIGHT // 2)))

        self.draw_button("new_game", "New Game", True)
        self.draw_button("undo", "Undo", self.game.can_undo())
        self.draw_button("redo", "Redo", self.game.can_redo())
        self.draw_button("draw_mode", f"Mode: Draw {self.game.draw_count}", True)

        info = f"Moves: {self.game.move_count()}     Time: {self.elapsed_text()}"
        info_surface = self.small_font.render(info, True, TEXT_LIGHT)
        self.screen.blit(info_surface,
                         info_surface.get_rect(midright=(WINDOW_WIDTH - 20, HEADER_HEIGHT // 2)))

    def draw_button(self, name, label, enabled):
        rect = self.buttons[name]
        if enabled:
            background = BUTTON
            text_colour = TEXT_LIGHT
        else:
            background = BUTTON_DISABLED
            text_colour = TEXT_MUTED
        pygame.draw.rect(self.screen, background, rect, border_radius=6)
        text = self.small_font.render(label, True, text_colour)
        self.screen.blit(text, text.get_rect(center=rect.center))

    def draw_message_bar(self):
        bar = pygame.Rect(0, WINDOW_HEIGHT - MESSAGE_BAR_HEIGHT, WINDOW_WIDTH, MESSAGE_BAR_HEIGHT)
        pygame.draw.rect(self.screen, FELT_DARK, bar)
        if self.message and pygame.time.get_ticks() < self.message_until:
            text = self.small_font.render(self.message, True, TEXT_ERROR)
        else:
            hint = "Click a card to select it, then click where it should go."
            text = self.small_font.render(hint, True, TEXT_MUTED)
        self.screen.blit(text, text.get_rect(midleft=(20, bar.centery)))

    def draw_win_overlay(self):
        shade = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT - HEADER_HEIGHT), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 150))     # black, partly see-through
        self.screen.blit(shade, (0, HEADER_HEIGHT))

        panel = pygame.Rect(0, 0, 380, 220)
        panel.center = (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2)
        pygame.draw.rect(self.screen, HEADER_COLOUR, panel, border_radius=12)
        pygame.draw.rect(self.screen, HIGHLIGHT, panel, 2, border_radius=12)

        title = self.big_font.render("You won!", True, HIGHLIGHT)
        self.screen.blit(title, title.get_rect(center=(panel.centerx, panel.top + 50)))
        summary = f"Moves: {self.game.move_count()}     Time: {self.elapsed_text()}"
        summary_surface = self.small_font.render(summary, True, TEXT_LIGHT)
        self.screen.blit(summary_surface,
                         summary_surface.get_rect(center=(panel.centerx, panel.top + 100)))

        pygame.draw.rect(self.screen, BUTTON, self.play_again_rect, border_radius=8)
        label = self.small_font.render("Play again", True, TEXT_LIGHT)
        self.screen.blit(label, label.get_rect(center=self.play_again_rect.center))

    # ==================================================================
    # Drawing the piles
    # ==================================================================

    def draw_stock(self):
        """One face-down card if the stock has cards, else an empty slot.

        The whole slot is one click target: clicking it draws or recycles.
        """
        if self.game.piles["stock"].is_empty():
            self.draw_empty_slot(self.stock_rect, "")
            centre = self.stock_rect.center
            pygame.draw.circle(self.screen, SLOT_OUTLINE, centre, 18, 3)
        else:
            pygame.draw.rect(self.screen, SHADOW, self.stock_rect.move(2, 3),
                             border_radius=CARD_RADIUS)
            self.draw_card_back(self.stock_rect)
        self.add_target(self.stock_rect, "pile", "stock")

    def draw_waste(self):
        """Draw 1: the top card. Draw 3: the top three, overlapping sideways."""
        slot = pygame.Rect(self.column_x(1), TOP_ROW_Y, CARD_WIDTH, CARD_HEIGHT)
        self.draw_empty_slot(slot, "")
        self.add_target(slot, "pile", "waste")

        # Temporary list for drawing only (bottom to top); thrown away after.
        waste_cards = list(self.game.piles["waste"])
        if self.game.draw_count == 3:
            visible = waste_cards[-3:]
        else:
            visible = waste_cards[-1:]
        for index, card in enumerate(visible):
            rect = slot.move(index * WASTE_FAN_GAP, 0)
            self.draw_card(card, rect)

    def draw_foundations(self):
        """Foundations sit above columns 3-6; only the top card is visible."""
        for number in range(4):
            pile_name = f"foundation_{number}"
            slot = pygame.Rect(self.column_x(3 + number), TOP_ROW_Y, CARD_WIDTH, CARD_HEIGHT)
            self.draw_empty_slot(slot, "A")
            self.add_target(slot, "pile", pile_name)
            pile = self.game.piles[pile_name]
            if not pile.is_empty():
                self.draw_card(pile.peek(), slot)

    def draw_tableau_column(self, column):
        pile_name = f"tableau_{column}"
        slot = pygame.Rect(self.column_x(column), TABLEAU_Y, CARD_WIDTH, CARD_HEIGHT)
        self.draw_empty_slot(slot, "")
        self.add_target(slot, "pile", pile_name)

        cards = list(self.game.piles[pile_name])   # temporary, for drawing only
        positions = self.card_positions(cards)
        for card, y in zip(cards, positions):
            rect = pygame.Rect(slot.x, y, CARD_WIDTH, CARD_HEIGHT)
            self.draw_card(card, rect)

    def card_positions(self, cards):
        """Top y position of each card in a column, squeezing tall columns.

        Normally face-down cards show 14 px and face-up cards 28 px. If the
        column would reach below the bottom of the table, every gap is
        shrunk by the same factor so the last card still fits.
        """
        gaps = []
        for card in cards[:-1]:
            if card.face_up:
                gaps.append(FACE_UP_GAP)
            else:
                gaps.append(FACE_DOWN_GAP)

        available = TABLEAU_BOTTOM - TABLEAU_Y - CARD_HEIGHT
        total = sum(gaps)
        scale = 1.0
        if total > available:
            scale = available / total

        positions = []
        y = TABLEAU_Y
        for index in range(len(cards)):
            positions.append(round(y))
            if index < len(gaps):
                y += gaps[index] * scale
        return positions

    # ==================================================================
    # Drawing single cards
    # ==================================================================

    def draw_card(self, card, rect):
        """Draw one card (face up or down), highlight it, register its click area."""
        pygame.draw.rect(self.screen, SHADOW, rect.move(2, 3), border_radius=CARD_RADIUS)
        if card.face_up:
            self.draw_card_face(card, rect)
        else:
            self.draw_card_back(rect)
        if self.is_highlighted(card):
            pygame.draw.rect(self.screen, HIGHLIGHT, rect.inflate(4, 4), 3,
                             border_radius=CARD_RADIUS + 2)
        self.add_target(rect, "card", card.card_id)

    def draw_card_face(self, card, rect):
        pygame.draw.rect(self.screen, CARD_FACE, rect, border_radius=CARD_RADIUS)
        pygame.draw.rect(self.screen, CARD_BORDER, rect, 1, border_radius=CARD_RADIUS)
        if card.colour == "red":
            colour = CARD_RED
        else:
            colour = CARD_BLACK
        suit = self.suit_text[card.suit]
        label = RANK_LABELS.get(card.rank, str(card.rank))

        corner = self.corner_font.render(label + suit, True, colour)
        self.screen.blit(corner, (rect.x + 6, rect.y + 1))
        centre = self.centre_font.render(suit, True, colour)
        self.screen.blit(centre, centre.get_rect(center=(rect.centerx, rect.centery + 10)))

    def draw_card_back(self, rect):
        pygame.draw.rect(self.screen, CARD_BACK, rect, border_radius=CARD_RADIUS)
        inner = rect.inflate(-12, -12)
        # Diagonal stripes, clipped so they stay inside the inner frame.
        self.screen.set_clip(inner)
        for offset in range(0, inner.width + inner.height, 9):
            start = (inner.left + offset, inner.top)
            end = (inner.left + offset - inner.height, inner.bottom)
            pygame.draw.line(self.screen, CARD_BACK_LINES, start, end, 1)
        self.screen.set_clip(None)
        pygame.draw.rect(self.screen, CARD_BACK_LINES, inner, 2, border_radius=4)

    def draw_empty_slot(self, rect, label):
        pygame.draw.rect(self.screen, SLOT_OUTLINE, rect, 2, border_radius=CARD_RADIUS)
        if label:
            text = self.centre_font.render(label, True, SLOT_OUTLINE)
            self.screen.blit(text, text.get_rect(center=rect.center))

    def is_highlighted(self, card):
        """Is this card the selected card, or a card on top of it in a column?"""
        if self.selected_card_id is None:
            return False
        selected = self.game.card_locations[self.selected_card_id]
        if card is selected["card"]:
            return True
        here = self.game.card_locations[card.card_id]
        if here["pile"] != selected["pile"] or not here["pile"].startswith("tableau_"):
            return False
        # Same column: highlighted if it lies above the selected card.
        # (Display only - it does not decide what may move.)
        return self.position_in_pile(card) > self.position_in_pile(selected["card"])

    def position_in_pile(self, card):
        pile_name = self.game.card_locations[card.card_id]["pile"]
        index = 0
        for pile_card in self.game.piles[pile_name]:
            if pile_card is card:
                return index
            index += 1
        return -1

    def add_target(self, rect, kind, value):
        """Remember a clickable rectangle for this frame (see find_target)."""
        self.click_targets.append((rect, kind, value))
