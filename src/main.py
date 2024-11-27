from order import Order
from orders_queue import OrdersQueue
from price_levels import PriceLevels
from orderbook import OrderBook
from custom_types import BookSide, OrderExecutionRules, OrderType

def main():

    first_in_order = Order(type = OrderType.LIMIT, execution_rules = OrderExecutionRules.GOOD_TILL_CANCELLED,
                          side = BookSide.BID, initial_quantity=100.0, price = 100.0)
    
    orderbook = OrderBook()

    orderbook.post_order(first_in_order)

    print('hello world')

if __name__ == '__main__':
    main()