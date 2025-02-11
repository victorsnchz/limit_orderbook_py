import collections
from order import Order

class OrdersQueue:

    """
    Store orders in a queue at each price level.
    FIFO.
    Handle adding, removing, getting next order to match against.
    """

    def __init__(self):
        # Python dicts preserve insertion order since 3.7 
        # OrderedDict redundqnt BUT clarifies purpose of this data struct
        self.queue: collections.OrderedDict[int, Order] = collections.OrderedDict()
    
    def add_order(self, order: Order):

        """
        Add order last in queue if not already in queue.
        """

        if order.id not in self.queue:
            self.queue[order.get_id()] = order
        else:
            raise RuntimeError(f'order id {order.get_id()} already in queue')

    def remove_order(self, order: Order) -> Order:
        """
        Pop order from queue.
        """

        return self.queue.pop(order.get_id())

    def is_empty(self) -> bool:
        """
        Check if queue is empty.
        """
        return not bool(self.queue)

    def next_order_to_execute(self) -> Order:
        """
        Return next order to be matched against.
        """
        return self.queue[next(iter(self.queue))]