"""삽입, 탐색, 삭제와 중위 순회를 지원하는 이진 탐색 트리."""

from typing import Any, List, Optional

from .dynamic_array import DynamicArray


class BinarySearchNode:
    __slots__ = ("key", "value", "left", "right")

    def __init__(self, key: Any, value: Any) -> None:
        self.key = key
        self.value = value
        self.left = None  # type: Optional[BinarySearchNode]
        self.right = None  # type: Optional[BinarySearchNode]


class BinarySearchTree:
    def __init__(self) -> None:
        self.root = None  # type: Optional[BinarySearchNode]

    def insert(self, key: Any, value: Any) -> None:
        if self.root is None:
            self.root = BinarySearchNode(key, value)
            return
        current = self.root
        while True:
            if key == current.key:
                current.value = value
                return
            if key < current.key:
                if current.left is None:
                    current.left = BinarySearchNode(key, value)
                    return
                current = current.left
            else:
                if current.right is None:
                    current.right = BinarySearchNode(key, value)
                    return
                current = current.right

    def search(self, key: Any) -> Any:
        node = self._find(key)
        if node is None:
            return None
        return node.value

    def delete(self, key: Any) -> bool:
        parent = None
        current = self.root
        while current is not None and current.key != key:
            parent = current
            current = current.left if key < current.key else current.right
        if current is None:
            return False

        if current.left is not None and current.right is not None:
            successor_parent = current
            successor = current.right
            while successor.left is not None:
                successor_parent = successor
                successor = successor.left
            current.key = successor.key
            current.value = successor.value
            parent = successor_parent
            current = successor

        child = current.left if current.left is not None else current.right
        if parent is None:
            self.root = child
        elif parent.left is current:
            parent.left = child
        else:
            parent.right = child
        return True

    def inorder(self) -> List[Any]:
        result = DynamicArray()
        self._inorder(self.root, result)
        return result.to_list()

    def _find(self, key: Any) -> Optional[BinarySearchNode]:
        current = self.root
        while current is not None:
            if key == current.key:
                return current
            current = current.left if key < current.key else current.right
        return None

    def _inorder(self, node: Optional[BinarySearchNode], result: DynamicArray) -> None:
        if node is None:
            return
        self._inorder(node.left, result)
        result.append(node.key)
        self._inorder(node.right, result)
