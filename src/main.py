from order import Order
from orders_queue import OrdersQueue
from price_levels import PriceLevels
from orderbook import OrderBook
from custom_types import BookSide, OrderExecutionRules, OrderType

def main():

    orderbook = OrderBook()
    order1 = Order(type = OrderType.LIMIT, execution_rules = OrderExecutionRules.GOOD_TILL_CANCELLED,
                        side = BookSide.BID, initial_quantity=10, price = 100.0)
    
    order2 = Order(type = OrderType.LIMIT, execution_rules = OrderExecutionRules.GOOD_TILL_CANCELLED,
                        side = BookSide.BID, initial_quantity=20, price = 99.0)
    
    order3 = Order(type = OrderType.LIMIT, execution_rules = OrderExecutionRules.GOOD_TILL_CANCELLED,
                        side = BookSide.BID, initial_quantity=75, price = 98.0)
    
    order_to_match = Order(type = OrderType.LIMIT, execution_rules = OrderExecutionRules.GOOD_TILL_CANCELLED,
                        side = BookSide.ASK, initial_quantity=100.0, price = 98.0)
    

    orderbook.post_order(order1)
    orderbook.post_order(order2)
    orderbook.post_order(order3)

    filled_orders, posted_order_to_match = orderbook.post_order(order_to_match)

    print('hello world')

if __name__ == '__main__':
    main()