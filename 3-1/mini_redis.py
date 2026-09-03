"""CLI 기반 Mini Redis의 핵심 저장소와 명령 처리기."""

import time
from typing import Callable, List, Optional, Tuple

from pubsub import PubSubBroker
from structures.doubly_linked_list import DoublyLinkedList, DoublyLinkedNode
from structures.hash_map import HashMap
from structures.min_heap import MinHeap


INTEGER_ERROR = "(error) ERR value is not an integer or out of range"
OOM_ERROR = "(error) OOM command not allowed when used_memory > 'maxmemory'"
SYNTAX_ERROR = "(error) ERR syntax error"


class Entry:
    """해시맵 값과 LRU/TTL 메타데이터를 한곳에서 연결한다."""

    __slots__ = ("key", "value", "lru_node", "expire_at")

    def __init__(self, key: str, value: str) -> None:
        self.key = key
        self.value = value
        self.lru_node = None  # type: Optional[DoublyLinkedNode]
        self.expire_at = None  # type: Optional[float]


class MiniRedis:
    """String, LRU 메모리 제한, TTL을 제공하는 인메모리 저장소."""

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._store = HashMap()
        self._lru = DoublyLinkedList()
        self._expirations = MinHeap()
        self._clock = clock
        self.maxmemory = 0
        self.used_memory = 0
        self.evicted_keys = 0
        self.pubsub = PubSubBroker()

    @staticmethod
    def _entry_size(key: str, value: str) -> int:
        return len(key.encode("utf-8")) + len(value.encode("utf-8"))

    def _delete_entry(self, entry: Entry) -> None:
        removed = self._store.remove(entry.key)
        if removed is None:
            return
        if entry.lru_node is not None:
            self._lru.remove_node(entry.lru_node)
            entry.lru_node = None
        self.used_memory -= self._entry_size(entry.key, entry.value)
        entry.expire_at = None

    def _purge_expired(self) -> None:
        now = self._clock()
        while True:
            item = self._expirations.peek()
            if item is None or item.expire_at > now:
                return
            self._expirations.pop()
            entry = self._store.get(item.key)
            if (
                entry is not None
                and entry.expire_at is not None
                and entry.expire_at == item.expire_at
                and entry.expire_at <= now
            ):
                self._delete_entry(entry)

    def set(self, key: str, value: str) -> str:
        self._purge_expired()
        new_size = self._entry_size(key, value)
        if self.maxmemory > 0 and new_size > self.maxmemory:
            return OOM_ERROR

        entry = self._store.get(key)
        if entry is None:
            entry = Entry(key, value)
            entry.lru_node = self._lru.insert_front(entry)
            self._store.put(key, entry)
            self.used_memory += new_size
        else:
            self.used_memory -= self._entry_size(entry.key, entry.value)
            entry.value = value
            entry.expire_at = None
            self.used_memory += new_size
            self._lru.move_to_front(entry.lru_node)

        self._evict_if_needed()
        return "OK"

    def _evict_if_needed(self) -> None:
        while self.maxmemory > 0 and self.used_memory > self.maxmemory:
            lru_node = self._lru.tail
            if lru_node is None:
                return
            self._delete_entry(lru_node.data)
            self.evicted_keys += 1

    def get(self, key: str) -> Optional[str]:
        self._purge_expired()
        entry = self._store.get(key)
        if entry is None:
            return None
        self._lru.move_to_front(entry.lru_node)
        return entry.value

    def delete(self, key: str) -> int:
        self._purge_expired()
        entry = self._store.get(key)
        if entry is None:
            return 0
        self._delete_entry(entry)
        return 1

    def exists(self, key: str) -> int:
        self._purge_expired()
        return 1 if self._store.contains(key) else 0

    def dbsize(self) -> int:
        self._purge_expired()
        return self._store.size()

    def keys(self) -> List[str]:
        self._purge_expired()
        return self._store.keys()

    def config_set_maxmemory(self, maximum: int) -> str:
        self.maxmemory = maximum
        return "OK"

    def info_memory(self) -> str:
        self._purge_expired()
        return (
            "used_memory:" + str(self.used_memory) + "\n"
            "maxmemory:" + str(self.maxmemory) + "\n"
            "evicted_keys:" + str(self.evicted_keys)
        )

    def expire(self, key: str, seconds: int) -> int:
        self._purge_expired()
        entry = self._store.get(key)
        if entry is None:
            return 0
        if seconds <= 0:
            self._delete_entry(entry)
            return 1
        expire_at = self._clock() + seconds
        entry.expire_at = expire_at
        self._expirations.push(expire_at, key)
        return 1

    def ttl(self, key: str) -> int:
        self._purge_expired()
        entry = self._store.get(key)
        if entry is None:
            return -2
        if entry.expire_at is None:
            return -1
        remaining = int(entry.expire_at - self._clock())
        return remaining if remaining >= 0 else -2

    def execute(self, line: str) -> Optional[str]:
        try:
            tokens = parse_command(line)
        except ValueError:
            return SYNTAX_ERROR
        if not tokens:
            return None

        command = tokens[0].upper()
        wrong_arguments = "(error) ERR wrong number of arguments for '" + command + "' command"

        if command == "SET":
            if len(tokens) != 3:
                return wrong_arguments
            return self.set(tokens[1], tokens[2])
        if command == "GET":
            if len(tokens) != 2:
                return wrong_arguments
            value = self.get(tokens[1])
            return "(nil)" if value is None else quote_value(value)
        if command == "DEL":
            if len(tokens) != 2:
                return wrong_arguments
            return integer_output(self.delete(tokens[1]))
        if command == "EXISTS":
            if len(tokens) != 2:
                return wrong_arguments
            return integer_output(self.exists(tokens[1]))
        if command == "DBSIZE":
            if len(tokens) != 1:
                return wrong_arguments
            return integer_output(self.dbsize())
        if command == "KEYS":
            if len(tokens) != 1:
                return wrong_arguments
            return keys_output(self.keys())
        if command == "CONFIG":
            if len(tokens) != 4:
                return wrong_arguments
            if tokens[1].upper() != "SET" or tokens[2].lower() != "maxmemory":
                return SYNTAX_ERROR
            valid, maximum = parse_integer(tokens[3])
            if not valid or maximum < 0:
                return INTEGER_ERROR
            return self.config_set_maxmemory(maximum)
        if command == "INFO":
            if len(tokens) != 2:
                return wrong_arguments
            if tokens[1].lower() != "memory":
                return SYNTAX_ERROR
            return self.info_memory()
        if command == "EXPIRE":
            if len(tokens) != 3:
                return wrong_arguments
            valid, seconds = parse_integer(tokens[2])
            if not valid:
                return INTEGER_ERROR
            return integer_output(self.expire(tokens[1], seconds))
        if command == "TTL":
            if len(tokens) != 2:
                return wrong_arguments
            return integer_output(self.ttl(tokens[1]))

        # 보너스: 한 REPL에서 기본 subscriber id는 "cli"를 사용한다.
        if command == "SUBSCRIBE":
            if len(tokens) not in (2, 3):
                return wrong_arguments
            subscriber = tokens[2] if len(tokens) == 3 else "cli"
            return integer_output(self.pubsub.subscribe(tokens[1], subscriber))
        if command == "PUBLISH":
            if len(tokens) != 3:
                return wrong_arguments
            return integer_output(self.pubsub.publish(tokens[1], tokens[2]))
        if command == "POLL":
            if len(tokens) not in (2, 3):
                return wrong_arguments
            subscriber = tokens[2] if len(tokens) == 3 else "cli"
            message = self.pubsub.poll(tokens[1], subscriber)
            return "(nil)" if message is None else quote_value(message)

        return "(error) ERR unknown command '" + command + "'"


