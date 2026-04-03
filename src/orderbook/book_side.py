from orderbook.orders_queue import OrdersQueue
from orders.order import Order

from sortedcontainers import SortedDict

class BookSide:

    """
    Store order queues in a tree map.
    O(1) access to top of book (likely most accessed book layer).
    O(nlogn) access to each price level.
    """

    def __init__(self):
        self.price_map = SortedDict()
    
    @property
    def is_empty(self) -> bool:
        """
        Check if level is empty.
        """
        return not bool(self.price_map)

    def post_order(self, order: Order ) -> None:
        """
        Add order to queue at approriate price level. If no level exists create it.
        """

        if order.limit_price not in self.price_map:
            self.price_map[order.limit_price] = OrdersQueue()

        self.price_map[order.limit_price].add_order(order)

    def get_best_price(self) -> int:
        """
        Return top-of-book price.
        """
        pass
    
    def get_top_of_book(self) -> OrdersQueue:
        """
        Return top-of-book queue.
        """
        pass

    def is_level_empty(self, price):
        """
        Check if there exists an order queue at input price.
        """
        return self.price_map[price].is_empty()
    
    def delete_level(self, price: float):
        """
        Delete queue at given price.
        """
        del self.price_map[price]

    def get_states(self) -> dict[float, tuple[float, int]]:
        """
        Return state for all price levels: {price: (volume, #participants)}
        """

        price_map_info = {}

        for price, queue in self.price_map.items():
            total_volume = 0
            participants = set()

            for order in queue.queue.values():
                participants.add(order.user_id)
                total_volume += order.remaining_quantity

            price_map_info[price] = (total_volume, len(participants))

        return price_map_info
    
    def get_top_state(self) -> dict[float, tuple[int, int]]:
        """
        Return state for top-of-book ONLY: {price: (total_volume, #participants)}
        """
        best_price = self.get_best_price()
        top_of_book = self.get_top_queue()

        total_volume = 0
        participants = set()


        for order in top_of_book.queue.values():
            total_volume += order.remaining_quantity
            participants.add(order.user_id)

        return {best_price: (total_volume, len(participants))}

    def get_volumes(self) -> dict[float, int]:
        """
        Return volumes for all price levels: {price: total_volume}
        """

        volumes = SortedDict()

        for price, queue in self.price_map.items():
            volume = 0

            for order in queue.queue.values():
                volume += order.remaining_quantity
        
            volumes[price] = volume
        
        return volumes

class BidSide(BookSide):

    """
    Bids prices sorted from highest-to-lowest. Stored in SortedDicts as asks BUT returns order are inverted.
    """

    def get_best_price(self) -> float:
        return self.price_map.keys()[-1]
    
    def get_top_queue(self) -> OrdersQueue:
        return self.price_map.values()[-1]
    
    def get_volumes(self):
        volumes = super().get_volumes()
        return dict(reversed(volumes.items()))

class AskSide(BookSide):

    def __init__(self):
        super().__init__()

    def get_best_price(self) -> float:
        return self.price_map.keys()[0]
    
    def get_top_queue(self) -> OrdersQueue:
        return self.price_map.values()[0]