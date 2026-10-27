import threading
from collections import defaultdict
from typing import Callable


class EventBus:
    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)

    def subscribe(self, event_name: str, handler: Callable) -> None:
        self._subscribers[event_name].append(handler)

    def publish(self, event_name: str, payload: dict) -> None:
        handlers = self._subscribers.get(event_name, [])
        print(f"[EventBus] публикуем '{event_name}' -> {len(handlers)} подписчик(ов)")
        for handler in handlers:
            # fire-and-forget: издатель не ждёт завершения обработчика
            threading.Thread(target=handler, args=(payload,), daemon=True).start()
