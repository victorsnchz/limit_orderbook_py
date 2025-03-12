import simulation.orders_generator as orders_generator
import time
import threading
import random

from bookkeeping.custom_types import OrderType
from orderbook.orderbook import OrderBook
from orderbook.order_execution import map_order_type_to_execution
from visuals.depth_chart import DepthChart
from simulation.orders_generator import map_order_type_to_generator, OrdersGenerator

def main():

    top_bid, top_ask = 100., 100.1

    counter = 500

    while(counter >= 0):

        mid = .5 * (top_bid + top_ask)
        bid_count = random.randint(20, 200)
        ask_count = random.randint(20, 200)
        bid_volume = 1000
        ask_volume = 1000
        limit_price = mid

        if counter > 450:
            order_type = OrderType.LIMIT
        else:
            random_binary = random.randint(0, 1)
            order_type = OrderType.LIMIT if random_binary else OrderType.MARKET
        

        orders_generator: OrdersGenerator = map_order_type_to_generator[order_type]()
        
        bids, asks = orders_generator.generate_orders(bid_count=bid_count, 
                                                      ask_count=ask_count,
                                                      bid_volume = bid_volume,
                                                      ask_volume=ask_volume,
                                                      best_bid = top_bid,
                                                      best_ask = top_ask,
                                                      bid_vol = .2,
                                                      ask_vol = .2
                                                      )


        orders = bids | asks

        for order in orders:
            exec = map_order_type_to_execution[order_type](order, orderbook)
            exec.execute()

        depth_chart._update_orderbook(orderbook)
        
        counter -= 1
        time.sleep(.5)

    
if __name__ == '__main__':

    orderbook = OrderBook()
    depth_chart = DepthChart()

    threading.Thread(target = main, daemon=True).start()
    depth_chart.animate()