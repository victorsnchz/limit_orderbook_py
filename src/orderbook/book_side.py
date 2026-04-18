from src.orderbook.orders_queue import OrdersQueue
from src.orders.order import Order
from src.bookkeeping.custom_types import LevelState
from sortedcontainers import SortedDict
from src.bookkeeping.exceptions import (
    EmptyBookSideError,
    PriceLevelNotFoundError,
    OrderNotFoundError,
)
from abc import ABC, abstractmethod
from typing import KeysView


class BookSide(ABC):
    """
    Store order queues in a tree map.
    O(1) access to top of book (likely most accessed book layer).
    O(nlogn) access to each price level.
    """

    def __init__(self):
        self._levels: SortedDict[int, OrdersQueue] = SortedDict()
        # TODO: shift index responsibility to BookSide
        # self._order_index: dict[int, int] = {}

    @property
    def prices(self) -> KeysView[int]:
        return self._levels.keys()

    @property
    def is_empty(self) -> bool:
        """
        Check if level is empty.
        """
        return not bool(self._levels)

    def post_order(self, order: Order) -> None:
        """
        Add order to queue at approriate price level. If no level exists create it.
        """

        if order.limit_price not in self._levels:
            self._levels[order.limit_price] = OrdersQueue()

        self._levels[order.limit_price].add_order(order)

    # TODO: fix with correct indxing logic, raise exceptions
    def get_order(self, price, order_id) -> Order:

        try:
            return self.get_level(price).get_order(order_id)
        except:
            raise OrderNotFoundError(
                f"order {order_id} not found at {price} price level"
            )

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

    def is_level_empty(self, price: int):
        """
        Check if there exists an order queue at input price.
        """
        return self._levels[price].is_empty

    def delete_level(self, price: int):
        """
        Delete queue at given price.
        """
        del self._levels[price]

    def get_states(self) -> dict[int, LevelState]:
        """
        Return state for all price levels
        """
        states = {}

        for price, queue in self._levels.items():
            states[price] = queue.get_state()

        return states

    # TODO: untitest
    def get_level(self, price: int) -> OrdersQueue:
        try:
            return self._levels[price]
        except KeyError:
            raise PriceLevelNotFoundError(
                f"no level at price {price} on {type(self).__name__}"
            )

    def get_top_state(self) -> dict[int, LevelState]:
        """
        Return state for top-of-book ONLY: {price: (total_volume, #participants)}
        """

        if self.is_empty:
            return {}

        price = self.best_price
        queue = self.top_level

        return {price: queue.get_state()}

    def get_volumes(self) -> dict[float, int]:
        """
        Return volumes for all price levels: {price: total_volume}
        """

        volumes = SortedDict()

        for price, queue in self._levels.items():
            volumes[price] = queue.get_volume()

        return volumes


class BidSide(BookSide):
    """
    Bids prices sorted from highest-to-lowest. Stored in SortedDicts as asks BUT returns order are inverted.
    """

    @property
    def best_price(self) -> int:
        if self.is_empty:
            raise EmptyBookSideError(f"{type(self).__name__} is empty")
        return self._levels.keys()[-1]

    @property
    def top_level(self) -> OrdersQueue:
        return self._levels.values()[-1]

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
        return self._levels.keys()[0]

    @property
    def top_level(self) -> OrdersQueue:
        return self._levels.values()[0]
