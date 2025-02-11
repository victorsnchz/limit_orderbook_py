import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np


class DepthChart:

    def __init__(self):

        self._fig, self._ax = plt.subplots(figsize=(10,5))
        self._bid_line, = self._ax.step([], [], label = 'bids', color = 'green', where = 'post')
        self._ask_line, = self._ax.step([], [], label = 'asks', color = 'red', where = 'post')
        self._best_bid_line = self._ax.axvline(x = 0, color = 'blue', linestyle = '--', alpha = .5, label = 'best bid')
        self._best_ask_line = self._ax.axvline(x = 0, color = 'orange', linestyle = '--', alpha = .5, label = 'best ask')

        self._ax.set_xlabel('Price')
        self._ax.set_ylabel('Cumulative Volume')
        self._ax.set_title('Order Book Depth Chart')
        self._ax.legend()
        self._ax.grid()

        self._bids = {}
        self._asks = {}

    def update_order_book(self, bids: dict, asks: dict) -> None:
        self._bids = bids
        self._asks = asks

    def update(self, frame):

        if not self._bids or not self._asks:
            return self._bid_line, self._ask_line, self._best_bid_line, self._best_ask_line  # Skip update if empty

        bid_prices = [key for key in self._bids.keys()]
        ask_prices = [key for key in self._asks.keys()]

        cumulative_bid_volumes = np.cumsum([volume for volume in self._bids.values()])
        cumulative_ask_volumes = np.cumsum([volume for volume in self._asks.values()])

        self._bid_line.set_data(bid_prices, cumulative_bid_volumes)
        self._ask_line.set_data(ask_prices, cumulative_ask_volumes)

        self._best_bid_line.set_xdata([bid_prices[0]])
        self._best_ask_line.set_xdata([ask_prices[0]])

        self._ax.set_xlim(.99 * bid_prices[-1], 1.01* ask_prices[-1])
        self._ax.set_ylim(0, max(cumulative_bid_volumes[-1], cumulative_ask_volumes[-1]) * 1.1)

        return self._bid_line, self._ask_line, self._best_bid_line, self._best_ask_line
    
    def animate(self):
        ani = animation.FuncAnimation(self._fig, self.update, frames = 100, interval = 500, blit = False )
        plt.show()

    