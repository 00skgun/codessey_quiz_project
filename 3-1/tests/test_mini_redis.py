import unittest

from mini_redis import INTEGER_ERROR, OOM_ERROR, MiniRedis, parse_command


class FakeClock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class MiniRedisCommandTests(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.redis = MiniRedis(self.clock)

    def test_string_commands(self):
        self.assertEqual(self.redis.execute('SET name "Alice Kim"'), "OK")
        self.assertEqual(self.redis.execute("GET name"), '"Alice Kim"')
        self.assertEqual(self.redis.execute("EXISTS name"), "(integer) 1")
        self.assertEqual(self.redis.execute("DBSIZE"), "(integer) 1")
        self.assertIn('"name"', self.redis.execute("KEYS"))
        self.assertEqual(self.redis.execute("DEL name"), "(integer) 1")
        self.assertEqual(self.redis.execute("DEL name"), "(integer) 0")
        self.assertEqual(self.redis.execute("GET name"), "(nil)")
        self.assertEqual(self.redis.execute("KEYS"), "(empty array)")

    def test_lru_eviction_and_memory_info(self):
        self.assertEqual(self.redis.execute("CONFIG SET maxmemory 30"), "OK")
        self.redis.execute('SET user:1 "Alice"')
        self.redis.execute('SET user:2 "Bob"')
        self.redis.execute('SET user:3 "Charlie"')

        self.assertEqual(self.redis.get("user:1"), None)
        self.assertEqual(self.redis.get("user:2"), "Bob")
        self.assertEqual(self.redis.used_memory, 22)
        self.assertEqual(
            self.redis.info_memory(),
            "used_memory:22\nmaxmemory:30\nevicted_keys:1",
        )

    def test_get_refreshes_lru(self):
        self.redis.config_set_maxmemory(8)
        self.redis.set("a", "111")
        self.redis.set("b", "222")
        self.assertEqual(self.redis.get("a"), "111")
        self.redis.set("c", "333")
        self.assertEqual(self.redis.get("a"), "111")
        self.assertIsNone(self.redis.get("b"))
        self.assertEqual(self.redis.get("c"), "333")

    def test_oom_does_not_modify_existing_data(self):
        self.redis.config_set_maxmemory(5)
        self.redis.set("a", "1")
        self.assertEqual(self.redis.set("a", "12345"), OOM_ERROR)
        self.assertEqual(self.redis.get("a"), "1")
        self.assertEqual(self.redis.set("long-key", "value"), OOM_ERROR)
        self.assertEqual(self.redis.dbsize(), 1)

    def test_utf8_memory_count(self):
        self.redis.set("한", "글")
        self.assertEqual(self.redis.used_memory, 6)
        self.redis.set("한", "글자")
        self.assertEqual(self.redis.used_memory, 9)

    def test_expire_ttl_and_lazy_heap_cleanup(self):
        self.redis.set("session", "value")
        self.assertEqual(self.redis.ttl("session"), -1)
        self.assertEqual(self.redis.expire("session", 5), 1)
        self.assertEqual(self.redis.ttl("session"), 5)

        self.clock.advance(2)
        self.assertEqual(self.redis.ttl("session"), 3)
        self.redis.expire("session", 10)
        self.clock.advance(4)
        self.assertEqual(self.redis.get("session"), "value")
        self.clock.advance(6)
        self.assertIsNone(self.redis.get("session"))
        self.assertEqual(self.redis.ttl("session"), -2)

    def test_overwrite_clears_ttl_and_nonpositive_expire_deletes(self):
        self.redis.set("key", "old")
        self.redis.expire("key", 10)
        self.redis.set("key", "new")
        self.assertEqual(self.redis.ttl("key"), -1)
        self.assertEqual(self.redis.expire("key", 0), 1)
        self.assertEqual(self.redis.exists("key"), 0)

    def test_expired_keys_do_not_count_as_eviction(self):
        self.redis.set("old", "value")
        self.redis.expire("old", 1)
        self.clock.advance(1)
        self.assertEqual(self.redis.dbsize(), 0)
        self.assertEqual(self.redis.used_memory, 0)
        self.assertEqual(self.redis.evicted_keys, 0)

    def test_errors(self):
        self.assertEqual(self.redis.execute("HELLO"), "(error) ERR unknown command 'HELLO'")
        self.assertEqual(
            self.redis.execute("GET"),
            "(error) ERR wrong number of arguments for 'GET' command",
        )
        self.assertEqual(self.redis.execute("CONFIG SET maxmemory abc"), INTEGER_ERROR)
        self.assertEqual(self.redis.execute("CONFIG SET maxmemory -1"), INTEGER_ERROR)
        self.assertEqual(self.redis.execute("EXPIRE key 1.5"), INTEGER_ERROR)
        self.assertEqual(self.redis.execute('SET key "unfinished'), "(error) ERR syntax error")

    def test_pubsub_bonus(self):
        self.assertEqual(self.redis.execute("SUBSCRIBE news alice"), "(integer) 1")
        self.assertEqual(self.redis.execute("SUBSCRIBE news bob"), "(integer) 2")
        self.assertEqual(self.redis.execute('PUBLISH news "hello team"'), "(integer) 2")
        self.assertEqual(self.redis.execute("POLL news alice"), '"hello team"')
        self.assertEqual(self.redis.execute("POLL news bob"), '"hello team"')
        self.assertEqual(self.redis.execute("POLL news bob"), "(nil)")


class ParserTests(unittest.TestCase):
    def test_quotes_spaces_empty_values_and_escapes(self):
        self.assertEqual(parse_command('SET key "Alice Kim"'), ["SET", "key", "Alice Kim"])
        self.assertEqual(parse_command('SET empty ""'), ["SET", "empty", ""])
        self.assertEqual(parse_command('SET quote "say \\"hi\\""'), ["SET", "quote", 'say "hi"'])


if __name__ == "__main__":
    unittest.main()
