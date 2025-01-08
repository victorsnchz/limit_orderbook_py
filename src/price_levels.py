from orders_queue import OrdersQueue
from custom_types import Side
from order import Order, LimitOrder

from sortedcontainers import SortedDict

# TODO
# compare perf hashmap vs tree for both many and few elements
# use rebalancing tree: more elegant, fast access to sorted layers, very fast access to unkown top of book layers
# for now implement as a hashmap O(1) access to known price (assuming not too many prices so no collision)
# but hard to keep track of which layers exist or not so access time will infine be slower


class PriceLevels:

    def __init__(self):
        self.levels = SortedDict()
    
    def is_empty(self) -> bool:
        return not bool(self.levels)

    def post_order(self, order: LimitOrder ) -> None:

        if not order.limit_price in self.levels:
            self.levels[order.limit_price] = OrdersQueue()

        self.levels[order.limit_price].add_order(order)

    def get_best_price(self) -> float:
        pass
    
    def get_top_of_book(self) -> OrdersQueue:
        pass

    def is_level_empty(self, price):
        return self.levels[price].is_empty()
    
    def delete_level(self, price: float):
        del self.levels[price]
    
class Bids(PriceLevels):

    def __init__(self):
        super().__init__()

    def get_best_price(self) -> float:
        return self.levels.keys()[-1]
    
    def get_top_of_book(self) -> OrdersQueue:
        return self.levels.values()[-1]

class Asks(PriceLevels):

    def __init__(self):
        super().__init__()

    def get_best_price(self) -> float:
        return self.levels.keys()[0]
    
    def get_top_of_book(self) -> OrdersQueue:
        return self.levels.values()[0]