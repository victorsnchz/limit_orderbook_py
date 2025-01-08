import collections
from order import Order

class OrdersQueue:

    def __init__(self):
        # Python dicts preserve insertion order since 3.7 
        # OrderedDict redundqnt BUT clarifies purpose of this data struct
        self.queue: collections.OrderedDict[int, Order] = collections.OrderedDict()
    
    def add_order(self, order: Order):
        if order.id not in self.queue:
            self.queue[order.get_id()] = order
        else:
            raise RuntimeError(f'order id {order.get_id()} already in queue')

    def remove_order(self, order: Order) -> Order:
        return self.queue.pop(order.get_id())

    def is_empty(self):
        return not bool(self.queue)

    def next_order_to_execute(self) -> Order:
        return self.queue[next(iter(self.queue))]