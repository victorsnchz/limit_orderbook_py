from src.orders.order import Order
from src.orderbook.orderbook import OrderBook
from src.orderbook.book_side import BookSide
from src.bookkeeping.custom_types import Side, OrderType, FilledPayload

from abc import ABC, abstractmethod


class OrderExecution(ABC):
    """
    Parent class for order execution.
    """

    def __init__(self, order: Order, orderbook: OrderBook):
        self.order: Order = order
        self.orderbook: OrderBook = orderbook
        self.filled_orders = []

    @abstractmethod
    def execute(self):
        pass

    def _get_side(self) -> BookSide:
        return self.orderbook.get_book_side(self.order.side)

    def _get_opposite_side(self) -> BookSide:
        return self.orderbook.get_opposite_book_side(self.order.side)

    @abstractmethod
    def _can_match_order(self) -> None:
        pass

    def _match(self) -> list[FilledPayload]:

        opposite_side: BookSide = self._get_opposite_side()

        while self._can_match_order(opposite_side):
            self.filled_orders += self.orderbook.fill_top(self.order)

    def _build_execution_report(self):
        aggressor = self.order.snapshot()
        fills = self.filled_orders

        posted = (
            not (aggressor.order_type == OrderType.MARKET)
            and aggressor.remaining_quantity > 0
        )


class LimitOrderExecution(OrderExecution):
    """
    Execute limit orders in order book.
    If possible will match order against opposite side orders.. Remaining will be posted in book.
    """

    def __init__(self, order: Order, orderbook):
        super().__init__(order, orderbook)

    def execute(self) -> None:

        self._match()
        if not self.order.is_filled:
            self.orderbook.post_order(self.order)

    def _can_match_order(self, opposite_price_levels: BookSide) -> bool:

        if self.order.is_filled:
            return False

        if opposite_price_levels.is_empty:
            return False

        if self.order.side == Side.ASK:
            return self.order.limit_price <= opposite_price_levels.best_price

        if self.order.side == Side.BID:
            return self.order.limit_price >= opposite_price_levels.best_price

        raise ValueError(f"order side {self.order.side.name} is not valid")


class MarketOrderExecution(OrderExecution):
    """
    Execute market orders in order book.
    If possible will match order against opposite side.
    """

    def __init__(self, order: Order, orderbook):
        super().__init__(order, orderbook)

    def _can_match_order(self, opposite_price_levels: BookSide) -> bool:

        if self.order.is_filled:
            return False

        if opposite_price_levels.is_empty:
            return False

        return True

    def execute(self):
        self._match()


map_order_type_to_execution = {
    OrderType.LIMIT: LimitOrderExecution,
    OrderType.MARKET: MarketOrderExecution,
}


def execute_order(order: Order, orderbook: OrderBook) -> None:
    executor = map_order_type_to_execution[order.order_type](order, orderbook)
    executor.execute()
