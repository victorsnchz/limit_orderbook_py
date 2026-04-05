import threading


class OrderIdGenerator:
    def __init__(self, start: int = 0):
        self._counter = start
        self._lock = threading.lock()

    def next_id(self) -> int:
        with self._lock:
            self._counter += 1
            return self._counter
