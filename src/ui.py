"""
PyQt6 interface for Klondike Solitaire: the window and its pages.

    MainWindow        - the window; shows one page at a time (QStackedWidget)
                        and connects the page buttons that switch pages
    MenuPage          - title, suit row, Play / Instructions / Exit
    InstructionsPage  - rules and controls, Back
    GamePage          - top bar, the card table (TableWidget), message bar,
                        and the game timer
    WinPage           - "You won!", moves and time, Play Again / Menu

The interface contains NO game rules and keeps NO copy of the game state.
Besides the selected card (in TableWidget), it only remembers display
information: the current message and the timer.
"""

import time

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QGuiApplication, QPainter, QPen, QPolygonF
from PyQt6.QtWidgets import (QHBoxLayout, QLabel, QMainWindow, QPushButton,
                             QStackedWidget, QVBoxLayout, QWidget)

from table_view import SUIT_SYMBOLS, TableWidget

GOLD = QColor("#c9a54c")
MESSAGE_NORMAL = "#f3ead2"     # cream
MESSAGE_ERROR = "#ff8a73"      # warm red
MESSAGE_DURATION_MS = 3000
HINT = "Click a card to select it, then click where it should go."

INSTRUCTIONS_HTML = """
<p><b>Goal.</b> Move all 52 cards onto the four foundations (top right):
one pile per suit, from Ace up to King.</p>

<p><b>Stock and waste.</b> Click the stock (top left) to turn over one card
(Draw 1) or three cards (Draw 3) onto the waste. Only the top waste card
can be played. When the stock is empty, click it again to turn the waste
back over.</p>

<p><b>Columns.</b> Build downwards in alternating colours, for example a
red 6 on a black 7. You can move a run of face-up cards together. Only a
King can go into an empty column. A face-down card turns over when it is
uncovered.</p>

<p><b>Foundations.</b> Start each one with an Ace, then add the 2, 3 ...
up to the King of the same suit. A card can also be moved back from a
foundation to a column.</p>

<p><b>Controls.</b> Click a card to select it (it is outlined in gold), then
click the pile where it should go. Click it again to cancel.
<b>Undo</b> and <b>Redo</b> take back or repeat moves. <b>New Game</b> deals
again. <b>Mode</b> switches between Draw 1 and Draw 3 and starts a new
game. <b>Menu</b> returns to the start menu; your game is kept.</p>
"""

