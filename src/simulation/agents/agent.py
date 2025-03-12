from orderbook.orderbook import OrderBook
from orders.order import Order

class Agent:
    def __init__(self, orderbook: OrderBook = None, bankroll: float = 0.0):

        """
        Template class for Agents which can interact with orderbook.
        """

        self._orderbook = orderbook if orderbook is not None else OrderBook

        self._best_bid, self._best_ask = self._orderbook

    def trade_decision(self) -> Order | None:
        pass

    def _update_orderbook(self, orderbook: OrderBook):
        self._orderbook = orderbook

    
