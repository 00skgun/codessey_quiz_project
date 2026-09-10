"""필수 명령, 그래프 탐색, 정렬, 역색인을 검증하는 표준 라이브러리 테스트."""

from datetime import datetime, timezone
import unittest

from main import (
    Commit, InvertedIndex, MiniGit, ancestor_hashes, merge_sort,
    shortest_path, topological_order,
)


class MiniGitTests(unittest.TestCase):
    def setUp(self):
        self.repo = MiniGit()
        self.repo.execute('init "Alice Kim"')

    def commit(self, message="Initial commit"):
        self.repo.execute(f'commit "{message}"')
        return self.repo.head

    def test_initialization_and_case_insensitive_commands(self):
        self.assertEqual(self.repo.user, "Alice Kim")
        self.assertEqual(self.repo.branches, {"main": None})
        self.repo.execute('CoMmIt "hello world"')
        self.assertEqual(self.repo.head, "00000001")

    def test_branch_divergence_and_log(self):
        root = self.commit()
        self.repo.execute("branch feature")
        self.repo.execute("switch feature")
        feature = self.commit("Add login feature")
        self.repo.execute("switch main")
        main = self.commit("Add payment feature")
        self.assertEqual(self.repo.commits[feature].parents, (root,))
        self.assertEqual(self.repo.commits[main].parents, (root,))
        self.assertEqual(self.repo.branches["feature"], feature)
        log = self.repo.execute("log")
        self.assertLess(log.index(root), log.index(feature))
        self.assertLess(log.index(root), log.index(main))
        self.assertEqual(self.repo.execute(f"path {feature} {main}"), f"{feature}->{root}->{main}")
        self.assertEqual(self.repo.execute(f"path {root} {feature}"), f"{root}->{feature}")

    def test_disconnected_roots_and_identity_path(self):
        self.repo.execute("branch empty")
        root = self.commit()
        self.repo.execute("switch empty")
        other = self.commit("Independent root")
        self.assertEqual(self.repo.execute(f"path {root} {other}"), "No path")
        self.assertEqual(self.repo.execute(f"path {root} {root}"), root)
        self.assertEqual(self.repo.execute(f"ancestors {root}"), "No ancestors")

    def test_indexed_search_and_spaces(self):
        first = self.commit("Add LOGIN login feature")
        self.commit("Add payment feature")
        self.assertEqual(self.repo.index.search("LOGIN"), {first})
        self.assertEqual(self.repo.index.search("login feature"), {first})
        self.assertEqual(self.repo.index.search("log"), set())
        self.assertIn(first, self.repo.execute('search "LOGIN feature"'))
        self.assertEqual(self.repo.execute('search "missing login"'), "No matches")
        self.assertEqual(self.repo.execute("search --author=alice"), "No matches")
        self.assertEqual(self.repo.execute('search --author="Alice Kim"').count("commit 000"), 2)

    def test_invalid_input_preserves_state(self):
        root = self.commit()
        cases = [
            ("switch missing", "Unknown branch: missing"),
            ("ancestors missing", "Unknown commit: missing"),
            (f"path {root} missing", "Unknown commit: missing"),
            ("branch main", "Branch already exists: main"),
            ('init "Bob"', "Repository already initialized"),
            ('commit "broken', "Invalid args"),
            ("commit too many words", "Invalid args"),
            ('commit " "', "Invalid args"),
            ("log --sort-by=unknown", "Invalid args"),
            ('search --author=""', "Invalid args"),
            ("search --wrong=x", "Invalid args"),
            ("quit extra", "Invalid args"),
            ("merge feature", "Unknown command: merge"),
            ("diff a b", "Unknown command: diff"),
        ]
        for command, expected in cases:
            with self.subTest(command=command):
                with self.assertRaises(ValueError) as error:
                    self.repo.execute(command)
                self.assertEqual(str(error.exception), expected)
                self.assertEqual(self.repo.head, root)
                self.assertEqual(len(self.repo.commits), 1)

    def test_empty_repository_and_exit(self):
        self.assertEqual(self.repo.execute("log"), "No commits")
        self.assertEqual(self.repo.execute("log --sort-by=date"), "No commits")
        self.assertEqual(self.repo.execute("search absent"), "No matches")
        self.assertEqual(self.repo.execute("   "), "")
        self.assertEqual(self.repo.execute("ExIt"), "Bye.")
        self.assertEqual(self.repo.execute("QUIT"), "Bye.")
        with self.assertRaisesRegex(ValueError, "Repository not initialized"):
            MiniGit().execute("commit hello")

    def test_unique_hashes_and_iterative_ancestors(self):
        for _ in range(1500):
            self.repo.create_commit("same message")
        self.assertEqual(len(self.repo.commits), 1500)
        ancestors = ancestor_hashes(self.repo.commits, self.repo.head)
        self.assertEqual(len(ancestors), 1499)
        self.assertNotIn(self.repo.head, ancestors)

    def test_sort_options(self):
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        later = datetime(2026, 1, 2, tzinfo=timezone.utc)
        self.repo.commits = {
            "a": Commit("a", "first", "Zoe", later, ()),
            "b": Commit("b", "second", "Alice", now, ()),
            "c": Commit("c", "third", "Alice", now, ()),
        }
        for option in ("date", "author"):
            result = self.repo.execute(f"log --sort-by={option}")
            self.assertLess(result.index("commit b"), result.index("commit c"))
            self.assertLess(result.index("commit c"), result.index("commit a"))


