"""Thread-safe monotonic source of unique order ids."""

import threading


class OrderIdGenerator:
    """
    Thread-safe monotonic id source.
    """

    def __init__(self, start: int = 0):
        self._counter = start
        self._lock = threading.Lock()

    def next_id(self) -> int:
        """
        Return the next id, strictly increasing and unique across threads.
        """
        with self._lock:
            self._counter += 1
            return self._counter
