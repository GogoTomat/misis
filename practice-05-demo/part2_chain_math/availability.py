import random

MINUTES_PER_MONTH = 30 * 24 * 60
SERVICE_AVAILABILITY = 0.999
TRIALS = 200_000
CHAIN_LENGTHS = [1, 3, 5, 10, 15]


def simulate(chain_length: int) -> float:
    successes = 0
    for _ in range(TRIALS):
        if all(random.random() < SERVICE_AVAILABILITY for _ in range(chain_length)):
            successes += 1
    return successes / TRIALS


def main() -> None:
    random.seed(5)
    print(f"Каждый сервис доступен {SERVICE_AVAILABILITY:.1%}\n")
    print(f"{'звеньев':>8} {'формула':>10} {'симуляция':>10} {'простой в месяц':>17}")
    for n in CHAIN_LENGTHS:
        formula = SERVICE_AVAILABILITY ** n
        simulated = simulate(n)
        downtime_hours = (1 - formula) * MINUTES_PER_MONTH / 60
        print(f"{n:>8} {formula:>10.3%} {simulated:>10.3%} {downtime_hours:>14.1f} ч")


if __name__ == "__main__":
    main()
