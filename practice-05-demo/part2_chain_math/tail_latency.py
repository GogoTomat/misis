import random
import statistics

REQUESTS = 20_000
SLOW_SHARE = 0.01
THRESHOLD_MS = 100
FAN_OUT = [1, 5, 10, 20, 50, 100]


def one_call() -> float:
    if random.random() < SLOW_SHARE:
        return random.uniform(100, 200)
    return max(1.0, random.gauss(10, 2))


def main() -> None:
    random.seed(5)
    single = [one_call() for _ in range(REQUESTS)]
    slow_single = sum(t > THRESHOLD_MS for t in single) / REQUESTS
    print(f"Один сервис: p50 = {statistics.median(single):.0f} мс, медленнее {THRESHOLD_MS} мс — {slow_single:.1%} запросов\n")
    print(f"{'вызовов':>8} {'медленнее 100 мс':>17} {'формула':>9} {'p50 ответа':>11}")
    for n in FAN_OUT:
        totals = [max(one_call() for _ in range(n)) for _ in range(REQUESTS)]
        slow = sum(t > THRESHOLD_MS for t in totals) / REQUESTS
        formula = 1 - (1 - SLOW_SHARE) ** n
        print(f"{n:>8} {slow:>17.1%} {formula:>9.1%} {statistics.median(totals):>8.0f} мс")


if __name__ == "__main__":
    main()
