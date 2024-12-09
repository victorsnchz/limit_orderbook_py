import unittest

from src.orders_queue import OrdersQueue
from order import Order, LimitOrder, MarketOrder, OrderID, OrderParameters
from custom_types import ExecutionRules, OrderType, Side

class  TestOrdersQueue(unittest.TestCase):

    def test_case_add(self):

        orders_queue = OrdersQueue()

        order = LimitOrder(OrderParameters(Side.BID, 100), OrderID(0),
                               limit_price=100, execution_rules = ExecutionRules.GTC)
        orders_queue.add_order(order)

        self.assertEqual(order.id in orders_queue.queue, True)

    def test_case_remove(self):

        orders_queue = OrdersQueue()
        order = LimitOrder(OrderParameters(Side.BID, 100), OrderID(0),
                               limit_price=100, execution_rules = ExecutionRules.GTC)
        
        orders_queue.add_order(order)
        order_id = list(orders_queue.queue.keys())[0]
        orders_queue.remove_order(order_id)

        self.assertEqual(bool(orders_queue.queue), False)

    def test_case_match_order(self):

        orders_queue = OrdersQueue()

        first_in_order = LimitOrder(OrderParameters(Side.BID, 100), OrderID(0),
                               limit_price=100, execution_rules = ExecutionRules.GTC)
        
        last_in_order = LimitOrder(OrderParameters(Side.BID, 100), OrderID(1),
                               limit_price=100, execution_rules = ExecutionRules.GTC)
        
        orders_queue.add_order(first_in_order)
        orders_queue.add_order(last_in_order)

        order_to_match = LimitOrder(OrderParameters(Side.ASK, 100), OrderID(2),
                               limit_price=99, execution_rules = ExecutionRules.GTC)
        
        filled = orders_queue.match_order(order_to_match)
        
        self.assertEqual(filled[0], (first_in_order))
        self.assertEqual(order_to_match.is_filled(), True)

    def test_case_match_order_larger_than_queue(self):

        orders_queue = OrdersQueue()

        first_in_order = LimitOrder(OrderParameters(Side.BID, 100), OrderID(0),
                               limit_price=100, execution_rules = ExecutionRules.GTC)
        
        last_in_order = LimitOrder(OrderParameters(Side.BID, 100), OrderID(1),
                               limit_price=100, execution_rules = ExecutionRules.GTC)
        
        orders_queue.add_order(first_in_order)
        orders_queue.add_order(last_in_order)

        order_to_match = LimitOrder(OrderParameters(Side.ASK, 500), OrderID(2),
                               limit_price=99, execution_rules = ExecutionRules.GTC)
        
        filled = orders_queue.match_order(order_to_match)
        
        self.assertEqual(filled[0], (first_in_order))
        self.assertEqual(filled[1], (last_in_order))
        self.assertEqual(orders_queue.is_empty(), True)
        self.assertEqual(order_to_match.is_filled(), False)

        filled = first_in_order.get_initial_quantity() + last_in_order.get_initial_quantity()
        self.assertEqual(order_to_match.remaining_quantity, order_to_match.get_initial_quantity() - filled)

