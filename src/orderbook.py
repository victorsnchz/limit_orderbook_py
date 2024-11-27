from order import Order
from custom_types import BookSide, OrderExecutionRules, OrderType
from price_levels import PriceLevels

class OrderBook:

    def __init__(self):
        
       #todo 
        self.bids = PriceLevels(BookSide.BID) # make it a tree
        self.asks = PriceLevels(BookSide.ASK) # make it a tree

    def match_order(self, order_in: Order):
        pass

    def post_order(self, order: Order):

        if self.can_match_order(order):
            self.match_order(order)
        
        conditionA = order.execution_rules != OrderExecutionRules.FILL_OR_KILL
        conditionB = order.type == OrderType.LIMIT
        conditionC = order.remaining_quantity > 0

        if conditionA and conditionB and conditionC:
            self.add_order_to_book(order)

    def add_order_to_book(self, order: Order) -> None:
        if order.side == BookSide.BID:
            self.bids.post_order(order)

        elif order.side == BookSide.ASK:
            self.asks.post_order(order)
        
        else:
            raise ValueError(f'order side {order.side} is not valid')

    def cancel_order(self, order: Order):
        if order.side == BookSide.BID:
            self.bids.cancel_order(order)
        
        elif order.side == BookSide.ASK:
            self.asks.cancel_order(order)

        else:
            raise ValueError(f'order side {order.side} is not valid')

    def can_match_order(self, order: Order) -> bool:

        if order.side == BookSide.BID:
            if self.bids.is_empty():
                return False
            return order.price >= self.asks.top_of_book()

        elif order.side == BookSide.ASK:
            if self.asks.is_empty():
                return False
            return order.price <= self.bids.top_of_book()
        
        else:
            raise ValueError(f'order side {order.side} is not valid')



    def modify_order(self, order_id) -> int:
        self.cancel_order(order_id)

        #make new order
        #order_to_post = Order...
        #self.match_order()

    