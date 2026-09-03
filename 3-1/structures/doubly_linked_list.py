"""LRU 순서를 O(1)에 갱신하기 위한 이중 연결 리스트."""

from typing import Any, Iterator, Optional


class DoublyLinkedNode:
    """앞/뒤 노드와 실제 데이터를 보관하는 리스트 노드."""

    __slots__ = ("prev", "next", "data")

    def __init__(self, data: Any) -> None:
        self.prev = None  # type: Optional[DoublyLinkedNode]
        self.next = None  # type: Optional[DoublyLinkedNode]
        self.data = data


class DoublyLinkedList:
    """삽입, 삭제, 노드 이동을 모두 O(1)에 수행한다."""

    def __init__(self) -> None:
        self.head = None  # type: Optional[DoublyLinkedNode]
        self.tail = None  # type: Optional[DoublyLinkedNode]
        self._size = 0

    def insert_front(self, data: Any) -> DoublyLinkedNode:
        node = DoublyLinkedNode(data)
        node.next = self.head
        if self.head is None:
            self.tail = node
        else:
            self.head.prev = node
        self.head = node
        self._size += 1
        return node

    def insert_back(self, data: Any) -> DoublyLinkedNode:
        node = DoublyLinkedNode(data)
        node.prev = self.tail
        if self.tail is None:
            self.head = node
        else:
            self.tail.next = node
        self.tail = node
        self._size += 1
        return node

    def remove_front(self) -> Any:
        if self.head is None:
            return None
        node = self.head
        self.remove_node(node)
        return node.data

    def remove_back(self) -> Any:
        if self.tail is None:
            return None
        node = self.tail
        self.remove_node(node)
        return node.data

    def remove_node(self, node: DoublyLinkedNode) -> Any:
        if node.prev is None:
            self.head = node.next
        else:
            node.prev.next = node.next

        if node.next is None:
            self.tail = node.prev
        else:
            node.next.prev = node.prev

        node.prev = None
        node.next = None
        self._size -= 1
        return node.data

    def move_to_front(self, node: DoublyLinkedNode) -> None:
        if node is self.head:
            return

        if node.prev is not None:
            node.prev.next = node.next
        if node.next is not None:
            node.next.prev = node.prev
        else:
            self.tail = node.prev

        node.prev = None
        node.next = self.head
        if self.head is not None:
            self.head.prev = node
        self.head = node
        if self.tail is None:
            self.tail = node

    def size(self) -> int:
        return self._size

    def iter_front(self) -> Iterator[Any]:
        current = self.head
        while current is not None:
            yield current.data
            current = current.next

    def iter_back(self) -> Iterator[Any]:
        current = self.tail
        while current is not None:
            yield current.data
            current = current.prev