# Qt "style sheet": CSS-like rules for colours, fonts and borders.
# '#name' targets a widget whose objectName is 'name'.
STYLE_SHEET = """
QStackedWidget#background {
    background: qradialgradient(cx:0.5, cy:0.35, radius:0.95,
                                stop:0 #217049, stop:1 #0c3622);
}

/* ---- Menu, instructions and win pages ---- */
QLabel#title { color: #e3c46d; font: bold 46pt "Georgia"; }
QLabel#pageTitle { color: #e3c46d; font: bold 32pt "Georgia"; }
QLabel#suitRow { color: #c9a54c; font: 22pt "Segoe UI"; }
QLabel#bodyText { color: #f3ead2; font: 12.5pt "Segoe UI"; }
QLabel#winSummary { color: #f3ead2; font: 15pt "Segoe UI"; }
QPushButton#menuButton, QPushButton#primaryButton {
    border-radius: 12px;
    padding: 12px;
    min-width: 260px;
    font: 15pt "Segoe UI";
}
QPushButton#menuButton {
    background: #16492f; color: #f3ead2; border: 1px solid #c9a54c;
}
QPushButton#menuButton:hover { background: #1f5f3e; }
QPushButton#menuButton:pressed { background: #0f3523; }
/* Play / Play Again: filled gold, like New Game */
QPushButton#primaryButton {
    background: #d4af4f; color: #1b1b1b; border: 1px solid #e8cc7a;
    font-weight: bold;
}
QPushButton#primaryButton:hover { background: #e2c062; }
QPushButton#primaryButton:pressed { background: #b8953d; }

/* ---- Game page: bars ---- */
QWidget#topBar { background: rgba(5, 30, 18, 200); }
QLabel#counter { color: #f3ead2; font: 12pt "Segoe UI"; padding: 0 10px; }
QLabel#messageBar {
    background: rgba(5, 30, 18, 200);
    color: #f3ead2;
    padding: 12px 20px;
    font: 12pt "Segoe UI";
}

/* ---- Game page: top buttons, coloured by purpose ---- */
QWidget#topBar QPushButton {
    border-radius: 8px;
    padding: 9px 20px;
    font: 12pt "Segoe UI";
}
/* New Game: filled gold - the main action */
QPushButton#newGameButton {
    background: #d4af4f; color: #1b1b1b; border: 1px solid #e8cc7a;
    font-weight: bold;
}
QPushButton#newGameButton:hover { background: #e2c062; }
QPushButton#newGameButton:pressed { background: #b8953d; }
/* Undo and Redo: cream outline - a matching pair */
QPushButton#undoButton, QPushButton#redoButton {
    background: transparent; color: #f3ead2; border: 1.5px solid #f3ead2;
}
QPushButton#undoButton:hover, QPushButton#redoButton:hover {
    background: rgba(243, 234, 210, 30);
}
/* Mode: green with a gold outline - a setting */
QPushButton#modeButton {
    background: #16492f; color: #f3ead2; border: 1.5px solid #c9a54c;
}
QPushButton#modeButton:hover { background: #1f5f3e; }
/* Menu: dark and subtle - navigation */
QPushButton#menuNavButton {
    background: rgba(0, 0, 0, 70); color: #b9cdbf;
    border: 1px solid rgba(255, 255, 255, 45);
}
QPushButton#menuNavButton:hover { color: #f3ead2; }
/* Any disabled top button: clearly greyed out */
QWidget#topBar QPushButton:disabled {
    background: transparent; color: #5f7466; border: 1.5px solid #3f5548;
}
"""


# ======================================================================
# Small shared helpers
# ======================================================================

def make_button(text, object_name):
    """A QPushButton whose objectName picks its style in STYLE_SHEET."""
    button = QPushButton(text)
    button.setObjectName(object_name)
    return button


def make_label(text, object_name):
    label = QLabel(text)
    label.setObjectName(object_name)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return label


def centre_panel(page, panel):
    """Place 'panel' in the middle of 'page' using stretchable empty space."""
    row = QHBoxLayout()
    row.addStretch(1)
    row.addWidget(panel)
    row.addStretch(1)
    layout = QVBoxLayout(page)
    layout.addStretch(1)
    layout.addLayout(row)
    layout.addStretch(1)


def paint_gold_panel(painter, rect):
    """Dark panel with a double gold border and gold diamond ornaments."""
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(GOLD, 2))
    painter.setBrush(QColor(5, 30, 18, 120))
    painter.drawRoundedRect(rect, 18, 18)

    inner = rect.adjusted(9, 9, -9, -9)
    painter.setPen(QPen(QColor(201, 165, 76, 120), 1))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRoundedRect(inner, 12, 12)

    # Diamonds on the four corners and in the middle of the top/bottom edges.
    points = [rect.topLeft(), rect.topRight(), rect.bottomLeft(), rect.bottomRight(),
              QPointF(rect.center().x(), rect.top()),
              QPointF(rect.center().x(), rect.bottom())]
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(GOLD)
    for point in points:
        size = 8
        painter.drawPolygon(QPolygonF([
            QPointF(point.x(), point.y() - size),
            QPointF(point.x() + size, point.y()),
            QPointF(point.x(), point.y() + size),
            QPointF(point.x() - size, point.y()),
        ]))


# ======================================================================
# The window
# ======================================================================

