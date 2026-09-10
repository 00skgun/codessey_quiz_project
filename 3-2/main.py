"""커밋 메타데이터와 그래프 알고리즘을 학습하는 메모리 기반 Mini Git."""

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
import shlex
from typing import Callable, Iterable, TypeVar


T = TypeVar("T")


def merge_sort(items: Iterable[T], key: Callable) -> list[T]:
    """비교 키를 받는 안정적인 병합 정렬. 표준 정렬 API를 사용하지 않는다."""
    source = list(items)
    size = len(source)
    target = source.copy()
    width = 1
    while width < size:
        for start in range(0, size, width * 2):
            middle = min(start + width, size)
            end = min(start + width * 2, size)
            left, right = start, middle
            for output in range(start, end):
                if left < middle and (
                    right >= end or key(source[left]) <= key(source[right])
                ):
                    target[output] = source[left]
                    left += 1
                else:
                    target[output] = source[right]
                    right += 1
        source, target = target, source
        width *= 2
    return source


@dataclass(frozen=True)
class Commit:
    """불변 커밋 노드. parents에는 부모의 hash들을 저장한다."""

    hash: str
    message: str
    author: str
    timestamp: datetime
    parents: tuple[str, ...]


class InvertedIndex:
    """메시지 토큰과 작성자에서 해당 커밋 hash 집합으로 연결하는 역색인."""

    def __init__(self) -> None:
        self.keywords: dict[str, set[str]] = {}
        self.authors: dict[str, set[str]] = {}

    def add(self, commit: Commit) -> None:
        """동일 메시지의 반복 토큰은 한 번만 색인한다."""
        for token in set(commit.message.lower().split()):
            self.keywords.setdefault(token, set()).add(commit.hash)
        self.authors.setdefault(commit.author, set()).add(commit.hash)

    def search(self, query: str, by_author: bool = False) -> set[str]:
        """작성자는 정확히 일치, 여러 검색 토큰은 모두 포함하는 커밋을 찾는다."""
        if by_author:
            return self.authors.get(query, set()).copy()
        postings = [self.keywords.get(token, set()) for token in set(query.lower().split())]
        if not postings:
            return set()
        # 가장 작은 후보 집합부터 교집합을 계산한다.
        smallest = min(postings, key=len)
        matches = smallest.copy()
        for posting in postings:
            matches.intersection_update(posting)
            if not matches:
                break
        return matches


def topological_order(commits: dict[str, Commit]) -> list[Commit]:
    """Kahn 알고리즘으로 저장소 전체를 부모가 먼저 나오도록 순회한다."""
    indegrees = {h: len(commit.parents) for h, commit in commits.items()}
    children: dict[str, list[str]] = {h: [] for h in commits}
    for h, commit in commits.items():
        for parent in commit.parents:
            children[parent].append(h)
    ready = deque(h for h, degree in indegrees.items() if degree == 0)
    result = []
    while ready:
        current = ready.popleft()
        result.append(commits[current])
        for child in children[current]:
            indegrees[child] -= 1
            if indegrees[child] == 0:
                ready.append(child)
    if len(result) != len(commits):
        raise ValueError("Invalid commit graph")
    return result


def shortest_path(
    neighbors: dict[str, set[str]], start: str, end: str
) -> list[str] | None:
    """역방향 BFS 거리와 탐욕 선택으로 사전순 최소인 최단 경로를 구한다."""
    distances = {end: 0}
    queue = deque([end])
    while queue:
        current = queue.popleft()
        for neighbor in neighbors[current]:
            if neighbor not in distances:
                distances[neighbor] = distances[current] + 1
                queue.append(neighbor)
    if start not in distances:
        return None
    path = [start]
    while path[-1] != end:
        current = path[-1]
        candidates = (
            h for h in neighbors[current]
            if distances.get(h) == distances[current] - 1
        )
        # 구분자까지 비교하여 hash 길이가 달라도 경로 문자열 기준을 지킨다.
        next_hash = min(candidates, key=lambda h: h + ("->" if h != end else ""))
        path.append(next_hash)
    return path


def ancestor_hashes(commits: dict[str, Commit], start: str) -> set[str]:
    """반복형 DFS로 자신을 제외한 모든 조상을 중복 없이 찾는다."""
    visited: set[str] = set()
    stack = list(commits[start].parents)
    while stack:
        current = stack.pop()
        if current in visited:
            continue
        visited.add(current)
        stack.extend(commits[current].parents)
    return visited


