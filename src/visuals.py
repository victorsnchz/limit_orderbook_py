from orderbook import OrderBook
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

class Visuals:
    def __init__(self, orderbook: OrderBook):
        self.orderbook: OrderBook = orderbook
    
    def plot_top_of_book(self, orderbook: OrderBook):

        bid, ask, mid = orderbook.get_bid_ask_mid()

        

        pass 

    def animate(self, i):
        pass

    ani = FuncAnimation(plt.gcf(), animate, interval = 1000)