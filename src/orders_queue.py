import collections
from order import Order

class OrdersQueue:

    def __init__(self):
        self.queue = collections.OrderedDict()
    
    def add_order(self, order: Order):
        # TODO
        # verif if order not already in queue
        self.queue[order.id] = order

    def remove_order(self, order_id: str) -> Order:
        self.queue.pop(order_id)

    def is_empty(self):
        return not bool(self.queue)

    def match_order(self, order_to_match: Order) -> list[Order]:

        filled_orders = []

        while( (not order_to_match.is_filled()) and (not self.is_empty())):
            
            waiting_order_id = next(iter(self.queue))
            waiting_order_quantity_to_fill = self.queue[waiting_order_id].remaining_quantity
            self.queue[waiting_order_id].fill_quantity(order_to_match.remaining_quantity)
            order_to_match.fill_quantity(waiting_order_quantity_to_fill - self.queue[waiting_order_id].remaining_quantity)

            if self.queue[waiting_order_id].is_filled():
                filled_orders.append(self.queue.pop(waiting_order_id))
            
        # order_to_match field 'remaining qty' is mutable, no need to return a new instance
        # only return a list of filled orders to pass up info
        return filled_orders