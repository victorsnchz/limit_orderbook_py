import unittest
unittest.TestLoader.sortTestMethodsUsing = None

from src.orders_queue import OrdersQueue
from order import Order
from custom_types import OrderExecutionRules, OrderType, BookSide

class  TestOrdersQueue(unittest.TestCase):

    orders_queue = OrdersQueue()


    def test_case_add(self):

        orders_queue = OrdersQueue()

        new_order = gtc_order = Order(type = OrderType.LIMIT, execution_rules = OrderExecutionRules.GOOD_TILL_CANCELLED,
                          side = BookSide.BID, initial_quantity=100.0, price = 100.0)
        orders_queue.add_order(new_order)

        self.assertEqual(new_order.id in orders_queue.queue, True)

    def test_case_remove(self):

        orders_queue = OrdersQueue()
        new_order = gtc_order = Order(type = OrderType.LIMIT, execution_rules = OrderExecutionRules.GOOD_TILL_CANCELLED,
                          side = BookSide.BID, initial_quantity=100.0, price = 100.0)
        orders_queue.add_order(new_order)
        order_id = list(orders_queue.queue.keys())[0]
        orders_queue.remove_order(order_id)

        self.assertEqual(bool(orders_queue.queue), False)

    def test_case_match_order(self):

        orders_queue = OrdersQueue()

        first_in_order = gtc_order = Order(type = OrderType.LIMIT, execution_rules = OrderExecutionRules.GOOD_TILL_CANCELLED,
                          side = BookSide.BID, initial_quantity=100.0, price = 100.0)
        
        last_in_order = gtc_order = Order(type = OrderType.LIMIT, execution_rules = OrderExecutionRules.GOOD_TILL_CANCELLED,
                          side = BookSide.BID, initial_quantity=100.0, price = 100.0)
        
        orders_queue.add_order(first_in_order)
        orders_queue.add_order(last_in_order)

        order_to_match = Order(type = OrderType.LIMIT, execution_rules = OrderExecutionRules.GOOD_TILL_CANCELLED,
                          side = BookSide.ASK, initial_quantity=150.0, price = 100.0)
        
        filled, order_to_match = orders_queue.match_order(order_to_match)
        
        self.assertEqual(filled[0], (first_in_order))
        self.assertEqual(order_to_match.is_filled(), True)

    def test_case_match_order_larger_than_queue(self):

        orders_queue = OrdersQueue()

        first_in_order = gtc_order = Order(type = OrderType.LIMIT, execution_rules = OrderExecutionRules.GOOD_TILL_CANCELLED,
                          side = BookSide.BID, initial_quantity=100.0, price = 100.0)
        
        last_in_order = gtc_order = Order(type = OrderType.LIMIT, execution_rules = OrderExecutionRules.GOOD_TILL_CANCELLED,
                          side = BookSide.BID, initial_quantity=100.0, price = 100.0)
        
        orders_queue.add_order(first_in_order)
        orders_queue.add_order(last_in_order)

        order_to_match = Order(type = OrderType.LIMIT, execution_rules = OrderExecutionRules.GOOD_TILL_CANCELLED,
                          side = BookSide.ASK, initial_quantity=500.0, price = 100.0)
        
        filled, order_to_match = orders_queue.match_order(order_to_match)
        
        self.assertEqual(filled[0], (first_in_order))
        self.assertEqual(filled[1], (last_in_order))
        self.assertEqual(orders_queue.is_empty(), True)
        self.assertEqual(order_to_match.is_filled(), False)
        self.assertEqual(order_to_match.remaining_quantity, order_to_match.initial_quantity - 200)

