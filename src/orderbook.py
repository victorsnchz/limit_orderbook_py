from order import Order, LimitOrder, MarketOrder
from custom_types import OrderType, Side, ExecutionRules
from price_levels import PriceLevels
import execution_schedules


# TODO
# smarter way of routing orders to bookside


class OrderBook:

    def __init__(self):
        
       #todo 
        self.bids = PriceLevels(Side.BID) # make it a tree
        self.asks = PriceLevels(Side.ASK) # make it a tree

    def match_order(self, order: Order):

        filled_orders = []
        
        while(not order.is_filled() and self.can_match_order(order)):

            if order.get_side() == Side.BID:
                filled_orders += self.asks.match_order(order)

            if order.get_side() == Side.ASK:
                filled_orders += self.bids.match_order(order)

        return filled_orders

    def post_order(self, order: LimitOrder | MarketOrder) -> tuple[list[Order], Order]:

        filled_orders = self.match_order(order)
        
        conditionA = isinstance(order, LimitOrder) 
        conditionC = order.remaining_quantity > 0

        if conditionA and not (order.execution_rules == ExecutionRules.IOC.name) and conditionC:
            self.add_order_to_book(order)
        
        return filled_orders, order

    def add_order_to_book(self, order: Order) -> None:
        if order.get_side() == Side.BID:
            self.bids.post_order(order)

        elif order.get_side() == Side.ASK:
            self.asks.post_order(order)
        
        else:
            raise ValueError(f'order side {order.get_side()} is not valid')

    def cancel_order(self, order: Order):
        if order.get_side() == Side.BID:
            self.bids.cancel_order(order)
        
        elif order.get_side() == Side.ASKS:
            self.asks.cancel_order(order)

        else:
            raise ValueError(f'order side {order.get_side()} is not valid')

    def can_match_order(self, order: Order) -> bool:
        # TODO:
        # fix market vs limit orders
        if order.get_side() == Side.BID:
            if self.asks.is_empty():
                return False
            return order.limit_price >= self.asks.get_best_price()

        elif order.get_side() == Side.ASK:
            if self.bids.is_empty():
                return False
            return order.limit_price <= self.bids.get_best_price()
        
        else:
            raise ValueError(f'order side {order.get_side().name} is not valid')

    def modify_order(self, order_id) -> int:
        self.cancel_order(order_id)

        #make new order
        #order_to_post = Order...
        #self.match_order()

    