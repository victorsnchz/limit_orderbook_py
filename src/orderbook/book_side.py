from src.orderbook.orders_queue import OrdersQueue
from src.orders.order import Order
from src.bookkeeping.custom_types import LevelState
from sortedcontainers import SortedDict
from src.bookkeeping.exceptions import EmptyBookSideError
from abc import ABC, abstractmethod


class BookSide(ABC):
    """
    Store order queues in a tree map.
    O(1) access to top of book (likely most accessed book layer).
    O(nlogn) access to each price level.
    """

    def __init__(self):
        self.levels: SortedDict[int, OrdersQueue] = SortedDict()

    @property
    def is_empty(self) -> bool:
        """
        Check if level is empty.
        """
        return not bool(self.levels)

    def post_order(self, order: Order) -> None:
        """
        Add order to queue at approriate price level. If no level exists create it.
        """

        if order.limit_price not in self.levels:
            self.levels[order.limit_price] = OrdersQueue()

        self.levels[order.limit_price].add_order(order)

    @property
    @abstractmethod
    def best_price(self) -> int:
        """
        Return top-of-book price.
        """
        pass

    @property
    @abstractmethod
    def top_level(self) -> OrdersQueue:
        """
        Return top-of-book queue.
        """
        pass

    def is_level_empty(self, price):
        """
        Check if there exists an order queue at input price.
        """
        return self.levels[price].is_empty

    def delete_level(self, price: int):
        """
        Delete queue at given price.
        """
        del self.levels[price]

    def get_states(self) -> dict[int, LevelState]:
        """
        Return state for all price levels
        """
        states = {}

        for price, queue in self.levels.items():
            total_volume = 0
            order_count = 0
            participants = set()

            for order in queue.queue.values():
                total_volume += order.remaining_quantity
                order_count += 1
                participants.add(order.user_id)

            states[price] = LevelState(
                total_volume=total_volume,
                order_count=order_count,
                participant_count=len(participants),
            )

        return states

    def get_top_state(self) -> dict[int, LevelState]:
        """
        Return state for top-of-book ONLY: {price: (total_volume, #participants)}
        """
        price = self.best_price
        queue = self.top_level

        total_volume = 0
        order_count = 0
        participants = set()

        for order in queue.queue.values():
            total_volume += order.remaining_quantity
            order_count += 1
            participants.add(order.user_id)

        return {
            price: LevelState(
                total_volume=total_volume,
                order_count=order_count,
                participant_count=len(participants),
            )
        }

    def get_volumes(self) -> dict[float, int]:
        """
        Return volumes for all price levels: {price: total_volume}
        """

        volumes = SortedDict()

        for price, queue in self.levels.items():
            volume = 0

            for order in queue.queue.values():
                volume += order.remaining_quantity

            volumes[price] = volume

        return volumes


class BidSide(BookSide):
    """
    Bids prices sorted from highest-to-lowest. Stored in SortedDicts as asks BUT returns order are inverted.
    """

    @property
    def best_price(self) -> int:
        if self.is_empty:
            raise EmptyBookSideError(f"{type(self).__name__} is empty")
        return self.levels.keys()[-1]

    @property
    def top_level(self) -> OrdersQueue:
        return self.levels.values()[-1]

    def get_volumes(self):
        volumes = super().get_volumes()
        return dict(reversed(volumes.items()))


class AskSide(BookSide):
    def __init__(self):
        super().__init__()

    @property
    def best_price(self) -> int:
        if self.is_empty:
            raise EmptyBookSideError(f"{type(self).__name__} is empty")
        return self.levels.keys()[0]

    @property
    def top_level(self) -> OrdersQueue:
        return self.levels.values()[0]
