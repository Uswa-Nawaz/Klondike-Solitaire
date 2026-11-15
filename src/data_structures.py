"""
Hand-written data structures used by the Klondike Solitaire game.

    Node        - one link in a chain of items
    LinkedList  - a doubly linked list; the ONLY place where items are stored
    Stack       - LIFO (last in, first out), built on top of a LinkedList
    Queue       - FIFO (first in, first out), built on top of a LinkedList

Stack and Queue use COMPOSITION: each one *has* a LinkedList inside it and
only exposes the operations that make sense for that structure. Because
the cards live inside the LinkedList nodes, no card is ever stored twice.

Game usage:
    Stack  -> 7 tableau columns, 4 foundations, the waste pile,
              and the undo/redo history (14 stacks in total)
    Queue  -> the stock (draw pile)
"""


class Node:
    """One element of a doubly linked list.

    A node holds an item (for example a Card) and two links:
    'prev' points to the node before it, 'next' to the node after it.
    """

    def __init__(self, item):
        self.item = item
        self.prev = None  # neighbour towards the head
        self.next = None  # neighbour towards the tail


class LinkedList:
    """A doubly linked list with head and tail pointers and a size counter.

    Keeping BOTH ends (head and tail) and BOTH links per node (prev and next)
    makes adding/removing at either end O(1) - no walking through the list.
    """

    def __init__(self):
        self.head = None  # first node (or None when empty)
        self.tail = None  # last node (or None when empty)
        self.size = 0     # number of nodes, kept up to date by every operation

    def __len__(self):
        """Lets Python's built-in len() work: len(my_list)."""
        return self.size

    def is_empty(self):
        return self.size == 0

    def first(self):
        """Return (without removing) the item at the head."""
        if self.is_empty():
            raise IndexError("first() called on an empty linked list")
        return self.head.item

    def last(self):
        """Return (without removing) the item at the tail."""
        if self.is_empty():
            raise IndexError("last() called on an empty linked list")
        return self.tail.item

    # ------------------------------------------------------------------
    # Insertion
    # ------------------------------------------------------------------

    def append(self, item):
        """Insert a new item at the tail. O(1)."""
        new_node = Node(item)
        if self.is_empty():
            # The only node is both the first and the last node.
            self.head = new_node
            self.tail = new_node
        else:
            # Link the new node after the current tail, then move the tail.
            new_node.prev = self.tail
            self.tail.next = new_node
            self.tail = new_node
        self.size += 1

    def append_list(self, other):
        """Move ALL nodes of 'other' onto the end of this list. O(1).

        No nodes are copied: we only connect our tail to other's head.
        Afterwards 'other' is empty, because its nodes now belong to us.
        Used for moving a run of tableau cards onto another column.
        """
        if other is self:
            raise ValueError("cannot append a linked list to itself")
        if other.is_empty():
            return

        if self.is_empty():
            self.head = other.head
        else:
            self.tail.next = other.head
            other.head.prev = self.tail
        self.tail = other.tail
        self.size += other.size

        # 'other' must forget the nodes, otherwise two lists would share them.
        other.clear()

    # ------------------------------------------------------------------
    # Removal
    # ------------------------------------------------------------------

    def remove_first(self):
        """Remove and return the item at the head. O(1)."""
        if self.is_empty():
            raise IndexError("remove_first() called on an empty linked list")

        removed = self.head
        self.head = removed.next
        if self.head is None:
            # The list is now empty, so the tail must be cleared too.
            self.tail = None
        else:
            self.head.prev = None
        removed.next = None  # detach the removed node completely
        self.size -= 1
        return removed.item

    def remove_last(self):
        """Remove and return the item at the tail. O(1) thanks to 'prev'."""
        if self.is_empty():
            raise IndexError("remove_last() called on an empty linked list")

        removed = self.tail
        self.tail = removed.prev
        if self.tail is None:
            # The list is now empty, so the head must be cleared too.
            self.head = None
        else:
            self.tail.next = None
        removed.prev = None  # detach the removed node completely
        self.size -= 1
        return removed.item

    def split_off_last(self, count):
        """Detach the last 'count' nodes and return them as a new LinkedList.

        The detached nodes keep their original order. Cost: O(count) to
        walk back from the tail to the cut point, then O(1) to cut.
        Used for picking up a run of face-up cards from a tableau column.

        Example: [A, B, C, D].split_off_last(2) -> this list [A, B],
                 returned list [C, D].
        """
        if count < 1 or count > self.size:
            raise ValueError(
                f"cannot split off {count} items from a list of size {self.size}"
            )

        # Step 1: walk backwards to find the first node of the segment.
        segment_head = self.tail
        for _ in range(count - 1):
            segment_head = segment_head.prev

        # Step 2: build the returned list around the existing nodes.
        segment = LinkedList()
        segment.head = segment_head
        segment.tail = self.tail
        segment.size = count

        # Step 3: cut the link between this list and the segment.
        new_tail = segment_head.prev
        segment_head.prev = None
        if new_tail is None:
            # We split off everything; this list becomes empty.
            self.head = None
        else:
            new_tail.next = None
        self.tail = new_tail
        self.size -= count

        return segment

    def clear(self):
        """Forget all nodes. O(1)."""
        self.head = None
        self.tail = None
        self.size = 0

    # ------------------------------------------------------------------
    # Traversal
    # ------------------------------------------------------------------

    def __iter__(self):
        """Visit every item from head to tail. O(n).

        Lets us write:  for item in my_list:  ...  or  list(my_list).
        'yield' hands back one item at a time and then continues from
        where it stopped, following the 'next' links.
        """
        current = self.head
        while current is not None:
            yield current.item
            current = current.next


