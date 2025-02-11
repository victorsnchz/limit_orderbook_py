from orders_queue import OrdersQueue
from order import LimitOrder

from sortedcontainers import SortedDict

class PriceLevels:

    """
    Store order queues in a tree map.
    O(1) access to top of book (likely most accessed book layer).
    O(nlogn) access to book levels.
    """

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

    def get_price_levels_state(self) -> dict[float, tuple[float, int]]:

        levels_info = {}

        for price_level, queue in self.levels.items():
            total_volume = 0
            participants = set()

            for order in queue.queue.values():
                participants.add(order.id.user_id)
                total_volume += order.remaining_quantity

            levels_info[price_level] = (total_volume, len(participants))

        return levels_info
    
    def get_top_of_book_state(self) -> dict[float, tuple[int, int]]:
        best_price = self.get_best_price()
        top_of_book = self.get_top_of_book()

        total_volume = 0
        participants = set()


        for order in top_of_book.queue.values():
            total_volume += order.remaining_quantity
            participants.add(order.id.user_id)

        return {best_price: (total_volume, len(participants))}

    def get_volumes(self) -> dict[float, int]:

        volumes = SortedDict()

        for price, queue in self.levels.items():
            volume = 0

            for order in queue.queue.values():
                volume += order.remaining_quantity
        
            volumes[price] = volume
        
        return volumes

class Bids(PriceLevels):

    def get_best_price(self) -> float:
        return self.levels.keys()[-1]
    
    def get_top_of_book(self) -> OrdersQueue:
        return self.levels.values()[-1]
    
    def get_volumes(self):
        volumes = super().get_volumes()
        return dict(reversed(volumes.items()))

class Asks(PriceLevels):

    def __init__(self):
        super().__init__()

    def get_best_price(self) -> float:
        return self.levels.keys()[0]
    
    def get_top_of_book(self) -> OrdersQueue:
        return self.levels.values()[0]