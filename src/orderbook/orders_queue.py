import collections
from src.orders.order import Order
from src.bookkeeping.exceptions import EmptyQueueError, OrderNotFoundError
from src.bookkeeping.custom_types import LevelState


class OrdersQueue:
    """
    Store orders in a queue at each price level.
    FIFO.
    Handle adding, removing, getting next order to match against.
    """

    def __init__(self):
        # Python dicts preserve insertion order since 3.7
        # OrderedDict redundant BUT clarifies purpose of this data struct
        self._queue: collections.OrderedDict[int, Order] = collections.OrderedDict()

    # TODO: unittest
    def __contains__(self, order_id: int) -> bool:
        return order_id in self._queue

    def add_order(self, order: Order):
        """
        Add order last in queue if not already in queue.
        """

        if order.order_id not in self._queue:
            self._queue[order.order_id] = order
        else:
            raise RuntimeError(f"order id {order.order_id} already in queue")

    def remove_order(self, order: Order) -> Order:
        """
        Pop order from queue.
        """

        return self._queue.pop(order.order_id)

    # TODO : unittest
    def get_state(self) -> LevelState:
        assert not self.is_empty, "get_state called on empty queue, invariant violation"
        total_volume = 0
        order_count = 0
        participants = set()

        for order in self._queue.values():
            total_volume += order.remaining_quantity
            order_count += 1
            participants.add(order.user_id)

        return LevelState(total_volume, order_count, len(participants))

    # TODO: unittest
    def get_volume(self) -> int:
        volume = 0
        for order in self._queue.values():
            volume += order.remaining_quantity

        return volume

    # TODO: unittest
    def get_order(self, order_id: int) -> Order:
        try:
            return self._queue[order_id]
        except KeyError:
            raise OrderNotFoundError(f"order {order_id} not in queue")

    @property
    def is_empty(self) -> bool:
        """
        Check if queue is empty.
        """
        return not bool(self._queue)

    @property
    def next_order_to_execute(self) -> Order:
        """
        Return next order to be matched against.
        """
        return self._queue[next(iter(self._queue))]

    # TODO : unit tests
    @property
    def tail(self) -> Order:
        """
        Last order in FIFO sequence. Precondition: not empty.
        """

        if self.is_empty:
            raise EmptyQueueError(...)

        return next(reversed(self._queue.values()))