class AlgorithmTests(unittest.TestCase):
    def test_merge_sort_boundaries_and_stability(self):
        for data, expected in [([], []), ([1], [1]), ([3, 1, 2], [1, 2, 3]),
                               ([4, 3, 2, 1], [1, 2, 3, 4]), ([2, 2, 1], [1, 2, 2])]:
            self.assertEqual(merge_sort(data, key=lambda x: x), expected)
        records = [(2, "a"), (1, "b"), (2, "c"), (1, "d")]
        self.assertEqual(merge_sort(records, key=lambda x: x[0]),
                         [(1, "b"), (1, "d"), (2, "a"), (2, "c")])
        self.assertEqual(records, [(2, "a"), (1, "b"), (2, "c"), (1, "d")])

    def test_topological_order_and_shared_ancestors(self):
        now = datetime.now(timezone.utc)
        # CLI에 병합 기능을 추가하지 않고, 일반 DAG 탐색을 독립 검증한다.
        commits = {
            "d": Commit("d", "child", "A", now, ("b", "c")),
            "c": Commit("c", "right", "A", now, ("a",)),
            "b": Commit("b", "left", "A", now, ("a",)),
            "a": Commit("a", "root", "A", now, ()),
        }
        positions = {c.hash: i for i, c in enumerate(topological_order(commits))}
        for child in commits.values():
            for parent in child.parents:
                self.assertLess(positions[parent], positions[child.hash])
        self.assertEqual(ancestor_hashes(commits, "d"), {"a", "b", "c"})

    def test_shortest_path_lexicographic_tie(self):
        graph = {"s": {"b", "a"}, "a": {"s", "t"},
                 "b": {"s", "t"}, "t": {"b", "a"}}
        self.assertEqual(shortest_path(graph, "s", "t"), ["s", "a", "t"])
        self.assertEqual(shortest_path(graph, "t", "s"), ["t", "a", "s"])

    def test_path_string_separator_tie(self):
        graph = {"s": {"a", "a0"}, "a": {"s", "t"},
                 "a0": {"s", "t"}, "t": {"a", "a0"}}
        self.assertEqual(shortest_path(graph, "s", "t"), ["s", "a", "t"])

    def test_index_authors_and_punctuation(self):
        index = InvertedIndex()
        now = datetime.now(timezone.utc)
        index.add(Commit("a", "Fix bug, bug,", "Alice Kim", now, ()))
        index.add(Commit("b", "Fix test", "Bob", now, ()))
        self.assertEqual(index.search("Alice Kim", True), {"a"})
        self.assertEqual(index.search("Bob", True), {"b"})
        self.assertEqual(index.search("bug,"), {"a"})
        self.assertEqual(index.search("bug"), set())
        self.assertEqual(index.search("fix"), {"a", "b"})


if __name__ == "__main__":
    unittest.main()
