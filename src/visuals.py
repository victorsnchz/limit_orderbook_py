import matplotlib.pyplot as plt
import numpy as np

import matplotlib.animation as animation
from orderbook import OrderBook

class Visuals:

    def __init__(self, orderbook: OrderBook = None):

        """
        Base class for order book visualisations.
        """

        self._orderbook = orderbook if orderbook is not None else OrderBook()

        self._fig, self._ax = plt.subplots(figsize=(10,5))

    def update_orderbook(self, orderbook: OrderBook) -> None:
        self._orderbook = orderbook

    def update(self) -> None:
        pass

    def snapshot(self) -> None:
        pass

    def animate(self) -> None:
        ani = animation.FuncAnimation(self._fig, self.update, frames = 100, interval = 500, blit = False )
        plt.show()