import sys
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)


def log(who: str, message: str) -> None:
    now = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"{now}  {who:<11} {message}", flush=True)


def title(text: str) -> None:
    print(f"\n=== {text} ===", flush=True)
