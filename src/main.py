import simulation.orders_generator as orders_generator
import time
import threading
import random
from itertools import zip_longest

from bookkeeping.custom_types import OrderType
from orderbook.orderbook import OrderBook
from orderbook.order_execution import map_order_type_to_execution
from visuals.depth_chart import DepthChart
from simulation.orders_generator import map_order_type_to_generator, OrdersGenerator

def main():

    orderbook = OrderBook()
    total_volume = 0

    top_bid, top_ask = 100., 100.1
    mid = .5 * (top_bid + top_ask)

    counter = 5000

    while(counter >= 0):

        bid_count = random.randint(20, 200)
        ask_count = random.randint(20, 200)
        bid_volume = random.randint(1500, 7500)
        ask_volume = random.randint(1500, 7500)



        if counter > 4750 or total_volume < 10**7:
            order_type = OrderType.LIMIT
        else:
            random_binary = random.randint(0, 1)

            if random_binary:
                order_type = OrderType.LIMIT 
            else: 
                order_type = OrderType.MARKET
                bid_volume //= 2
                ask_volume //= 2
        

        orders_generator: OrdersGenerator = map_order_type_to_generator[order_type]()

        bids, asks = orders_generator.generate_orders(bid_count=bid_count, 
                                                      ask_count=ask_count,
                                                      bid_volume = bid_volume,
                                                      ask_volume=ask_volume,
                                                      best_bid = top_bid,
                                                      best_ask = top_ask,
                                                      bid_vol = 2,
                                                      ask_vol = 2
                                                      )


        orders = bids | asks

        for order in orders:
            exec = map_order_type_to_execution[order_type](order, orderbook)
            exec.execute()

        depth_chart._update_orderbook(orderbook)
        
        counter -= 1
        time.sleep(.05)
        top_bid, top_ask, _= orderbook.get_bid_ask_mid()

        total_volume = 0
        bid_side, ask_side = orderbook.get_volumes()
        for b_volume, a_volume in zip_longest(bid_side.values(), ask_side.values(),
                                              fillvalue=0):
            total_volume += b_volume + a_volume

    
if __name__ == '__main__':

    depth_chart = DepthChart()

    threading.Thread(target = main, daemon=True).start()
    depth_chart.animate()