class Stack:
    """LIFO stack built on a LinkedList (composition).

    The tail of the linked list is the TOP of the stack and the head is the
    BOTTOM. Only the top can be pushed to or popped from.
    """

    def __init__(self):
        self._items = LinkedList()

    def push(self, item):
        """Put an item on top. O(1)."""
        self._items.append(item)

    def pop(self):
        """Remove and return the top item. O(1)."""
        if self.is_empty():
            raise IndexError("pop() called on an empty stack")
        return self._items.remove_last()

    def peek(self):
        """Return the top item without removing it. O(1)."""
        if self.is_empty():
            raise IndexError("peek() called on an empty stack")
        return self._items.last()

    def is_empty(self):
        return self._items.is_empty()

    def __len__(self):
        return len(self._items)

    def pop_many(self, count):
        """Remove the top 'count' items TOGETHER and return them as a LinkedList.

        Like lifting several plates off the top at once: their order is kept
        (bottom-most of the group first). The nodes are detached, not copied.
        Used to pick up a run of cards from a tableau column.
        """
        if count < 1 or count > len(self):
            raise ValueError(
                f"cannot pop {count} items from a stack of size {len(self)}"
            )
        return self._items.split_off_last(count)

    def push_many(self, items):
        """Place a LinkedList of items (from pop_many) on top, keeping order.

        The given list's nodes are re-linked onto this stack and the given
        list becomes empty. Used to drop a run of cards onto a column.
        """
        self._items.append_list(items)

    def clear(self):
        self._items.clear()

    def __iter__(self):
        """Visit items from BOTTOM to TOP (the order they are drawn on screen)."""
        return iter(self._items)


class Queue:
    """FIFO queue built on a LinkedList (composition).

    Items join at the BACK (the tail) and leave from the FRONT (the head),
    so the first item added is the first item removed.
    """

    def __init__(self):
        self._items = LinkedList()

    def enqueue(self, item):
        """Add an item at the back. O(1)."""
        self._items.append(item)

    def dequeue(self):
        """Remove and return the item at the front. O(1)."""
        if self.is_empty():
            raise IndexError("dequeue() called on an empty queue")
        return self._items.remove_first()

    def peek(self):
        """Return the front item without removing it. O(1)."""
        if self.is_empty():
            raise IndexError("peek() called on an empty queue")
        return self._items.first()

    def is_empty(self):
        return self._items.is_empty()

    def __len__(self):
        return len(self._items)

    def clear(self):
        self._items.clear()

    def __iter__(self):
        """Visit items from FRONT to BACK."""
        return iter(self._items)
