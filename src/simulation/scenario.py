from orders.order import Order
from orderbook import orderbook

import random

class Scenario:
    def __init__(self, orderbook):

        self._orders = []
        self._agents = []
        pass

    def refresh(self):
        
        """
        Update. Provide agents with data, get their orders.
        """

        # shuffle agents to avoid unfair execution
        random.shuffle(self._agents)

    def get_orders(self) -> list[order]:
        return self._orders
    


    