"""TTL 만료 시각을 가장 빠른 순서로 꺼내는 최소 힙."""

from typing import Optional

from .dynamic_array import DynamicArray


class HeapItem:
    """(expire_at, key) TTL 레코드."""

    __slots__ = ("expire_at", "key")

    def __init__(self, expire_at: float, key: str) -> None:
        self.expire_at = expire_at
        self.key = key


class MinHeap:
    """expire_at이 가장 작은 항목을 루트에 유지한다."""

    def __init__(self) -> None:
        self._items = DynamicArray()

    def push(self, expire_at: float, key: str) -> None:
        self._items.append(HeapItem(expire_at, key))
        self._heapify_up(self._items.size() - 1)

    def pop(self) -> Optional[HeapItem]:
        if self._items.size() == 0:
            return None
        root = self._items.get(0)
        last = self._items.pop()
        if self._items.size() > 0:
            self._items.set(0, last)
            self._heapify_down(0)
        return root

    def peek(self) -> Optional[HeapItem]:
        if self._items.size() == 0:
            return None
        return self._items.get(0)

    def size(self) -> int:
        return self._items.size()

    def _heapify_up(self, index: int) -> None:
        while index > 0:
            parent = (index - 1) // 2
            if self._items.get(parent).expire_at <= self._items.get(index).expire_at:
                break
            self._swap(parent, index)
            index = parent

    def _heapify_down(self, index: int) -> None:
        size = self._items.size()
        while True:
            left = index * 2 + 1
            right = left + 1
            smallest = index
            if left < size and self._items.get(left).expire_at < self._items.get(smallest).expire_at:
                smallest = left
            if right < size and self._items.get(right).expire_at < self._items.get(smallest).expire_at:
                smallest = right
            if smallest == index:
                return
            self._swap(index, smallest)
            index = smallest

    def _swap(self, first: int, second: int) -> None:
        temporary = self._items.get(first)
        self._items.set(first, self._items.get(second))
        self._items.set(second, temporary)