def parse_command(line: str) -> List[str]:
    """공백 구분과 작은/큰따옴표 값을 처리하는 간단한 파서."""
    tokens = []
    current = []
    quote = None
    escaped = False
    token_started = False

    for character in line:
        if escaped:
            if character == "n":
                current.append("\n")
            elif character == "t":
                current.append("\t")
            else:
                current.append(character)
            escaped = False
            token_started = True
        elif character == "\\":
            escaped = True
            token_started = True
        elif quote is not None:
            if character == quote:
                quote = None
            else:
                current.append(character)
            token_started = True
        elif character == '"' or character == "'":
            quote = character
            token_started = True
        elif character.isspace():
            if token_started:
                tokens.append("".join(current))
                current = []
                token_started = False
        else:
            current.append(character)
            token_started = True

    if escaped:
        current.append("\\")
    if quote is not None:
        raise ValueError("unterminated quote")
    if token_started:
        tokens.append("".join(current))
    return tokens


def parse_integer(text: str) -> Tuple[bool, int]:
    """부호가 있는 64비트 십진 정수만 허용한다."""
    if not text:
        return False, 0
    sign = 1
    index = 0
    if text[0] == "+" or text[0] == "-":
        sign = -1 if text[0] == "-" else 1
        index = 1
    if index == len(text):
        return False, 0

    value = 0
    while index < len(text):
        character = text[index]
        if character < "0" or character > "9":
            return False, 0
        value = value * 10 + (ord(character) - ord("0"))
        index += 1
    value *= sign
    if value < -(1 << 63) or value > (1 << 63) - 1:
        return False, 0
    return True, value


def quote_value(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\t", "\\t")
    return '"' + escaped + '"'


def integer_output(value: int) -> str:
    return "(integer) " + str(value)


def keys_output(keys: List[str]) -> str:
    if not keys:
        return "(empty array)"
    lines = []
    index = 0
    while index < len(keys):
        lines.append(str(index + 1) + ". " + quote_value(keys[index]))
        index += 1
    return "\n".join(lines)
