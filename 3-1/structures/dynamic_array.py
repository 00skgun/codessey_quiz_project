"""고정 길이 파이썬 리스트를 저장 공간으로 사용하는 동적 배열."""

from typing import Any, Iterator, List


class DynamicArray:
    """공간이 차면 capacity를 두 배로 늘리는 직접 구현 동적 배열."""

    def __init__(self, initial_capacity: int = 4) -> None:
        if initial_capacity < 1:
            initial_capacity = 1
        self._capacity = initial_capacity
        self._size = 0
        self._items = [None] * self._capacity

    def _grow(self) -> None:
        new_capacity = self._capacity * 2
        new_items = [None] * new_capacity
        index = 0
        while index < self._size:
            new_items[index] = self._items[index]
            index += 1
        self._items = new_items
        self._capacity = new_capacity

    def append(self, value: Any) -> None:
        if self._size == self._capacity:
            self._grow()
        self._items[self._size] = value
        self._size += 1

    def get(self, index: int) -> Any:
        self._check_index(index)
        return self._items[index]

    def set(self, index: int, value: Any) -> None:
        self._check_index(index)
        self._items[index] = value

    def remove(self, index: int) -> Any:
        self._check_index(index)
        removed = self._items[index]
        cursor = index
        while cursor < self._size - 1:
            self._items[cursor] = self._items[cursor + 1]
            cursor += 1
        self._size -= 1
        self._items[self._size] = None
        return removed

    def pop(self) -> Any:
        if self._size == 0:
            return None
        self._size -= 1
        value = self._items[self._size]
        self._items[self._size] = None
        return value

    def size(self) -> int:
        return self._size

    def capacity(self) -> int:
        return self._capacity

    def to_list(self) -> List[Any]:
        result = []
        index = 0
        while index < self._size:
            result.append(self._items[index])
            index += 1
        return result

    def _check_index(self, index: int) -> None:
        if index < 0 or index >= self._size:
            raise IndexError("dynamic array index out of range")

    def __iter__(self) -> Iterator[Any]:
        index = 0
        while index < self._size:
            yield self._items[index]
            index += 1
