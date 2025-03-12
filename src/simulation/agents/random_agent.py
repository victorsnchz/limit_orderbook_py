from agent import Agent
from orderbook.orderbook import OrderBook
from orders.order import Order
from bookkeeping import custom_types

import random

class RandomAgent(Agent):

    def __init__(self, orderbook: OrderBook = None, bankroll: float = 0.0):
        super().__init__(orderbook, bankroll)

    def _trade_direction(self) -> custom_types.Side:

        rand = random.random(-1, 2)

        if rand == 0:
            return None

        if rand == -1:
            return custom_types.Side.ASK
        
        if rand == 1:
            return custom_types.Side.BID
        
    def _order_type(self) -> custom_types.OrderType:

        rand = random.random(0, 2)

        if rand == 0:
            return custom_types.OrderType.LIMIT

        return custom_types.OrderType.MARKET
    
    def trade_decision(self) -> Order:
        
        direction = self._trade_direction

        if direction is None:
            return
        
        order_type = self._order_type

