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
        
        # price levels should be agnostic to its nature
        # implement a tree to enforce this
        # now we use a hash map => necessary to specify side to return top of book or 
        # know how to inspect orders when matching orders
        # using a hashmap creates confusions and complexity in implementation
        
        self.side = side
        self.levels_ordered = list()
        self.levels = dict()

    def is_empty(self) -> bool:
        return not bool(self.levels_ordered)

    def post_order(self, order) -> None:

        if not order.price in self.levels_ordered:
            self.levels[order.price] = OrdersQueue()
            self.levels_ordered.append(order.price)
            self.levels_ordered.sort(reverse = (self.side == BookSide.BID))

        self.levels[order.price].add_order(order)

    # pass price & id ? or order obj
    def cancel_order(self, order: Order) -> None:
        try:
            self.levels[order.price].remove_order(order.id)
            if self.is_level_empty(order.price):
                self._delete_level(order.price)
            
        except:
            print('error cancelling order')

    def _delete_level(self, price: float):
        self.levels_ordered.remove(price)
        del self.levels[price]
    
    def is_level_empty(self, price):
        return self.levels[price].is_empty()

    def top_of_book(self) -> float:
        return self.levels_ordered[0]