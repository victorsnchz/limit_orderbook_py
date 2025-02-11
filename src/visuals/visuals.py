import matplotlib.pyplot as plt

import matplotlib.animation as animation
from orderbook.orderbook import OrderBook

class Visuals:

    def __init__(self, orderbook: OrderBook = None):

        """
        Base class for order book visualisations.
        """

        self._orderbook = orderbook if orderbook is not None else OrderBook()

        self._fig, self._ax = plt.subplots(figsize=(10,5))

    def _update_orderbook(self, orderbook: OrderBook) -> None:
        self._orderbook = orderbook

    def _update(self) -> None:
        """
        Update plot.
        """
        pass

    def snapshot(self) -> None:
        pass

    def animate(self) -> None:

        """
        Update plot with live data. 
        Execute order in main thread, call animate from a secondary thread to simulate live order book dynamics.
        """

        ani = animation.FuncAnimation(self._fig, self._update, frames = 100, interval = 500, blit = False )
        plt.show()