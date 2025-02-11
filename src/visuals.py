import matplotlib.pyplot as plt
import numpy as np

class Visuals:

    def __init__(self, data_directory: str = None):
        self._data_directory = data_directory

    def depth_chart(self, bids: dict[float, int], asks: dict[float, int]) -> None:

        bid_volumes = [volume for volume in bids.values()]
        ask_volumes = [volume for volume in asks.values()]

        cumulative_bid_volumes = np.cumsum(bid_volumes)
        cumulative_ask_volumes = np.cumsum(ask_volumes)

        bid_prices = [price for price in bids.keys()]
        ask_prices = [price for price in asks.keys()]

        #plt.figure(figsize=(10, 5))
        plt.step(bid_prices, cumulative_bid_volumes, label = 'bids', color = 'green', where = 'post')
        plt.step(ask_prices, cumulative_ask_volumes, label = 'asks', color = 'red', where = 'post')
        
        plt.axvline(x=bid_prices[0], color='blue', linestyle='--', alpha=0.5, label='best bid')
        plt.axvline(x=ask_prices[0], color='orange', linestyle='--', alpha=0.5, label='best ask')

        plt.xlabel('Price')
        plt.ylabel('Cumulative Volume')
        plt.title('Order Book Depth Chart')
        plt.legend()
        plt.grid()
        plt.show()
        


    def ladder_view(self):
        pass
