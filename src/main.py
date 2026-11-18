"""
Start Klondike Solitaire (PyQt6 version).

Run from the project folder with:
    python src\\main.py
"""

import sys

from PyQt6.QtWidgets import QApplication

from game import KlondikeGame
from ui import MainWindow


def main():
    app = QApplication(sys.argv)          # every PyQt program needs one
    window = MainWindow(KlondikeGame())   # game logic + the window that shows it
    window.show()
    sys.exit(app.exec())                  # Qt's event loop: runs until the window closes


if __name__ == "__main__":
    main()
