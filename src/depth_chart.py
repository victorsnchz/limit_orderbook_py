import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np

from visuals import Visuals

class DepthChart(Visuals):

    def __init__(self, orderbook = None):
        
        """
        Plot order book depth-chart (cumulative volume vs price).
        """
        
        super().__init__(orderbook)

        self._bid_line, = self._ax.step([], [], label = 'bids', color = 'green', where = 'post')
        self._ask_line, = self._ax.step([], [], label = 'asks', color = 'red', where = 'post')
        self._best_bid_line = self._ax.axvline(x = 0, color = 'blue', linestyle = '--', alpha = .5, label = 'best bid')
        self._best_ask_line = self._ax.axvline(x = 0, color = 'orange', linestyle = '--', alpha = .5, label = 'best ask')

        self._ax.set_xlabel('Price')
        self._ax.set_ylabel('Cumulative Volume')
        self._ax.set_title('Order Book Depth Chart')
        self._ax.legend()
        self._ax.grid()

        self._bids, self._asks = self._orderbook.get_volumes()

    def update_volumes(self) -> None:
        self._bids, self._asks = self._orderbook.get_volumes()

    def update(self, frame):

        self.update_volumes()

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

    