from orders_queue import OrdersQueue
from heaps import MinHeap, MaxHeap

class Levels:

    def __init__(self):
        pass

    def post_order(self):
        pass

    def cancel_order(self):
        pass

class Bids(Levels):

    def __init__(self):
        self.levels = MinHeap()
        

class Asks(Levels):

    def __init__(self):
        self.levels = MaxHeap()