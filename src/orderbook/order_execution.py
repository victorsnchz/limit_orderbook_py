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

    def get_book_side(self) -> BookSide:
        return self.orderbook.get_book_side(self.order.side)

    def get_opposite_book_side(self) -> BookSide:
        return self.orderbook.get_opposite_book_side(self.order.side)

    def match_to_orders_in_queue(self, queue: OrdersQueue) -> list[FilledOrder]:

        filled_orders = []

        while not self.order.is_filled and not queue.is_empty:
            to_match = queue.next_order_to_execute()

            filled = to_match.fill(self.order.remaining_quantity)

            self.order.fill(filled)

            if to_match.is_filled:
                filled_order = queue.remove_order(to_match)
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

        self.match_order()
        self.post_order()

    def can_match_order(self, opposite_price_levels):

        if self.order.is_filled:
            return False

        if opposite_price_levels.is_empty:
            return False

        if self.order.side == Side.ASK:
            return self.order.limit_price <= opposite_price_levels.best_price

        if self.order.side == Side.BID:
            return self.order.limit_price >= opposite_price_levels.best_price

        raise ValueError(f"order side {self.order.side.name} is not valid")

    def match_order(self):

        filled_orders: list[Order] = []

        opposite_price_levels: BookSide = self.get_opposite_book_side()

        while self.can_match_order(opposite_price_levels):
            top_of_book: OrdersQueue = opposite_price_levels.top_level
            filled_orders += self.match_to_orders_in_queue(top_of_book)

            if top_of_book.is_empty():
                top_price = opposite_price_levels.get_best_price()
                opposite_price_levels.delete_level(top_price)

    def post_order(self) -> None:

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

    def can_match_order(self, opposite_price_levels):

        if self.order.is_filled:
            return False

        if opposite_price_levels.is_empty:
            return False

        return True

    def execute(self):
        self.match_order()

    def match_order(self) -> None:
        """
        Match order against top-of-book opposite side order if possible. Delete opposite top-of-book if empty.
        """

        filled_orders = []

        opposite_price_levels = self.get_opposite_book_side()

        while self.can_match_order(opposite_price_levels):
            top_of_book: OrdersQueue = opposite_price_levels.top_level
            filled_orders += self.match_to_orders_in_queue(top_of_book)

            if top_of_book.is_empty:
                top_price = opposite_price_levels.best_price
                opposite_price_levels.delete_level(top_price)


map_order_type_to_execution = {
    OrderType.LIMIT: LimitOrderExecution,
    OrderType.MARKET: MarketOrderExecution,
}


def execute_order(order: Order, orderbook: OrderBook) -> None:
    executor = map_order_type_to_execution[order.order_type](order, orderbook)
    executor.execute()
