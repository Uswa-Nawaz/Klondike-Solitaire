"""
The card table of the PyQt6 interface: measuring, drawing and clicks.

The table contains NO game rules and keeps NO copy of the cards. Every time
Qt asks it to repaint, it reads the piles from KlondikeGame and draws them.
A click is turned into a call to a public game method (draw_from_stock,
can_pick_up, move_cards); the game alone decides what is legal.

One function, compute_layout(), measures everything. It returns a list of
(rectangle, kind, value) in DRAWING ORDER, where kind is "pile" (an empty
slot or the stock) or "card", and value is a pile name or a card id.
Drawing walks this list forwards; finding what was clicked walks the SAME
list backwards (the last thing drawn is on top), so what you see is always
what you click.
"""

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QPolygonF
from PyQt6.QtWidgets import QWidget

from card import RANK_LABELS

# ---------------------------------------------------------------------
# Colours
# ---------------------------------------------------------------------
CARD_CREAM = QColor("#fbf5e6")
CARD_EDGE = QColor("#d6c49a")
CARD_RED = QColor("#b3261e")
CARD_BLACK = QColor("#1e1e24")
GOLD = QColor("#c9a54c")
FRAME_FILL = QColor("#f4e7c3")
BACK_GREEN = QColor("#1c5539")
BACK_PATTERN = QColor(201, 165, 76, 110)     # gold, partly see-through
SHADOW = QColor(0, 0, 0, 70)
SLOT_EDGE = QColor(255, 255, 255, 70)
SLOT_FILL = QColor(0, 0, 0, 30)
SLOT_TEXT = QColor(255, 255, 255, 55)
BADGE_TEXT = QColor("#1e1e24")

SUIT_SYMBOLS = {"hearts": "♥", "diamonds": "♦",
                "clubs": "♣", "spades": "♠"}

# ---------------------------------------------------------------------
# Proportions (relative to the card size, so everything scales together)
# ---------------------------------------------------------------------
# ---------------------------------------------------------------------
# Pip positions for number cards 2-10 (the standard playing-card layout)
# ---------------------------------------------------------------------
# Each pip is (x, y) as a fraction of the card's width and height:
# x = 0.32 left column, 0.5 centre, 0.68 right column;
# y = 0.25 top row ... 0.75 bottom row (0.5 is the middle of the card).
# Pips below the middle (y > 0.5) are drawn upside down, like real cards.
PIP_LAYOUTS = {
    2: [(0.5, 0.25), (0.5, 0.75)],
    3: [(0.5, 0.25), (0.5, 0.5), (0.5, 0.75)],
    4: [(0.32, 0.25), (0.68, 0.25),
        (0.32, 0.75), (0.68, 0.75)],
    5: [(0.32, 0.25), (0.68, 0.25),
        (0.5, 0.5),
        (0.32, 0.75), (0.68, 0.75)],
    6: [(0.32, 0.25), (0.68, 0.25),
        (0.32, 0.5), (0.68, 0.5),
        (0.32, 0.75), (0.68, 0.75)],
    7: [(0.32, 0.25), (0.68, 0.25),
        (0.5, 0.375),
        (0.32, 0.5), (0.68, 0.5),
        (0.32, 0.75), (0.68, 0.75)],
    8: [(0.32, 0.25), (0.68, 0.25),
        (0.5, 0.375),
        (0.32, 0.5), (0.68, 0.5),
        (0.5, 0.625),
        (0.32, 0.75), (0.68, 0.75)],
    9: [(0.32, 0.25), (0.68, 0.25),
        (0.32, 0.417), (0.68, 0.417),
        (0.5, 0.5),
        (0.32, 0.583), (0.68, 0.583),
        (0.32, 0.75), (0.68, 0.75)],
    10: [(0.32, 0.25), (0.68, 0.25),
         (0.5, 0.333),
         (0.32, 0.417), (0.68, 0.417),
         (0.32, 0.583), (0.68, 0.583),
         (0.5, 0.667),
         (0.32, 0.75), (0.68, 0.75)],
}

CARD_RATIO = 1.4                 # card height = 1.4 x card width
FACE_DOWN_GAP = 0.11             # visible part of a face-down card (x height)
FACE_UP_GAP = 0.23               # visible part of a face-up card (x height)
WASTE_FAN_GAP = 0.28             # Draw 3 sideways overlap (x width)


