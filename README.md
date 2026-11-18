# Klondike Solitaire

A Klondike Solitaire game written in Python with a PyQt6 desktop interface,
made as the mid-term project for CSC200 Data Structure & Algorithms. The
game logic is built on hand-written data structures (a doubly linked list,
a stack and a queue) together with Python lists and dictionaries, and
supports Draw 1 and Draw 3, stock recycling, moving runs of cards, undo and
redo, and win detection. The interface only displays the game and passes the
player's clicks to it; all rules live in the game logic.

## Requirements and setup

- Python 3.14 (developed and tested on Python 3.14.7, Windows 11)
- PyQt6 6.12.1 (the only external package)

Install the package from the project folder:

```
python -m pip install -r requirements.txt
```

## Running

Run these commands from the project folder.

| What | Command |
|---|---|
| Play the game | `python src\main.py` |
| Run all tests | `python -m unittest discover -s tests -v` |
| Preview the win screen | `python scripts\preview_win.py` |

The win preview is a separate developer script. It moves all 52 cards onto
the foundations and opens the window on the win page; the game itself has
no such shortcut.

## How to play

The goal is to move all 52 cards onto the four foundations, one per suit,
from Ace up to King. In the columns, cards are built downwards in
alternating colours (for example a red 6 on a black 7), and only a King can
go into an empty column.

| Control | What it does |
|---|---|
| Click a card, then click a pile | Selects the card (outlined in gold) and moves it, with every card on top of it, to that pile. Click the selected card again to cancel. |
| Click the stock | Draws one card (Draw 1) or three cards (Draw 3) onto the waste. When the stock is empty, the click turns the waste back over into the stock. |
| Undo / Redo | Takes back or repeats moves, draws and recycles. |
| Mode | Switches between Draw 1 and Draw 3 and starts a new game. |
| New Game | Deals a new game and resets the timer. |
| Menu | Returns to the start menu. The current game is kept and the timer pauses. |

If a move is not allowed, the reason appears in the message bar at the
bottom, and nothing on the table changes.

## Data structures

| Structure | Where it is used | Why it fits |
|---|---|---|
| Array / List | `create_deck()` builds the 52-card deck as a Python list; `shuffle_deck()` shuffles it; `new_game()` reads it by position while dealing. | Shuffling swaps cards at random positions, which needs O(1) access by index. The deck has a fixed size, so slow inserts in the middle never matter. |
| Linked List | `LinkedList` with `Node` in `data_structures.py` (doubly linked, with head, tail and size). Each tableau column is a linked list of nodes, one node per card, wrapped in a Stack. A linked list is also the storage inside every other Stack and the Queue. | Adding and removing at either end is O(1). A run of cards is moved by cutting and relinking nodes (`split_off_last`, `append_list`), so cards are never copied. |
| Stack (LIFO) | 14 stacks: 7 tableau columns, 4 foundations, the waste pile, and the undo and redo history. Built on a LinkedList by composition. | Only the top card of a pile can be taken, and undo must reverse the most recent action first. Both are last in, first out. |
| Queue (FIFO) | The stock (draw pile). Built on a LinkedList by composition. | Cards are drawn in the order they were placed in the stock, and recycled cards return in their original order. |
| HashMap / Dictionary | `piles`: pile name to pile object (for example `"tableau_3"` to its Stack). `card_locations`: card id to the Card object and its pile name (for example `"10H"` to `{"card": ..., "pile": "tableau_3"}`). | O(1) lookup: a clicked card's pile is found without searching all 13 piles. The dictionary holds a reference to the same Card object that is in the pile, so the face-up state is never stored twice. |

## Algorithms

- **Fisher-Yates shuffle** (`shuffle_deck` in `card.py`). From the last
  position down to position 1, pick a random position `j` between 0 and `i`
  and swap the two cards. Every order of the deck is equally likely.
  O(n) time, O(1) extra space. Tests can pass a seeded random generator so
  the shuffle is repeatable.
- **Two-stack reversal when recycling** (`_recycle_waste` in `game.py`). The
  waste holds the drawn cards with the first one at the bottom. Popping
  every card onto a temporary stack reverses the order; popping the
  temporary stack and enqueuing each card into the stock reverses it back,
  so the stock is in its original order again.
- **Queue rotation when undoing a draw** (`_undo_draw` in `game.py`). The
  drawn cards must return to the front of the stock, but a queue only adds
  at the back. They are enqueued at the back, then each older card is
  dequeued and enqueued again, which brings the returned cards to the front.
  Only FIFO operations are used; O(n) for n stock cards.
- **Moving a run with `pop_many` / `push_many`** (`_transfer` in `game.py`).
  `pop_many(count)` walks `count` nodes back from the top and cuts the run
  off the source list; `push_many` links the run onto the destination's top
  in O(1). The cards' nodes are moved, not copied, and their order is kept.

Every move is checked completely before anything changes, so an illegal
move leaves the game exactly as it was. Undo and redo store each action as a
small dictionary record on the undo and redo stacks; a new action clears the
redo stack, and the move counter is the size of the undo stack.

## Project structure

```
Klondike-Solitaire/
  src/
    main.py                  Starts the application
    card.py                  Card class, create_deck() and the Fisher-Yates shuffle
    data_structures.py       Node, LinkedList, Stack and Queue (hand-written)
    game.py                  KlondikeGame: dealing, rules, moves, undo/redo, win check
    ui.py                    Window and pages: menu, instructions, game, win
    table_view.py            The card table: drawing the cards and handling clicks
  tests/
    test_data_structures.py  Tests for LinkedList, Stack and Queue
    test_card.py             Tests for Card, the deck and the shuffle
    test_game.py             Tests for dealing, rules, drawing, undo/redo and winning
    test_ui_smoke.py         Offscreen check that the interface works without crashing
  scripts/
    preview_win.py           Opens the window on a won game (developer preview)
  docs/
    Mid_Project_Fall_2026.pdf  The assignment brief
  requirements.txt           PyQt6 version
```

## Testing

The project has 118 unit tests, written with Python's built-in `unittest`.

| File | Tests | What they cover |
|---|---|---|
| `test_data_structures.py` | 36 | Linked list insert, remove, split, join and traversal (including checking every `prev`/`next` link); stack LIFO order and group moves; queue FIFO order; empty-structure errors. |
| `test_card.py` | 26 | Card attributes, colour and id; invalid ranks and suits; 52 unique cards in the deck; the shuffle keeps the same cards, is repeatable with a seed, and is fair (each order of 3 items appears about equally often in 60,000 shuffles). |
| `test_game.py` | 53 | Dealing (1 to 7 cards per column, only top cards face up, 24 cards in the stock); every move rule, legal and illegal; illegal moves change nothing; card flipping; Draw 1 and Draw 3; recycling order; undo and redo of every action type; undoing a whole played game returns exactly to the starting deal; win detection; the card-location dictionary always matches the piles. |
| `test_ui_smoke.py` | 3 | Page switching, clicks reaching the game, and the win page, on Qt's offscreen platform (no window opens). |

## Author

- Name: _[Uswa Nawaz]_
- Course: CSC200 Data Structure & Algorithms
