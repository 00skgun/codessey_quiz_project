"""FNV-1a 해시와 체이닝 충돌 해결을 사용하는 해시맵."""

from typing import Any, List, Optional


class BucketNode:
    """한 버킷의 체인을 구성하는 단일 연결 노드."""

    __slots__ = ("key", "value", "next")

    def __init__(self, key: str, value: Any, next_node: Any = None) -> None:
        self.key = key
        self.value = value
        self.next = next_node  # type: Optional[BucketNode]


class HashMap:
    """로드 팩터가 0.75를 넘기 전에 버킷을 두 배로 확장한다."""

    _FNV_OFFSET = 14695981039346656037
    _FNV_PRIME = 1099511628211
    _MASK_64 = (1 << 64) - 1

    def __init__(self, initial_capacity: int = 8) -> None:
        capacity = 4
        while capacity < initial_capacity:
            capacity *= 2
        self._buckets = [None] * capacity
        self._size = 0

    def _hash(self, key: str) -> int:
        """문자열의 UTF-8 바이트를 FNV-1a 절차로 64비트 해싱한다."""
        value = self._FNV_OFFSET
        for byte in key.encode("utf-8"):
            value ^= byte
            value = (value * self._FNV_PRIME) & self._MASK_64
        return value

    def hash_index(self, key: str) -> int:
        """현재 버킷 배열에서 key가 들어갈 인덱스를 반환한다."""
        return self._hash(key) % len(self._buckets)

    def _find_node(self, key: str) -> Optional[BucketNode]:
        current = self._buckets[self.hash_index(key)]
        while current is not None:
            if current.key == key:
                return current
            current = current.next
        return None

    def put(self, key: str, value: Any) -> Any:
        existing = self._find_node(key)
        if existing is not None:
            old_value = existing.value
            existing.value = value
            return old_value

        if (self._size + 1) / len(self._buckets) > 0.75:
            self._resize(len(self._buckets) * 2)

        index = self.hash_index(key)
        self._buckets[index] = BucketNode(key, value, self._buckets[index])
        self._size += 1
        return None

    def get(self, key: str) -> Any:
        node = self._find_node(key)
        if node is None:
            return None
        return node.value

    def remove(self, key: str) -> Any:
        index = self.hash_index(key)
        current = self._buckets[index]
        previous = None
        while current is not None:
            if current.key == key:
                if previous is None:
                    self._buckets[index] = current.next
                else:
                    previous.next = current.next
                self._size -= 1
                return current.value
            previous = current
            current = current.next
        return None

    def contains(self, key: str) -> bool:
        return self._find_node(key) is not None

    def keys(self) -> List[str]:
        result = []
        bucket_index = 0
        while bucket_index < len(self._buckets):
            current = self._buckets[bucket_index]
            while current is not None:
                result.append(current.key)
                current = current.next
            bucket_index += 1
        return result

    def size(self) -> int:
        return self._size

    def capacity(self) -> int:
        return len(self._buckets)

    def _resize(self, new_capacity: int) -> None:
        old_buckets = self._buckets
        self._buckets = [None] * new_capacity

        bucket_index = 0
        while bucket_index < len(old_buckets):
            current = old_buckets[bucket_index]
            while current is not None:
                next_node = current.next
                new_index = self.hash_index(current.key)
                current.next = self._buckets[new_index]
                self._buckets[new_index] = current
                current = next_node
            bucket_index += 1
