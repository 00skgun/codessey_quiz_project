"""Mini Redis REPL 인터페이스."""

from mini_redis import MiniRedis


def run_cli() -> None:
    database = MiniRedis()
    while True:
        try:
            line = input("mini-redis> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if line.strip().lower() in ("exit", "quit"):
            break
        result = database.execute(line)
        if result is not None:
            print(result)
