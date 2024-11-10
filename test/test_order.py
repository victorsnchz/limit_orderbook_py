import unittest
import sys
sys.path.append('../')
sys.path.append('src')

from src.order import Order
from src.custom_types import OrderExecutionRules, OrderType, BookSide

class TestOrder(unittest.TestCase):

    def test_case_1(self):


        
        new_order = Order(type = OrderType.LIMIT, execution_rules = OrderExecutionRules.GOOD_TILL_CANCELLED,
                          side = BookSide.BID, initial_quantity=100.0, price = 100.0)
        
        self.assertEqual(new_order.remaining_quantity, new_order.initial_quantity)

        to_fill = 50
        new_order.fill_quantity(to_fill)
        self.assertEqual(new_order.remaining_quantity, new_order.initial_quantity - to_fill)
        self.assertEqual(new_order.is_filled(), False)

        to_fill = new_order.remaining_quantity
        new_order.fill_quantity(to_fill)
        self.assertEqual(new_order.remaining_quantity, 0)
        self.assertEqual(new_order.is_filled(), True)
