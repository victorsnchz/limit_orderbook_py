from order import Order, MarketOrder, LimitOrder
from orderbook import OrderBook
from price_levels import PriceLevels
from custom_types import Side
from orders_queue import OrdersQueue
from filled_order import FilledOrder

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

    def get_book_levels(self) -> PriceLevels:
        return self.orderbook.get_levels(self.order.get_side())
    
    def get_opposite_book_level(self) -> PriceLevels:
        return self.orderbook.get_opposite_side_levels(self.order.get_side())

    def match_to_orders_in_queue(self, queue: OrdersQueue) -> list[FilledOrder]:

        filled_orders = []

        while(not self.order.is_filled() and not queue.is_empty()):

            to_match = queue.next_order_to_execute()
            fillable_qty = to_match.remaining_quantity
            to_match.fill_quantity(self.order.remaining_quantity)

            filled_qty = fillable_qty - to_match.remaining_quantity

            self.order.fill_quantity(filled_qty)

            if to_match.is_filled():
                filled_order = queue.remove_order(to_match)
                filled_orders.append(FilledOrder(order = filled_order, filled_qty = filled_qty))

        return filled_orders

    def get_execution_report(self):
        pass

class LimitOrderExecution(OrderExecution):

    """
    Execute limit orders in order book.
    If possible will match order against opposite side orders.. Remaining will be posted in book.
    """

    def __init__(self, order: LimitOrder, orderbook):
        super().__init__(order, orderbook)

    def execute(self) -> None:
        
        self.match_order()
        self.post_order()

    def can_match_order(self, opposite_price_levels):
        
        if self.order.is_filled():
            return False

        if opposite_price_levels.is_empty():
            return False

        if self.order.get_side() == Side.ASK:
            return self.order.limit_price <= opposite_price_levels.get_best_price()
        
        if self.order.get_side() == Side.BID:
            return self.order.limit_price >= opposite_price_levels.get_best_price()
        
        raise ValueError(f'order side {self.order.get_side().name} is not valid')
    
    def match_order(self):

        filled_orders: list[Order] = []

        opposite_price_levels: PriceLevels = self.get_opposite_book_level()

        while self.can_match_order(opposite_price_levels):

            top_of_book: OrdersQueue = opposite_price_levels.get_top_of_book()
            filled_orders += self.match_to_orders_in_queue(top_of_book)

            if top_of_book.is_empty():
                top_price = opposite_price_levels.get_best_price()
                opposite_price_levels.delete_level(top_price)

    def post_order(self) -> None:

        if self.order.is_filled():
            return
        
        order_side = self.order.get_side()
        same_side_price_levels = self.orderbook.get_levels(order_side)
        same_side_price_levels.post_order(self.order)

class MarketOrderExecution(OrderExecution):

    """
    Execute market orders in order book.
    If possible will match order against opposite side.
    """

    def __init__(self, order: MarketOrder, orderbook):
        super().__init__(order, orderbook)

    def can_match_order(self, opposite_price_levels):

        if self.order.is_filled():
            return False

        if opposite_price_levels.is_empty():
            return False
        
        return True
    
    def execute(self):
        self.match_order()

    def match_order(self):
        filled_orders = []

        opposite_price_levels = self.get_opposite_book_level()

        while self.can_match_order(opposite_price_levels):
            top_of_book: OrdersQueue = opposite_price_levels.get_top_of_book()
            filled_orders += self.match_to_orders_in_queue(top_of_book)

            if top_of_book.is_empty():
                top_price = opposite_price_levels.get_best_price()
                opposite_price_levels.delete_level(top_price)
    
