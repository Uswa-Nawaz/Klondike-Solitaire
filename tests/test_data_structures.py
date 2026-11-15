"""
Unit tests for the hand-written data structures in src/data_structures.py.

Run all tests from the project root with:
    .venv\\Scripts\\python.exe -m unittest discover -s tests -v
"""

import os
import sys
import unittest

# Python does not look inside src/ automatically, so we add it to the
# list of folders Python searches when importing modules.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from data_structures import LinkedList, Queue, Stack  # noqa: E402


def make_list(*items):
    """Helper: build a LinkedList containing the given items in order."""
    linked_list = LinkedList()
    for item in items:
        linked_list.append(item)
    return linked_list


class LinkedListTests(unittest.TestCase):

    def assert_links_consistent(self, linked_list, expected_items):
        """Check contents, size, and that 'next' and 'prev' links agree."""
        # Walk forwards using 'next'.
        forwards = []
        node = linked_list.head
        while node is not None:
            forwards.append(node.item)
            node = node.next

        # Walk backwards using 'prev'.
        backwards = []
        node = linked_list.tail
        while node is not None:
            backwards.append(node.item)
            node = node.prev

        self.assertEqual(forwards, expected_items)
        self.assertEqual(backwards, list(reversed(expected_items)))
        self.assertEqual(len(linked_list), len(expected_items))

        if expected_items:
            self.assertIsNone(linked_list.head.prev)
            self.assertIsNone(linked_list.tail.next)
        else:
            self.assertIsNone(linked_list.head)
            self.assertIsNone(linked_list.tail)

    def test_new_list_is_empty(self):
        linked_list = LinkedList()
        self.assertTrue(linked_list.is_empty())
        self.assert_links_consistent(linked_list, [])

    def test_append_keeps_insertion_order(self):
        linked_list = make_list("A", "B", "C")
        self.assertFalse(linked_list.is_empty())
        self.assertEqual(linked_list.first(), "A")
        self.assertEqual(linked_list.last(), "C")
        self.assert_links_consistent(linked_list, ["A", "B", "C"])

    def test_traversal_visits_head_to_tail(self):
        linked_list = make_list(1, 2, 3, 4)
        self.assertEqual(list(linked_list), [1, 2, 3, 4])
        self.assertEqual(list(LinkedList()), [])

    def test_remove_first_returns_items_from_head(self):
        linked_list = make_list("A", "B", "C")
        self.assertEqual(linked_list.remove_first(), "A")
        self.assert_links_consistent(linked_list, ["B", "C"])

    def test_remove_last_returns_items_from_tail(self):
        linked_list = make_list("A", "B", "C")
        self.assertEqual(linked_list.remove_last(), "C")
        self.assert_links_consistent(linked_list, ["A", "B"])

    def test_removing_only_item_empties_list(self):
        from_front = make_list("X")
        from_front.remove_first()
        self.assert_links_consistent(from_front, [])

        from_back = make_list("X")
        from_back.remove_last()
        self.assert_links_consistent(from_back, [])

    def test_operations_on_empty_list_raise(self):
        linked_list = LinkedList()
        with self.assertRaises(IndexError):
            linked_list.remove_first()
        with self.assertRaises(IndexError):
            linked_list.remove_last()
        with self.assertRaises(IndexError):
            linked_list.first()
        with self.assertRaises(IndexError):
            linked_list.last()

    def test_split_off_last_from_middle(self):
        linked_list = make_list("A", "B", "C", "D", "E")
        segment = linked_list.split_off_last(2)
        self.assert_links_consistent(linked_list, ["A", "B", "C"])
        self.assert_links_consistent(segment, ["D", "E"])

    def test_split_off_one_item(self):
        linked_list = make_list("A", "B")
        segment = linked_list.split_off_last(1)
        self.assert_links_consistent(linked_list, ["A"])
        self.assert_links_consistent(segment, ["B"])

    def test_split_off_everything(self):
        linked_list = make_list("A", "B", "C")
        segment = linked_list.split_off_last(3)
        self.assert_links_consistent(linked_list, [])
        self.assert_links_consistent(segment, ["A", "B", "C"])

    def test_split_off_invalid_count_raises(self):
        linked_list = make_list("A", "B")
        with self.assertRaises(ValueError):
            linked_list.split_off_last(0)
        with self.assertRaises(ValueError):
            linked_list.split_off_last(3)
        # A failed split must not damage the list.
        self.assert_links_consistent(linked_list, ["A", "B"])

    def test_append_list_onto_non_empty_list(self):
        target = make_list("A", "B")
        other = make_list("C", "D")
        target.append_list(other)
        self.assert_links_consistent(target, ["A", "B", "C", "D"])
        # 'other' gave its nodes away, so it must now be empty.
        self.assert_links_consistent(other, [])

    def test_append_list_onto_empty_list(self):
        target = LinkedList()
        other = make_list("C", "D")
        target.append_list(other)
        self.assert_links_consistent(target, ["C", "D"])
        self.assert_links_consistent(other, [])

    def test_append_empty_list_changes_nothing(self):
        target = make_list("A")
        target.append_list(LinkedList())
        self.assert_links_consistent(target, ["A"])

    def test_append_list_to_itself_raises(self):
        target = make_list("A")
        with self.assertRaises(ValueError):
            target.append_list(target)

    def test_split_then_append_moves_nodes_not_copies(self):
        source = make_list("A", "B", "C")
        target = make_list("X")
        node_c = source.tail  # remember the actual node object

        segment = source.split_off_last(2)
        target.append_list(segment)

        self.assert_links_consistent(source, ["A"])
        self.assert_links_consistent(target, ["X", "B", "C"])
        # The very same Node object moved - nothing was duplicated.
        self.assertIs(target.tail, node_c)

    def test_clear_empties_list(self):
        linked_list = make_list(1, 2, 3)
        linked_list.clear()
        self.assert_links_consistent(linked_list, [])


