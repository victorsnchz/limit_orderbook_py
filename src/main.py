from order import Order, LimitOrder, MarketOrder, OrderID, OrderParameters
from orderbook import OrderBook
from custom_types import Side, ExecutionRules, OrderType

def main():

    orderbook = OrderBook()
    order1 = LimitOrder(OrderParameters(Side.BID, 90), OrderID(0),
                            limit_price=100, execution_rules = ExecutionRules.GTC)
    
    order2 = LimitOrder(OrderParameters(Side.BID, 10), OrderID(1),
                            limit_price=99, execution_rules = ExecutionRules.GTC)
    
    order3 = LimitOrder(OrderParameters(Side.BID, 100), OrderID(2),
                            limit_price=98, execution_rules = ExecutionRules.GTC)
    
    order_to_match = LimitOrder(OrderParameters(Side.ASK, 100), OrderID(3),
                            limit_price=98, execution_rules = ExecutionRules.GTC)

    orderbook.post_order(order1)
    orderbook.post_order(order2)
    orderbook.post_order(order3)

    filled_orders, posted_order_to_match = orderbook.post_order(order_to_match)
    
    pass

if __name__ == '__main__':
    main()