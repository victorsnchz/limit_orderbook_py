from order import Order

class OrderBook:

    def __init__(self):
        
       #todo 
        self.bids = None # min heap
        self.asks = None # max heap

    def match_order(self, order_in: Order):
        pass

    def cancel_order(self, id):
        pass

    def modify_order(self, order_id) -> int:
        self.cancel_order(order_id)

        #make new order
        #order_to_post = Order...
        #self.match_order()

    