class MainWindow(QMainWindow):
    """The application window. Holds the game and shows one page at a time."""

    def __init__(self, game):
        super().__init__()
        self.game = game
        self.setWindowTitle("Klondike Solitaire")

        # A QStackedWidget holds several pages and shows exactly one.
        self.stack = QStackedWidget()
        self.stack.setObjectName("background")
        self.menu_page = MenuPage()
        self.instructions_page = InstructionsPage()
        self.game_page = GamePage(game)
        self.win_page = WinPage()
        for page in [self.menu_page, self.instructions_page,
                     self.game_page, self.win_page]:
            self.stack.addWidget(page)
        self.setCentralWidget(self.stack)
        self.setStyleSheet(STYLE_SHEET)

        # Signals -> slots: "when this button is clicked, run this method".
        self.menu_page.play_button.clicked.connect(self.play)
        self.menu_page.instructions_button.clicked.connect(self.show_instructions)
        self.menu_page.exit_button.clicked.connect(self.close)
        self.instructions_page.back_button.clicked.connect(self.show_menu)
        self.game_page.menu_button.clicked.connect(self.show_menu)
        self.game_page.game_won.connect(self.show_win)
        self.win_page.play_again_button.clicked.connect(self.play_again)
        self.win_page.menu_button.clicked.connect(self.show_menu)

        self.open_large()
        self.show_menu()

    def open_large(self):
        """Open at 85% of the screen; the user can maximise the window."""
        self.setMinimumSize(1000, 660)
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            area = screen.availableGeometry()
            self.resize(max(1000, int(area.width() * 0.85)),
                        max(660, int(area.height() * 0.85)))

    # ---- page switching -------------------------------------------------

    def show_menu(self):
        self.game_page.pause_timer()
        self.stack.setCurrentWidget(self.menu_page)

    def show_instructions(self):
        self.game_page.pause_timer()
        self.stack.setCurrentWidget(self.instructions_page)

    def show_game(self):
        self.stack.setCurrentWidget(self.game_page)
        self.game_page.resume_timer()

    def show_win(self):
        self.win_page.set_summary(self.game.move_count(), self.game_page.time_text())
        self.stack.setCurrentWidget(self.win_page)

    def play(self):
        """Menu -> Play returns to the current game (a new one if it was won)."""
        if self.game.is_won():
            self.game_page.new_game()
        self.show_game()

    def play_again(self):
        self.game_page.new_game()
        self.show_game()


# ======================================================================
# Pages
# ======================================================================

class MenuPage(QWidget):
    """Start menu: title, a row of suits and exactly three buttons."""

    def __init__(self):
        super().__init__()
        suits = "   ".join(SUIT_SYMBOLS[suit] for suit in
                           ["spades", "hearts", "diamonds", "clubs"])
        self.play_button = make_button("Play", "primaryButton")
        self.instructions_button = make_button("Instructions", "menuButton")
        self.exit_button = make_button("Exit", "menuButton")

        # The panel holds the content; the gold frame is painted around it.
        self.panel = QWidget()
        panel_layout = QVBoxLayout(self.panel)
        panel_layout.setContentsMargins(80, 50, 80, 56)
        panel_layout.addWidget(make_label("Klondike Solitaire", "title"))
        panel_layout.addSpacing(6)
        panel_layout.addWidget(make_label(suits, "suitRow"))
        panel_layout.addSpacing(34)
        for button in [self.play_button, self.instructions_button, self.exit_button]:
            panel_layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignHCenter)
            panel_layout.addSpacing(8)
        centre_panel(self, self.panel)

    def paintEvent(self, event):
        """Paint the decorations; Qt draws the widgets on top afterwards."""
        painter = QPainter(self)
        self.paint_corner_suits(painter)
        paint_gold_panel(painter, QRectF(self.panel.geometry()))
        painter.end()

    def paint_corner_suits(self, painter):
        """Four large, very faint suit symbols, partly outside the corners."""
        size = self.height() * 0.42
        font = QFont("Segoe UI")
        font.setPixelSize(round(size))
        painter.setFont(font)
        painter.setPen(QColor(227, 196, 109, 22))
        corners = [
            ("spades", -size * 0.25, -size * 0.2),
            ("hearts", self.width() - size * 0.75, -size * 0.2),
            ("diamonds", -size * 0.25, self.height() - size * 0.8),
            ("clubs", self.width() - size * 0.75, self.height() - size * 0.8),
        ]
        for suit, x, y in corners:
            painter.drawText(QRectF(x, y, size, size), Qt.AlignmentFlag.AlignCenter,
                             SUIT_SYMBOLS[suit])


