import unittest

from structures.binary_search_tree import BinarySearchTree
from structures.binary_tree import BinaryTree
from structures.doubly_linked_list import DoublyLinkedList
from structures.dynamic_array import DynamicArray
from structures.hash_map import HashMap
from structures.linear_collections import Deque, Queue, Stack
from structures.min_heap import MinHeap


class DynamicArrayTests(unittest.TestCase):
    def test_grows_and_supports_index_operations(self):
        values = DynamicArray(2)
        values.append("a")
        values.append("b")
        values.append("c")

        self.assertEqual(values.capacity(), 4)
        self.assertEqual(values.get(2), "c")
        values.set(1, "B")
        self.assertEqual(values.remove(0), "a")
        self.assertEqual(values.to_list(), ["B", "c"])


class DoublyLinkedListTests(unittest.TestCase):
    def test_all_end_operations_and_move(self):
        linked = DoublyLinkedList()
        middle = linked.insert_front("middle")
        linked.insert_front("front")
        linked.insert_back("back")

        linked.move_to_front(middle)
        self.assertEqual(list(linked.iter_front()), ["middle", "front", "back"])
        self.assertEqual(linked.remove_front(), "middle")
        self.assertEqual(linked.remove_back(), "back")
        self.assertEqual(linked.size(), 1)


class HashMapTests(unittest.TestCase):
    def test_chaining_update_remove_and_resize(self):
        table = HashMap(8)
        self.assertEqual(table.hash_index("a"), table.hash_index("i"))
        table.put("a", 1)
        table.put("i", 2)
        self.assertEqual(table.get("a"), 1)
        self.assertEqual(table.get("i"), 2)
        self.assertEqual(table.put("a", 3), 1)
        self.assertEqual(table.remove("i"), 2)
        self.assertFalse(table.contains("i"))

        for index in range(10):
            table.put("key:" + str(index), index)
        self.assertGreaterEqual(table.capacity(), 16)
        for index in range(10):
            self.assertEqual(table.get("key:" + str(index)), index)


class MinHeapTests(unittest.TestCase):
    def test_pops_in_expiration_order(self):
        heap = MinHeap()
        heap.push(30.0, "late")
        heap.push(10.0, "first")
        heap.push(20.0, "middle")

        self.assertEqual(heap.peek().key, "first")
        self.assertEqual(heap.pop().key, "first")
        self.assertEqual(heap.pop().key, "middle")
        self.assertEqual(heap.pop().key, "late")
        self.assertIsNone(heap.pop())


class BonusStructureTests(unittest.TestCase):
    def test_stack_queue_and_deque(self):
        stack = Stack()
        stack.push(1)
        stack.push(2)
        self.assertEqual(stack.pop(), 2)

        queue = Queue()
        queue.enqueue(1)
        queue.enqueue(2)
        self.assertEqual(queue.dequeue(), 1)

        deque = Deque()
        deque.append_left(1)
        deque.append_right(2)
        self.assertEqual(deque.pop_right(), 2)
        self.assertEqual(deque.pop_left(), 1)

    def test_binary_tree_traversals(self):
        tree = BinaryTree()
        for value in range(1, 8):
            tree.add(value)
        self.assertEqual(tree.preorder(), [1, 2, 4, 5, 3, 6, 7])
        self.assertEqual(tree.inorder(), [4, 2, 5, 1, 6, 3, 7])
        self.assertEqual(tree.postorder(), [4, 5, 2, 6, 7, 3, 1])
        self.assertEqual(tree.level_order(), [1, 2, 3, 4, 5, 6, 7])

    def test_binary_search_tree(self):
        tree = BinarySearchTree()
        for key in (5, 3, 7, 2, 4, 6, 8):
            tree.insert(key, "value:" + str(key))
        self.assertEqual(tree.search(4), "value:4")
        self.assertTrue(tree.delete(5))
        self.assertEqual(tree.inorder(), [2, 3, 4, 6, 7, 8])
        self.assertFalse(tree.delete(99))


if __name__ == "__main__":
    unittest.main()
