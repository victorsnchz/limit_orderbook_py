from order import Order
from orders_queue import OrdersQueue
from custom_types import BookSide, OrderExecutionRules, OrderType

def main():

    first_in_order = Order(type = OrderType.LIMIT, execution_rules = OrderExecutionRules.GOOD_TILL_CANCELLED,
                          side = BookSide.BID, initial_quantity=100.0, price = 100.0)
    
    last_in_order = Order(type = OrderType.LIMIT, execution_rules = OrderExecutionRules.GOOD_TILL_CANCELLED,
                          side = BookSide.BID, initial_quantity=100.0, price = 100.0)
    
    queue = OrdersQueue()

    queue.add_order(first_in_order)
    queue.add_order(last_in_order)

    order_to_match = Order(type = OrderType.LIMIT, execution_rules = OrderExecutionRules.FILL_OR_KILL,
                          side = BookSide.ASK, initial_quantity=150.0, price = 100.0)

    filled = queue.match_order(order_to_match)

    print('hello world')

if __name__ == '__main__':
    main()