class InstructionsPage(QWidget):
    """The rules and controls in plain language, and a Back button."""

    def __init__(self):
        super().__init__()
        text = QLabel(INSTRUCTIONS_HTML)
        text.setObjectName("bodyText")
        text.setTextFormat(Qt.TextFormat.RichText)
        text.setWordWrap(True)
        text.setFixedWidth(720)
        self.back_button = make_button("Back", "menuButton")

        self.panel = QWidget()
        panel_layout = QVBoxLayout(self.panel)
        panel_layout.setContentsMargins(60, 36, 60, 40)
        panel_layout.addWidget(make_label("How to Play", "pageTitle"))
        panel_layout.addSpacing(12)
        panel_layout.addWidget(text)
        panel_layout.addSpacing(16)
        panel_layout.addWidget(self.back_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        centre_panel(self, self.panel)

    def paintEvent(self, event):
        painter = QPainter(self)
        paint_gold_panel(painter, QRectF(self.panel.geometry()))
        painter.end()


class WinPage(QWidget):
    """Shown when the game is won: moves, time, Play Again and Menu."""

    def __init__(self):
        super().__init__()
        self.summary = make_label("", "winSummary")
        self.play_again_button = make_button("Play Again", "primaryButton")
        self.menu_button = make_button("Menu", "menuButton")

        self.panel = QWidget()
        panel_layout = QVBoxLayout(self.panel)
        panel_layout.setContentsMargins(80, 50, 80, 56)
        panel_layout.addWidget(make_label("You won!", "title"))
        panel_layout.addSpacing(10)
        panel_layout.addWidget(self.summary)
        panel_layout.addSpacing(30)
        panel_layout.addWidget(self.play_again_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        panel_layout.addSpacing(8)
        panel_layout.addWidget(self.menu_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        centre_panel(self, self.panel)

    def set_summary(self, moves, time_text):
        self.summary.setText(f"Moves: {moves}      Time: {time_text}")

    def paintEvent(self, event):
        painter = QPainter(self)
        paint_gold_panel(painter, QRectF(self.panel.geometry()))
        painter.end()


class GamePage(QWidget):
    """Top bar, the card table, the message bar and the game timer."""

    # Custom signal: MainWindow connects it to show_win.
    game_won = pyqtSignal()

    def __init__(self, game):
        super().__init__()
        self.game = game

        # objectName selects the button's colour in STYLE_SHEET.
        self.menu_button = make_button("Menu", "menuNavButton")
        self.new_game_button = make_button("New Game", "newGameButton")
        self.undo_button = make_button("Undo", "undoButton")
        self.redo_button = make_button("Redo", "redoButton")
        self.mode_button = make_button("", "modeButton")
        self.moves_label = make_label("", "counter")
        self.time_label = make_label("", "counter")

        self.table = TableWidget(game)
        self.message_bar = QLabel()
        self.message_bar.setObjectName("messageBar")
        self.build_layout()

        # ---- Timer (display-only state) --------------------------------
        # elapsed_before: seconds counted in earlier running periods.
        # running_since:  when the current running period started, or None
        #                 while paused (menu/instructions shown, or won).
        self.elapsed_before = 0.0
        self.running_since = None
        # A QTimer calls refresh_time twice per second to update the label.
        self.clock = QTimer(self)
        self.clock.timeout.connect(self.refresh_time)
        self.clock.start(500)
        # A single-shot QTimer puts the hint back 3 s after an error message.
        self.message_timer = QTimer(self)
        self.message_timer.setSingleShot(True)
        self.message_timer.timeout.connect(self.show_hint)

        # ---- Signals -> slots --------------------------------------------
        self.new_game_button.clicked.connect(self.new_game)
        self.undo_button.clicked.connect(self.undo)
        self.redo_button.clicked.connect(self.redo)
        self.mode_button.clicked.connect(self.change_mode)
        self.table.changed.connect(self.after_change)
        self.table.message.connect(self.show_error)

        self.show_hint()
        self.refresh_labels()
        self.refresh_time()

    def build_layout(self):
        top_bar = QWidget()
        top_bar.setObjectName("topBar")
        # Plain QWidgets only paint a style-sheet background with this flag.
        top_bar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        bar_layout = QHBoxLayout(top_bar)
        bar_layout.setContentsMargins(18, 12, 18, 12)
        bar_layout.setSpacing(10)
        bar_layout.addWidget(self.menu_button)
        bar_layout.addSpacing(14)
        for button in [self.new_game_button, self.undo_button,
                       self.redo_button, self.mode_button]:
            bar_layout.addWidget(button)
        bar_layout.addStretch(1)
        bar_layout.addWidget(self.moves_label)
        bar_layout.addWidget(self.time_label)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(top_bar)
        layout.addWidget(self.table, 1)       # the table takes all spare space
        layout.addWidget(self.message_bar)

    # ---- Button actions (each one clears the selection) ---------------

    def new_game(self):
        self.game.new_game()
        self.reset_timer()
        self.show_hint()
        self.after_action()

    def undo(self):
        self.game.undo()
        self.after_action()

    def redo(self):
        self.game.redo()
        self.after_action()

    def change_mode(self):
        """Switch Draw 1 <-> Draw 3; this always starts a new game."""
        if self.game.draw_count == 1:
            self.game.draw_count = 3
        else:
            self.game.draw_count = 1
        self.new_game()

    def after_action(self):
        self.table.clear_selection()
        self.after_change()

    def after_change(self):
        """Called after anything may have changed (also via table.changed)."""
        self.table.update()
        self.refresh_labels()
        if self.game.is_won():
            self.pause_timer()                 # the clock stops on a win
            self.game_won.emit()

    # ---- Labels and messages ------------------------------------------

    def refresh_labels(self):
        """Read the game and update the top bar (no copy of the game is kept)."""
        self.mode_button.setText(f"Mode: Draw {self.game.draw_count}")
        self.moves_label.setText(f"Moves: {self.game.move_count()}")
        self.undo_button.setEnabled(self.game.can_undo())
        self.redo_button.setEnabled(self.game.can_redo())

    def show_message(self, text, error=False):
        """Show text in the message bar: warm red for errors, cream otherwise."""
        if error:
            colour = MESSAGE_ERROR
        else:
            colour = MESSAGE_NORMAL
        self.message_bar.setStyleSheet(f"color: {colour};")
        self.message_bar.setText(text)

    def show_error(self, text):
        self.show_message(text, error=True)
        self.message_timer.start(MESSAGE_DURATION_MS)   # restarts if already running

    def show_hint(self):
        self.show_message(HINT)

    # ---- Timer ----------------------------------------------------------

    def pause_timer(self):
        if self.running_since is not None:
            self.elapsed_before += time.monotonic() - self.running_since
            self.running_since = None

    def resume_timer(self):
        if self.running_since is None and not self.game.is_won():
            self.running_since = time.monotonic()

    def reset_timer(self):
        """Back to 00:00. Keeps running if it was running (New Game / Mode)."""
        self.elapsed_before = 0.0
        if self.running_since is not None:
            self.running_since = time.monotonic()

    def elapsed_seconds(self):
        total = self.elapsed_before
        if self.running_since is not None:
            total += time.monotonic() - self.running_since
        return int(total)

    def time_text(self):
        seconds = self.elapsed_seconds()
        return f"{seconds // 60:02d}:{seconds % 60:02d}"

    def refresh_time(self):
        self.time_label.setText(f"Time: {self.time_text()}")
