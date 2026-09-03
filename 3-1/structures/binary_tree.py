"""배열로 완전 이진 트리를 표현하고 네 가지 순회를 제공한다."""

from typing import Any, List

from .dynamic_array import DynamicArray


class BinaryTree:
    def __init__(self) -> None:
        self._nodes = DynamicArray()

    def add(self, value: Any) -> None:
        self._nodes.append(value)

    def preorder(self) -> List[Any]:
        result = DynamicArray()
        self._preorder(0, result)
        return result.to_list()

    def inorder(self) -> List[Any]:
        result = DynamicArray()
        self._inorder(0, result)
        return result.to_list()

    def postorder(self) -> List[Any]:
        result = DynamicArray()
        self._postorder(0, result)
        return result.to_list()

    def level_order(self) -> List[Any]:
        return self._nodes.to_list()

    def _preorder(self, index: int, result: DynamicArray) -> None:
        if index >= self._nodes.size():
            return
        result.append(self._nodes.get(index))
        self._preorder(index * 2 + 1, result)
        self._preorder(index * 2 + 2, result)

    def _inorder(self, index: int, result: DynamicArray) -> None:
        if index >= self._nodes.size():
            return
        self._inorder(index * 2 + 1, result)
        result.append(self._nodes.get(index))
        self._inorder(index * 2 + 2, result)

    def _postorder(self, index: int, result: DynamicArray) -> None:
        if index >= self._nodes.size():
            return
        self._postorder(index * 2 + 1, result)
        self._postorder(index * 2 + 2, result)
        result.append(self._nodes.get(index))
