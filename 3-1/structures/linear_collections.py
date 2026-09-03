"""직접 구현 자료구조를 재사용한 스택, 큐, 덱."""

from typing import Any

from .doubly_linked_list import DoublyLinkedList
from .dynamic_array import DynamicArray


class Stack:
    def __init__(self) -> None:
        self._items = DynamicArray()

    def push(self, value: Any) -> None:
        self._items.append(value)

    def pop(self) -> Any:
        return self._items.pop()

    def peek(self) -> Any:
        if self._items.size() == 0:
            return None
        return self._items.get(self._items.size() - 1)

    def size(self) -> int:
        return self._items.size()


class Queue:
    def __init__(self) -> None:
        self._items = DoublyLinkedList()

    def enqueue(self, value: Any) -> None:
        self._items.insert_back(value)

    def dequeue(self) -> Any:
        return self._items.remove_front()

    def peek(self) -> Any:
        if self._items.head is None:
            return None
        return self._items.head.data

    def size(self) -> int:
        return self._items.size()


class Deque:
    def __init__(self) -> None:
        self._items = DoublyLinkedList()

    def append_left(self, value: Any) -> None:
        self._items.insert_front(value)

    def append_right(self, value: Any) -> None:
        self._items.insert_back(value)

    def pop_left(self) -> Any:
        return self._items.remove_front()

    def pop_right(self) -> Any:
        return self._items.remove_back()

    def peek_left(self) -> Any:
        if self._items.head is None:
            return None
        return self._items.head.data

    def peek_right(self) -> Any:
        if self._items.tail is None:
            return None
        return self._items.tail.data

    def size(self) -> int:
        return self._items.size()
