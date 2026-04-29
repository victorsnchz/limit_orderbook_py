import collections
from src.orders.order import Order
from src.bookkeeping.exceptions import (
    EmptyQueueError,
    OrderNotFoundError,
    DuplicateOrderError,
)
from src.bookkeeping.custom_types import LevelState


class OrdersQueue:
    """
    FIFO queue of orders at a single price level, keyed by `order_id`.
    """

    def __init__(self):
        # Python dicts preserve insertion order since 3.7
        # OrderedDict redundant BUT clarifies purpose of this data struct
        self._queue: collections.OrderedDict[int, Order] = collections.OrderedDict()

    # TODO: unittest
    def __contains__(self, order_id: int) -> bool:
        return order_id in self._queue

    def __len__(self) -> int:
        return len(self._queue)

    def add_order(self, order: Order):
        """
        Append `order` to the tail. Raises `DuplicateOrderError` if its id is already queued.
        """

        if order.order_id not in self:
            self._queue[order.order_id] = order
        else:
            raise DuplicateOrderError(f"order id {order.order_id} already in queue")

    def remove_order(self, order_id: int) -> Order:
        """
        Pop and return the order with `order_id`. Asserts non-empty and present.
        """
        assert not self.is_empty, "remove_order raised on empty queue"
        assert order_id in self, "removing order not in queue"
        return self._queue.pop(order_id)

    def get_state(self) -> LevelState:
        """
        Aggregate the queue into total volume, order count, and unique participant count.
        Asserts non-empty.
        """
        assert not self.is_empty, "get_state called on empty queue, invariant violation"
        total_volume = 0
        order_count = 0
        participants = set()

        for order in self._queue.values():
            total_volume += order.remaining_quantity
            order_count += 1
            participants.add(order.user_id)

        return LevelState(total_volume, order_count, len(participants))

    def get_volume(self) -> int:
        """
        Sum of `remaining_quantity` across the queue. Returns 0 if empty.
        """
        volume = 0
        for order in self._queue.values():
            volume += order.remaining_quantity

        return volume

    # TODO: unittest
    def get_order(self, order_id: int) -> Order:
        """
        Return the order with `order_id`. Raises `OrderNotFoundError` if absent.
        """
        try:
            return self._queue[order_id]
        except KeyError:
            raise OrderNotFoundError(f"order {order_id} not in queue")

    @property
    def is_empty(self) -> bool:
        """
        Whether the queue holds zero orders.
        """
        return not bool(self._queue)

    @property
    def next_order_to_execute(self) -> Order:
        """
        Head of the FIFO. Raises `EmptyQueueError` if empty.
        """
        if self.is_empty:
            raise EmptyQueueError("queue is empty no order to execute")
        return self._queue[next(iter(self._queue))]

    @property
    def tail(self) -> Order:
        """
        Tail of the FIFO. Raises `EmptyQueueError` if empty.
        """

        if self.is_empty:
            raise EmptyQueueError("queue is empty no order to execute")

        return next(reversed(self._queue.values()))
