from order import Order, LimitOrder, MarketOrder, OrderID, OrderParameters
from orderbook import OrderBook
from custom_types import Side, ExecutionRules, OrderType
from price_levels import Bids, Asks
from order_execution import LimitOrderExecution
from saver import Saver
from visuals import Visuals
import order_generator

def main():

    orderbook = OrderBook()

    bid1 = LimitOrder(OrderParameters(Side.BID, 100), OrderID(0),
                            limit_price=100, execution_rules = ExecutionRules.GTC)
    bid2 = LimitOrder(OrderParameters(Side.BID, 200), OrderID(1),
                            limit_price=100, execution_rules = ExecutionRules.GTC)
    bid3 = LimitOrder(OrderParameters(Side.BID, 100), OrderID(0),
                            limit_price=105, execution_rules = ExecutionRules.GTC)

    ask1 = LimitOrder(OrderParameters(Side.ASK, 100), OrderID(2),
                            limit_price=110, execution_rules = ExecutionRules.GTC)
    ask2 = LimitOrder(OrderParameters(Side.ASK, 100), OrderID(3),
                            limit_price=120, execution_rules = ExecutionRules.GTC)

    bids, asks = order_generator.generate()
    orders = bids + asks

    for order in orders:
        exec = LimitOrderExecution(order, orderbook)
        exec.execute()


    bid_vol, ask_vol = orderbook.get_volumes()


    visuals = Visuals()

    visuals.depth_chart(bid_vol, ask_vol)

if __name__ == '__main__':
    main()