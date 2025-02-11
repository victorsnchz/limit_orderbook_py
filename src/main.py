import order_generator
import time
import threading

from orderbook import OrderBook
from order_execution import LimitOrderExecution
from depth_chart import DepthChart

def main():

    while(1):

        bids, asks = order_generator.generate()
        orders = bids + asks

        for order in orders:
            exec = LimitOrderExecution(order, orderbook)
            exec.execute()

        depth_chart.update_orderbook(orderbook)
            
        time.sleep(.5)

    
if __name__ == '__main__':
    orderbook = OrderBook()
    depth_chart = DepthChart()

    threading.Thread(target = main, daemon=True).start()
    depth_chart.animate()