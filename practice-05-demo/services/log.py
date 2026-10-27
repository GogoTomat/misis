import time


def log(service: str, message: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {service:<9} {message}", flush=True)
