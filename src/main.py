from order import Order, LimitOrder, MarketOrder, OrderID, OrderParameters
from orderbook import OrderBook
from custom_types import Side, ExecutionRules, OrderType
from price_levels import Bids, Asks
from order_execution import LimitOrderExecution

def main():

    orderbook = OrderBook()
    order_to_post = LimitOrder(OrderParameters(Side.BID, 100), OrderID(0),
                            limit_price=100, execution_rules = ExecutionRules.GTC)
    
    exec = LimitOrderExecution(order_to_post, orderbook)
    exec.post_order()

    order_side = order_to_post.get_side()

    pass

if __name__ == '__main__':
    main()