class MiniGit:
    """저장소 상태, 브랜치 포인터, 커밋 생성과 명령 실행을 관리한다."""

    def __init__(self) -> None:
        self.user: str | None = None
        self.current_branch = "main"
        self.branches: dict[str, str | None] = {}
        self.commits: dict[str, Commit] = {}
        self.neighbors: dict[str, set[str]] = {}
        self.index = InvertedIndex()
        self.counter = 0

    @property
    def head(self) -> str | None:
        """현재 브랜치가 가리키는 커밋. 아직 커밋이 없으면 None이다."""
        return self.branches.get(self.current_branch)

    def initialize(self, user: str) -> str:
        """최초 한 번 저장소를 초기화한다. 재초기화로 인한 데이터 손실을 막는다."""
        if self.user is not None:
            raise ValueError("Repository already initialized")
        self.user = user
        self.branches["main"] = None
        return f"Initialized repository.\nCurrent branch: main\nCurrent user: {user}"

    def create_commit(self, message: str) -> Commit:
        """기존 HEAD만 부모로 연결하므로 새 간선이 사이클을 만들지 않는다."""
        if self.user is None:
            raise ValueError("Repository not initialized")
        self.counter += 1
        commit_hash = f"{self.counter:08x}"
        parents = (self.head,) if self.head is not None else ()
        commit = Commit(
            commit_hash, message, self.user, datetime.now(timezone.utc), parents
        )
        self.commits[commit_hash] = commit
        self.neighbors[commit_hash] = set(parents)
        for parent in parents:
            self.neighbors[parent].add(commit_hash)
        self.branches[self.current_branch] = commit_hash
        self.index.add(commit)
        return commit

    def require_commit(self, commit_hash: str) -> None:
        """탐색 전에 요청한 hash가 저장소에 있는지 검증한다."""
        if commit_hash not in self.commits:
            raise ValueError(f"Unknown commit: {commit_hash}")

    @staticmethod
    def format_commits(commits: list[Commit], empty: str = "No commits") -> str:
        """커밋의 필수 메타데이터를 동일한 형식으로 표시한다."""
        if not commits:
            return empty
        return "\n".join(
            f"commit {c.hash} | author: {c.author} | "
            f"timestamp: {c.timestamp.isoformat()}\n    {c.message}"
            for c in commits
        )

    def execute(self, line: str) -> str:
        """명령을 파싱하고 실행한다. 잘못된 입력은 ValueError로 전달한다."""
        try:
            parts = shlex.split(line)
        except ValueError:
            raise ValueError("Invalid args") from None
        if not parts:
            return ""
        command, args = parts[0].upper(), parts[1:]
        counts = {
            "INIT": (1,), "BRANCH": (1,), "SWITCH": (1,), "COMMIT": (1,),
            "LOG": (0, 1), "PATH": (2,), "ANCESTORS": (1,),
            "SEARCH": (1,), "EXIT": (0,), "QUIT": (0,),
        }
        if command not in counts:
            raise ValueError(f"Unknown command: {parts[0]}")
        if len(args) not in counts[command] or any(not a.strip() for a in args):
            raise ValueError("Invalid args")
        if command in ("EXIT", "QUIT"):
            return "Bye."
        if command == "INIT":
            return self.initialize(args[0])
        if self.user is None:
            raise ValueError("Repository not initialized")
        if command == "BRANCH":
            name = args[0]
            if name in self.branches:
                raise ValueError(f"Branch already exists: {name}")
            self.branches[name] = self.head
            return f"Created branch: {name}"
        if command == "SWITCH":
            name = args[0]
            if name not in self.branches:
                raise ValueError(f"Unknown branch: {name}")
            self.current_branch = name
            return f"Switched to branch: {name}"
        if command == "COMMIT":
            commit = self.create_commit(args[0])
            return f"[{self.current_branch} {commit.hash}] {commit.message}"
        if command == "LOG":
            if not args:
                return self.format_commits(topological_order(self.commits))
            if args[0] == "--sort-by=date":
                key = lambda c: c.timestamp
            elif args[0] == "--sort-by=author":
                key = lambda c: c.author
            else:
                raise ValueError("Invalid args")
            return self.format_commits(merge_sort(self.commits.values(), key))
        if command == "PATH":
            for h in args:
                self.require_commit(h)
            path = shortest_path(self.neighbors, args[0], args[1])
            return "->".join(path) if path is not None else "No path"
        if command == "ANCESTORS":
            self.require_commit(args[0])
            hashes = ancestor_hashes(self.commits, args[0])
            commits = merge_sort((self.commits[h] for h in hashes), key=lambda c: c.hash)
            return self.format_commits(commits, "No ancestors")
        query = args[0]
        by_author = query.startswith("--author=")
        if by_author:
            query = query[len("--author="):]
            if not query.strip():
                raise ValueError("Invalid args")
        elif query.startswith("--"):
            raise ValueError("Invalid args")
        hashes = self.index.search(query, by_author)
        commits = merge_sort((self.commits[h] for h in hashes), key=lambda c: c.hash)
        return self.format_commits(commits, "No matches")


def main() -> None:
    """오류가 발생해도 계속 입력받는 REPL. EOF와 Ctrl+C로도 종료한다."""
    repository = MiniGit()
    print("Mini Git | INIT <user_name>으로 시작하세요. exit / quit로 종료합니다.")
    while True:
        try:
            line = input("mini-git> ")
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break
        try:
            output = repository.execute(line)
        except ValueError as error:
            print(error)
            continue
        if output:
            print(output)
        if output == "Bye.":
            break


if __name__ == "__main__":
    main()
