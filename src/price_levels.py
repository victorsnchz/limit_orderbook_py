from orders_queue import OrdersQueue
from custom_types import BookSide
from order import Order

# TODO
# compare perf hashmap vs tree for both many and few elements
# use rebalancing tree: more elegant, fast access to sorted layers, very fast access to unkown top of book layers
# for now implement as a hashmap O(1) access to known price (assuming not too many prices so no collision)
# but hard to keep track of which layers exist or not so access time will infine be slower


class PriceLevels:

    def __init__(self, side: BookSide):
        
        self.side = side
        self.levels = dict()

    def post_order(self, order) -> None:
        if not self.can_match(order.price):
            self.levels[order.price] = OrdersQueue()
        self.levels[order.price].add_order(order)
        
    def can_match(self, price: float) -> bool:
        return price in self.levels

    # pass price & id ? or order obj
    def cancel_order(self, order: Order) -> None:
        try:
            self.levels[order.price].remove_order(order.id)
            if self.is_level_empty(order.price):
                self._delete_level(order.price)
            
        except:
            print('error cancelling order')

    def _delete_level(self, price: float):
        del self.levels[price]
    
    def is_level_empty(self, price):
        return self.levels[price].is_empty()

    def top_of_book(self) -> float:
        if self.side.value == BookSide.BID:
            return max(self.levels.keys())
        return min(self.levels.keys())