class StackTests(unittest.TestCase):

    def test_new_stack_is_empty(self):
        stack = Stack()
        self.assertTrue(stack.is_empty())
        self.assertEqual(len(stack), 0)

    def test_push_and_pop_are_last_in_first_out(self):
        stack = Stack()
        stack.push("A")
        stack.push("B")
        stack.push("C")
        self.assertEqual(stack.pop(), "C")
        self.assertEqual(stack.pop(), "B")
        self.assertEqual(stack.pop(), "A")
        self.assertTrue(stack.is_empty())

    def test_peek_does_not_remove(self):
        stack = Stack()
        stack.push("A")
        stack.push("B")
        self.assertEqual(stack.peek(), "B")
        self.assertEqual(stack.peek(), "B")
        self.assertEqual(len(stack), 2)

    def test_pop_and_peek_on_empty_stack_raise(self):
        stack = Stack()
        with self.assertRaises(IndexError):
            stack.pop()
        with self.assertRaises(IndexError):
            stack.peek()

    def test_iteration_goes_bottom_to_top(self):
        stack = Stack()
        for item in ["bottom", "middle", "top"]:
            stack.push(item)
        self.assertEqual(list(stack), ["bottom", "middle", "top"])

    def test_pop_many_keeps_order_of_the_group(self):
        stack = Stack()
        for item in ["K", "Q", "J", "10"]:
            stack.push(item)
        group = stack.pop_many(3)
        self.assertEqual(list(group), ["Q", "J", "10"])
        self.assertEqual(list(stack), ["K"])
        self.assertEqual(stack.peek(), "K")

    def test_pop_many_invalid_count_raises(self):
        stack = Stack()
        stack.push("A")
        with self.assertRaises(ValueError):
            stack.pop_many(0)
        with self.assertRaises(ValueError):
            stack.pop_many(2)
        self.assertEqual(list(stack), ["A"])

    def test_push_many_places_group_on_top_in_order(self):
        source = Stack()
        target = Stack()
        for item in ["K", "Q", "J"]:
            source.push(item)
        target.push("A")

        target.push_many(source.pop_many(2))

        self.assertEqual(list(target), ["A", "Q", "J"])
        self.assertEqual(target.peek(), "J")
        self.assertEqual(list(source), ["K"])

    def test_moving_whole_stack_empties_source(self):
        source = Stack()
        target = Stack()
        for item in [1, 2, 3]:
            source.push(item)
        target.push_many(source.pop_many(3))
        self.assertTrue(source.is_empty())
        self.assertEqual(list(target), [1, 2, 3])
        self.assertEqual(len(source) + len(target), 3)

    def test_stack_still_works_after_group_moves(self):
        # After pop_many/push_many the internal links must stay valid,
        # so normal push/pop must still behave correctly.
        source = Stack()
        target = Stack()
        for item in ["A", "B", "C"]:
            source.push(item)
        target.push_many(source.pop_many(2))
        target.push("D")
        self.assertEqual(target.pop(), "D")
        self.assertEqual(target.pop(), "C")
        self.assertEqual(target.pop(), "B")
        self.assertTrue(target.is_empty())
        self.assertEqual(source.pop(), "A")

    def test_clear_empties_stack(self):
        stack = Stack()
        stack.push(1)
        stack.push(2)
        stack.clear()
        self.assertTrue(stack.is_empty())

    def test_stack_stores_the_same_object_not_a_copy(self):
        item = ["some", "object"]
        stack = Stack()
        stack.push(item)
        self.assertIs(stack.peek(), item)
        self.assertIs(stack.pop(), item)


class QueueTests(unittest.TestCase):

    def test_new_queue_is_empty(self):
        queue = Queue()
        self.assertTrue(queue.is_empty())
        self.assertEqual(len(queue), 0)

    def test_enqueue_and_dequeue_are_first_in_first_out(self):
        queue = Queue()
        queue.enqueue("A")
        queue.enqueue("B")
        queue.enqueue("C")
        self.assertEqual(queue.dequeue(), "A")
        self.assertEqual(queue.dequeue(), "B")
        self.assertEqual(queue.dequeue(), "C")
        self.assertTrue(queue.is_empty())

    def test_peek_shows_front_without_removing(self):
        queue = Queue()
        queue.enqueue("A")
        queue.enqueue("B")
        self.assertEqual(queue.peek(), "A")
        self.assertEqual(len(queue), 2)

    def test_dequeue_and_peek_on_empty_queue_raise(self):
        queue = Queue()
        with self.assertRaises(IndexError):
            queue.dequeue()
        with self.assertRaises(IndexError):
            queue.peek()

    def test_interleaved_operations_keep_fifo_order(self):
        queue = Queue()
        queue.enqueue(1)
        queue.enqueue(2)
        self.assertEqual(queue.dequeue(), 1)
        queue.enqueue(3)
        self.assertEqual(queue.dequeue(), 2)
        self.assertEqual(queue.dequeue(), 3)
        # Re-using the queue after it became empty must still work.
        queue.enqueue(4)
        self.assertEqual(queue.peek(), 4)
        self.assertEqual(queue.dequeue(), 4)

    def test_iteration_goes_front_to_back(self):
        queue = Queue()
        for item in ["first", "second", "third"]:
            queue.enqueue(item)
        self.assertEqual(list(queue), ["first", "second", "third"])

    def test_clear_empties_queue(self):
        queue = Queue()
        queue.enqueue(1)
        queue.clear()
        self.assertTrue(queue.is_empty())


if __name__ == "__main__":
    unittest.main()