class TableWidget(QWidget):
    """Draws the stock, waste, foundations and 7 columns of a KlondikeGame."""

    # Custom signals. The game page connects to them:
    #   changed - "the game may have changed": refresh labels, check for a win
    #   message - the reason an action was refused, to show in the message bar
    changed = pyqtSignal()
    message = pyqtSignal(str)

    def __init__(self, game, parent=None):
        super().__init__(parent)
        self.game = game
        self.selected_card_id = None     # display-only: the selected card
        self.setMinimumSize(720, 460)

    # ==================================================================
    # Measuring
    # ==================================================================

    def card_size(self):
        """Biggest card that fits both the width and the height of the table.

        Width:  7 columns plus small margins need about 8.1 card widths.
        Height: margin + top row + gap + about 2.8 card heights for the
                columns need about 4.35 card heights.
        """
        width_limit = self.width() / 8.1
        height_limit = self.height() / 4.35 / CARD_RATIO
        card_width = min(width_limit, height_limit)
        return card_width, card_width * CARD_RATIO

    def compute_layout(self):
        """Measure every slot and card. Returns [(QRectF, kind, value), ...]."""
        card_width, card_height = self.card_size()

        # Spread the columns over the available width (with limits), so a
        # wide window has no big empty strips at the sides.
        gap = (self.width() - 7 * card_width) / 8
        gap = max(0.15 * card_width, min(gap, 0.55 * card_width))
        left = (self.width() - 7 * card_width - 6 * gap) / 2
        top = 0.18 * card_height
        tableau_top = top + card_height + 0.28 * card_height
        tableau_bottom = self.height() - 0.10 * card_height

        def slot(column, y):
            x = left + column * (card_width + gap)
            return QRectF(x, y, card_width, card_height)

        layout = []

        # Stock (one target for the whole pile) and waste.
        layout.append((slot(0, top), "pile", "stock"))
        waste_slot = slot(1, top)
        layout.append((waste_slot, "pile", "waste"))
        waste_cards = list(self.game.piles["waste"])     # temporary, for drawing
        visible = waste_cards[-self.game.draw_count:]
        for index, card in enumerate(visible):
            rect = waste_slot.translated(index * WASTE_FAN_GAP * card_width, 0)
            layout.append((rect, "card", card.card_id))

        # Foundations above columns 3-6: the slot and only the top card.
        for number in range(4):
            pile_name = f"foundation_{number}"
            rect = slot(3 + number, top)
            layout.append((rect, "pile", pile_name))
            pile = self.game.piles[pile_name]
            if not pile.is_empty():
                layout.append((rect, "card", pile.peek().card_id))

        # The 7 columns.
        for column in range(7):
            pile_name = f"tableau_{column}"
            rect = slot(column, tableau_top)
            layout.append((rect, "pile", pile_name))
            cards = list(self.game.piles[pile_name])     # temporary, for drawing
            positions = self.card_positions(cards, tableau_top, tableau_bottom, card_height)
            for card, y in zip(cards, positions):
                layout.append((QRectF(rect.x(), y, card_width, card_height),
                               "card", card.card_id))
        return layout

    def card_positions(self, cards, top, bottom, card_height):
        """Top y of each card in a column; tall columns are squeezed to fit."""
        gaps = []
        for card in cards[:-1]:
            if card.face_up:
                gaps.append(FACE_UP_GAP * card_height)
            else:
                gaps.append(FACE_DOWN_GAP * card_height)

        available = bottom - top - card_height
        total = sum(gaps)
        scale = 1.0
        if total > available > 0:
            scale = available / total

        positions = []
        y = top
        for index in range(len(cards)):
            positions.append(y)
            if index < len(gaps):
                y += gaps[index] * scale
        return positions

    # ==================================================================
    # Drawing
    # ==================================================================

    def paintEvent(self, event):
        """Qt calls this whenever the table must be redrawn."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        # Highlighting: in the layout list, every pile's slot comes before
        # that pile's cards. Once we meet the selected card, it and every
        # later card of the SAME pile are outlined (the run that would move).
        highlighting = False
        for rect, kind, value in self.compute_layout():
            if kind == "pile":
                highlighting = False          # a new pile starts here
                self.draw_slot(painter, rect, value)
            else:
                if value == self.selected_card_id:
                    highlighting = True
                # HashMap lookup: card id -> the Card object itself.
                card = self.game.card_locations[value]["card"]
                self.draw_card(painter, rect, card, highlighting)
        painter.end()

    # ==================================================================
    # Clicks
    # ==================================================================

    def mousePressEvent(self, event):
        """Qt calls this when a mouse button is pressed on the table."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.handle_click(event.position())

    def handle_click(self, position):
        """Decide what a click means and call the right game method."""
        target = self.find_target(position)
        if target is None:
            self.selected_card_id = None          # bare felt: deselect
        elif target == ("pile", "stock"):
            self.selected_card_id = None
            self.game.draw_from_stock()           # draws, or recycles the waste
        elif self.selected_card_id is None:
            self.try_select(target)
        else:
            self.try_move(target)
        self.update()                             # ask Qt to repaint the table
        self.changed.emit()

    def find_target(self, position):
        """Translate a click position into ("card", card_id) or ("pile", name).

        compute_layout() lists every slot and card in DRAWING order, using
        exactly the same rectangles that paintEvent draws (also in squeezed
        columns and the Draw 3 fan). A card drawn later lies on top, so we
        search the list BACKWARDS and return the first rectangle that
        contains the click: the top-most thing under the mouse. A partly
        covered card is therefore found only on its visible strip.
        Returns None for a click on bare felt.
        """
        for rect, kind, value in reversed(self.compute_layout()):
            if rect.contains(position):
                return (kind, value)
        return None

    def try_select(self, target):
        """Nothing selected yet: the game decides whether this card may be picked up."""
        kind, value = target
        if kind != "card":
            return
        if self.game.can_pick_up(value):
            self.selected_card_id = value
        else:
            self.message.emit("That card can't be picked up")

    def try_move(self, target):
        """A card is selected: ask the game to move it to the clicked pile."""
        kind, value = target
        if kind == "card" and value == self.selected_card_id:
            self.selected_card_id = None          # clicked again: deselect
            return

        if kind == "card":
            destination = self.game.card_locations[value]["pile"]
        else:
            destination = value

        selected_pile = self.game.card_locations[self.selected_card_id]["pile"]
        if destination == selected_pile:
            # Another card in the same pile: select that one instead.
            self.selected_card_id = None
            self.try_select(target)
            return

        moved, reason = self.game.move_cards(self.selected_card_id, destination)
        self.selected_card_id = None
        if not moved:
            self.message.emit(reason)

    def clear_selection(self):
        self.selected_card_id = None
        self.update()

    def draw_slot(self, painter, rect, pile_name):
        """An empty place on the table (the stock is drawn here too)."""
        radius = rect.width() * 0.08
        if pile_name == "stock" and not self.game.piles["stock"].is_empty():
            self.draw_shadow(painter, rect)
            self.draw_card_back(painter, rect)
            self.draw_stock_badge(painter, rect, len(self.game.piles["stock"]))
            return

        painter.setPen(QPen(SLOT_EDGE, 1.5))
        painter.setBrush(SLOT_FILL)
        painter.drawRoundedRect(rect, radius, radius)

        if pile_name.startswith("foundation_"):
            self.draw_centred_text(painter, rect, "A", SLOT_TEXT, rect.width() * 0.4)
        elif pile_name == "stock":
            # Empty stock: a circle means "click to turn the waste over".
            painter.setPen(QPen(SLOT_TEXT, rect.width() * 0.04))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            size = rect.width() * 0.36
            painter.drawEllipse(rect.center(), size / 2, size / 2)

    def draw_card(self, painter, rect, card, highlighted):
        self.draw_shadow(painter, rect)
        if card.face_up:
            self.draw_card_face(painter, rect, card)
        else:
            self.draw_card_back(painter, rect)
        if highlighted:
            painter.setPen(QPen(GOLD, 3))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            radius = rect.width() * 0.09
            painter.drawRoundedRect(rect.adjusted(-2, -2, 2, 2), radius, radius)

    def draw_shadow(self, painter, rect):
        radius = rect.width() * 0.08
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(SHADOW)
        painter.drawRoundedRect(rect.translated(0, rect.height() * 0.02), radius, radius)

    def draw_card_face(self, painter, rect, card):
        """Cream card, corners top-left and bottom-right, then the centre."""
        radius = rect.width() * 0.08
        painter.setPen(QPen(CARD_EDGE, 1))
        painter.setBrush(CARD_CREAM)
        painter.drawRoundedRect(rect, radius, radius)

        if card.colour == "red":
            colour = CARD_RED
        else:
            colour = CARD_BLACK
        label = RANK_LABELS.get(card.rank, str(card.rank))
        corner_text = label + SUIT_SYMBOLS[card.suit]

        self.draw_corner(painter, rect, corner_text, colour)
        # Bottom-right corner: move the origin to the card's bottom-right
        # point and turn the painter 180 degrees, then draw the same corner.
        painter.save()
        painter.translate(rect.right(), rect.bottom())
        painter.rotate(180)
        self.draw_corner(painter, QRectF(0, 0, rect.width(), rect.height()),
                         corner_text, colour)
        painter.restore()

        if card.rank > 10:
            self.draw_face_frame(painter, rect, label, card.suit, colour)
        elif card.rank == 1:
            self.draw_centred_text(painter, rect, SUIT_SYMBOLS[card.suit],
                                   colour, rect.width() * 0.6)
        else:
            self.draw_pips(painter, rect, card, colour)

    def draw_pips(self, painter, rect, card, colour):
        """Number cards: one suit symbol per pip position in PIP_LAYOUTS."""
        font = QFont("Segoe UI")
        font.setPixelSize(round(rect.width() * 0.17))
        painter.setFont(font)
        painter.setPen(colour)
        half = rect.width() * 0.11
        symbol = SUIT_SYMBOLS[card.suit]

        for x_fraction, y_fraction in PIP_LAYOUTS[card.rank]:
            # Move the painter's origin to the pip's centre, so turning it
            # upside down (rotate 180) spins the pip around its own middle.
            painter.save()
            painter.translate(rect.x() + x_fraction * rect.width(),
                              rect.y() + y_fraction * rect.height())
            if y_fraction > 0.5:
                painter.rotate(180)
            painter.drawText(QRectF(-half, -half, 2 * half, 2 * half),
                             Qt.AlignmentFlag.AlignCenter, symbol)
            painter.restore()

    def draw_corner(self, painter, rect, text, colour):
        font = QFont("Segoe UI")
        font.setPixelSize(max(9, round(rect.width() * 0.17)))
        font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.setPen(colour)
        pad_x = rect.width() * 0.07
        pad_y = rect.height() * 0.01
        area = QRectF(rect.x() + pad_x, rect.y() + pad_y, rect.width(), rect.height() * 0.25)
        painter.drawText(area, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, text)

    def draw_face_frame(self, painter, rect, letter, suit, colour):
        """J, Q, K: a gold double frame with corner diamonds and a big letter."""
        width = rect.width()
        frame = rect.adjusted(width * 0.2, rect.height() * 0.2,
                              -width * 0.2, -rect.height() * 0.2)
        radius = width * 0.05

        painter.setPen(QPen(GOLD, max(1.5, width * 0.025)))
        painter.setBrush(FRAME_FILL)
        painter.drawRoundedRect(frame, radius, radius)
        inset = width * 0.04
        painter.setPen(QPen(GOLD, 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(frame.adjusted(inset, inset, -inset, -inset), radius, radius)

        for corner in [frame.topLeft(), frame.topRight(),
                       frame.bottomLeft(), frame.bottomRight()]:
            self.draw_diamond(painter, corner, width * 0.045)

        letter_font = QFont("Georgia")
        letter_font.setPixelSize(round(width * 0.42))
        letter_font.setBold(True)
        painter.setFont(letter_font)
        painter.setPen(colour)
        upper = QRectF(frame.x(), frame.y(), frame.width(), frame.height() * 0.68)
        painter.drawText(upper, Qt.AlignmentFlag.AlignCenter, letter)

        lower = QRectF(frame.x(), frame.y() + frame.height() * 0.6,
                       frame.width(), frame.height() * 0.32)
        self.draw_centred_text(painter, lower, SUIT_SYMBOLS[suit], colour, width * 0.16)

    def draw_diamond(self, painter, centre, size):
        diamond = QPolygonF([
            QPointF(centre.x(), centre.y() - size),
            QPointF(centre.x() + size, centre.y()),
            QPointF(centre.x(), centre.y() + size),
            QPointF(centre.x() - size, centre.y()),
        ])
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(GOLD)
        painter.drawPolygon(diamond)

    def draw_card_back(self, painter, rect):
        """Green back with a gold lattice inside a gold frame."""
        radius = rect.width() * 0.08
        painter.setPen(QPen(CARD_EDGE, 1))
        painter.setBrush(BACK_GREEN)
        painter.drawRoundedRect(rect, radius, radius)

        inset = rect.width() * 0.08
        inner = rect.adjusted(inset, inset, -inset, -inset)
        clip = QPainterPath()
        clip.addRoundedRect(inner, radius * 0.6, radius * 0.6)
        painter.save()
        painter.setClipPath(clip)
        painter.setPen(QPen(BACK_PATTERN, 1))
        step = rect.width() * 0.12
        offset = -inner.height()
        while offset < inner.width():
            x = inner.left() + offset
            painter.drawLine(QPointF(x, inner.top()),
                             QPointF(x + inner.height(), inner.bottom()))
            painter.drawLine(QPointF(x + inner.height(), inner.top()),
                             QPointF(x, inner.bottom()))
            offset += step
        painter.restore()

        painter.setPen(QPen(GOLD, max(1.0, rect.width() * 0.015)))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(inner, radius * 0.6, radius * 0.6)

    def draw_stock_badge(self, painter, rect, count):
        """Small gold circle on the stock showing how many cards are left."""
        size = rect.width() * 0.3
        centre = QPointF(rect.right() - size * 0.75, rect.bottom() - size * 0.75)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(GOLD)
        painter.drawEllipse(centre, size / 2, size / 2)
        badge = QRectF(centre.x() - size / 2, centre.y() - size / 2, size, size)
        self.draw_centred_text(painter, badge, str(count), BADGE_TEXT, size * 0.5, bold=True)

    def draw_centred_text(self, painter, rect, text, colour, pixel_size, bold=False):
        font = QFont("Segoe UI")
        font.setPixelSize(max(8, round(pixel_size)))
        font.setBold(bold)
        painter.setFont(font)
        painter.setPen(colour)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
