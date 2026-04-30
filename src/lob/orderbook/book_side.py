from lob.orderbook.orders_queue import OrdersQueue
from lob.orders.order import Order
from lob.bookkeeping.custom_types import LevelState
from sortedcontainers import SortedDict
from lob.bookkeeping.exceptions import (
    EmptyBookSideError,
    PriceLevelNotFoundError,
    OrderNotFoundError,
)
from abc import ABC, abstractmethod
from typing import KeysView


class BookSide(ABC):
    """
    One side of the book: price levels in a SortedDict, each holding a FIFO queue.
    O(1) at the top, O(log n) at arbitrary levels.
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
        Whether this side holds zero levels.
        """
        return not bool(self._levels)

    def post_order(self, order: Order) -> None:
        """
        Append `order` at its limit price, creating the level if absent.
        """

        if order.limit_price not in self._levels:
            self._levels[order.limit_price] = OrdersQueue()

        self._levels[order.limit_price].add_order(order)

    # TODO: fix with correct indxing logic, raise exceptions
    def get_order(self, price, order_id) -> Order:
        """
        Return the order at `price` with `order_id`. Raises `OrderNotFoundError` if absent.
        """

        try:
            return self.get_level(price).get_order(order_id)
        except KeyError:
            raise OrderNotFoundError(
                f"order {order_id} not found at {price} price level"
            )

    @property
    @abstractmethod
    def best_price(self) -> int:
        """
        Best price on this side. Raises `EmptyBookSideError` if empty.
        """
        pass

    @property
    @abstractmethod
    def top_level(self) -> OrdersQueue:
        """
        Queue at the best price. Raises `EmptyBookSideError` if empty.
        """
        pass

    def is_level_empty(self, price: int):
        """
        Whether the queue at `price` is empty. Raises `PriceLevelNotFoundError` if absent.
        """
        try:
            return self._levels[price].is_empty
        except KeyError:
            raise PriceLevelNotFoundError(
                f"no level at price {price} on {type(self).__name__}"
            )

    def delete_level(self, price: int):
        """
        Drop the level at `price`. Raises `PriceLevelNotFoundError` if absent.
        """
        try:
            del self._levels[price]
        except KeyError:
            raise PriceLevelNotFoundError(
                f"no level at price {price} on {type(self).__name__}"
            )

    def get_states(self) -> dict[int, LevelState]:
        """
        Return `{price: LevelState}` for every level on this side.
        """
        states = {}

        for price, queue in self._levels.items():
            states[price] = queue.get_state()

        return states

    # TODO: untitest
    def get_level(self, price: int) -> OrdersQueue:
        """
        Return the queue at `price`. Raises `PriceLevelNotFoundError` if absent.
        """
        try:
            return self._levels[price]
        except KeyError:
            raise PriceLevelNotFoundError(
                f"no level at price {price} on {type(self).__name__}"
            )

    def get_top_state(self) -> dict[int, LevelState]:
        """
        Return `{best_price: LevelState}`, or `{}` if this side is empty.
        """

        if self.is_empty:
            return {}

        price = self.best_price
        queue = self.top_level

        return {price: queue.get_state()}

    def get_volumes(self) -> dict[float, int]:
        """
        Return `{price: total_volume}` for every level on this side.
        """

        volumes = SortedDict()

        for price, queue in self._levels.items():
            volumes[price] = queue.get_volume()

        return volumes


class BidSide(BookSide):
    """
    Bid side: best price is the highest. Iteration order is reversed vs. ask.
    """

    @property
    def best_price(self) -> int:
        try:
            return self._levels.keys()[-1]
        except IndexError:
            raise EmptyBookSideError(f"{type(self).__name__} is empty")

    @property
    def top_level(self) -> OrdersQueue:
        try:
            return self._levels.values()[-1]
        except IndexError:
            raise EmptyBookSideError("book side is empty cannot get top level")

    def get_volumes(self):
        """
        Same shape as the base, but iterated highest-price-first.
        """
        volumes = super().get_volumes()
        return dict(reversed(volumes.items()))


class AskSide(BookSide):
    """
    Ask side: best price is the lowest.
    """

    def __init__(self):
        super().__init__()

    @property
    def best_price(self) -> int:
        try:
            return self._levels.keys()[0]
        except IndexError:
            raise EmptyBookSideError(f"{type(self).__name__} is empty")

    @property
    def top_level(self) -> OrdersQueue:
        try:
            return self._levels.values()[0]
        except IndexError:
            raise EmptyBookSideError("book side is empty cannot get top level")
