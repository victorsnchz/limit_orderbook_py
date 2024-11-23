from order import Order
from orders_queue import OrdersQueue
from price_levels import PriceLevels
from custom_types import BookSide, OrderExecutionRules, OrderType

def main():

    first_in_order = Order(type = OrderType.LIMIT, execution_rules = OrderExecutionRules.GOOD_TILL_CANCELLED,
                          side = BookSide.BID, initial_quantity=100.0, price = 100.0)
    
    last_in_order = Order(type = OrderType.LIMIT, execution_rules = OrderExecutionRules.GOOD_TILL_CANCELLED,
                          side = BookSide.BID, initial_quantity=100.0, price = 100.0)
    
    queue = OrdersQueue()
    levels = PriceLevels(BookSide.BID)

    levels.post_order(first_in_order)


    levels.cancel_order(first_in_order)

    print('hello world')

if __name__ == '__main__':
    main()