import bisect
import hashlib
import random
import sys
from collections import Counter

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

KEYS = [f"customer:{i}" for i in range(100_000)]
VIRTUAL_NODES = 100
LOGICAL_SHARDS = 4096


def h(value: str) -> int:
    return int.from_bytes(hashlib.md5(value.encode()).digest()[:8], "big")


def modulo(key: str, shards: int) -> int:
    return h(key) % shards


class Ring:
    def __init__(self, nodes: int, virtual: int = VIRTUAL_NODES) -> None:
        points = sorted((h(f"node-{n}#{v}"), n) for n in range(nodes) for v in range(virtual))
        self.hashes = [p[0] for p in points]
        self.nodes = [p[1] for p in points]

    def node(self, key: str) -> int:
        index = bisect.bisect(self.hashes, h(key)) % len(self.hashes)
        return self.nodes[index]


def moved_share(before: dict, after: dict) -> float:
    return sum(before[k] != after[k] for k in KEYS) / len(KEYS)


def spread(assignment: dict) -> str:
    counts = Counter(assignment.values())
    return f"min {min(counts.values())}, max {max(counts.values())}"


def logical_mapping(servers: int) -> list[int]:
    return [shard % servers for shard in range(LOGICAL_SHARDS)]


def rebalance(mapping: list[int], new_server: int) -> list[int]:
    result = list(mapping)
    target = LOGICAL_SHARDS // (new_server + 1)
    for shard in range(LOGICAL_SHARDS):
        if target == 0:
            break
        if shard % (new_server + 1) == new_server:
            result[shard] = new_server
            target -= 1
    return result


def main() -> None:
    random.seed(6)
    print(f"{len(KEYS)} ключей, добавляем пятый сервер к четырём\n")

    before = {k: modulo(k, 4) for k in KEYS}
    after = {k: modulo(k, 5) for k in KEYS}
    print("Шаг 1. hash(key) mod N")
    print(f"   распределение на 4 серверах: {spread(before)}")
    print(f"   переехало ключей при 4 → 5: {moved_share(before, after):.1%}")

    ring4, ring5 = Ring(4), Ring(5)
    before = {k: ring4.node(k) for k in KEYS}
    after = {k: ring5.node(k) for k in KEYS}
    print(f"\nШаг 2. Консистентное хеширование ({VIRTUAL_NODES} виртуальных точек на сервер)")
    print(f"   распределение на 4 серверах: {spread(before)}")
    print(f"   переехало ключей при 4 → 5: {moved_share(before, after):.1%}")
    one_point = Ring(4, virtual=1)
    print(f"   с одной точкой на сервер:    {spread({k: one_point.node(k) for k in KEYS})}")

    map4 = logical_mapping(4)
    map5 = rebalance(map4, 4)
    before = {k: map4[h(k) % LOGICAL_SHARDS] for k in KEYS}
    after = {k: map5[h(k) % LOGICAL_SHARDS] for k in KEYS}
    moved_shards = sum(a != b for a, b in zip(map4, map5))
    print(f"\nШаг 3. {LOGICAL_SHARDS} логических шардов поверх физических серверов")
    print("   ключ → логический шард не меняется никогда")
    print(f"   переносим логических шардов: {moved_shards} из {LOGICAL_SHARDS}")
    print(f"   переехало ключей: {moved_share(before, after):.1%}, распределение на 5: {spread(after)}")

    print("\nШаг 4. Горячий ключ: равномерные ключи ≠ равномерная нагрузка")
    ring = Ring(4)
    requests = Counter()
    celebrity = "customer:777"
    for _ in range(200_000):
        key = celebrity if random.random() < 0.3 else random.choice(KEYS)
        requests[ring.node(key)] += 1
    total = sum(requests.values())
    for node in range(4):
        mark = "  ← здесь живёт customer:777" if node == ring.node(celebrity) else ""
        print(f"   сервер {node}: {requests[node] / total:.0%} запросов{mark}")


if __name__ == "__main__":
    main()
