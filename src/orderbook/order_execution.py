from src.orders.order import Order
from src.orderbook.orderbook import OrderBook
from src.orderbook.book_side import BookSide
from src.bookkeeping.custom_types import Side, OrderType
from src.orderbook.orders_queue import OrdersQueue
from src.orders.filled_order import FilledOrder

# TODO
# factory to choose execution based on order type


class OrderExecution:
    """
    Parent class for order execution.
    """

    def __init__(self, order: Order, orderbook: OrderBook):
        self.order = order
        self.orderbook = orderbook

    def execute(self):
        pass

    def _get_side(self) -> BookSide:
        return self.orderbook.get_book_side(self.order.side)

    def _get_opposite_side(self) -> BookSide:
        return self.orderbook.get_opposite_book_side(self.order.side)

    def _fill_from_queue(self, queue: OrdersQueue) -> list[FilledOrder]:

        filled_orders = []

        incoming = self.order
        while not incoming.is_filled and not queue.is_empty:
            resting = queue.next_order_to_execute

            filled = resting.fill(self.order.remaining_quantity)

            incoming.fill(filled)

            if resting.is_filled:
                filled_order = queue.remove_order(resting)
                filled_orders.append(FilledOrder(order=filled_order, filled_qty=filled))

        return filled_orders

    def get_execution_report(self):
        pass


class LimitOrderExecution(OrderExecution):
    """
    Execute limit orders in order book.
    If possible will match order against opposite side orders.. Remaining will be posted in book.
    """

    def __init__(self, order: Order, orderbook):
        super().__init__(order, orderbook)

    def execute(self) -> None:

        self._match()
        self._post_order()

    def _can_match_order(self, opposite_price_levels):

        if self.order.is_filled:
            return False

        if opposite_price_levels.is_empty:
            return False

        if self.order.side == Side.ASK:
            return self.order.limit_price <= opposite_price_levels.best_price

        if self.order.side == Side.BID:
            return self.order.limit_price >= opposite_price_levels.best_price

        raise ValueError(f"order side {self.order.side.name} is not valid")

    def _match(self):

        filled_orders: list[Order] = []

        opposite_side: BookSide = self._get_opposite_side()

        while self._can_match_order(opposite_side):
            top: OrdersQueue = opposite_side.top_level
            filled_orders += self._fill_from_queue(top)

            if top.is_empty:
                opposite_side.delete_level(opposite_side.best_price)

    def _post_order(self) -> None:

        if self.order.is_filled:
            return

        same_side_price_levels = self.orderbook.get_book_side(self.order.side)
        same_side_price_levels.post_order(self.order)


class MarketOrderExecution(OrderExecution):
    """
    Execute market orders in order book.
    If possible will match order against opposite side.
    """

    def __init__(self, order: Order, orderbook):
        super().__init__(order, orderbook)

    def _can_match_order(self, opposite_price_levels):

        if self.order.is_filled:
            return False

        if opposite_price_levels.is_empty:
            return False

        return True

    def execute(self):
        self._match()

    def _match(self) -> None:
        """
        Match order against top-of-book opposite side order if possible. Delete opposite top-of-book if empty.
        """

        filled_orders = []

        opposite_side = self._get_opposite_side()

        while self._can_match_order(opposite_side):
            top: OrdersQueue = opposite_side.top_level
            filled_orders += self._fill_from_queue(top)

            if top.is_empty:
                opposite_side.delete_level(opposite_side.best_price)


map_order_type_to_execution = {
    OrderType.LIMIT: LimitOrderExecution,
    OrderType.MARKET: MarketOrderExecution,
}


def execute_order(order: Order, orderbook: OrderBook) -> None:
    executor = map_order_type_to_execution[order.order_type](order, orderbook)
    executor.execute()
