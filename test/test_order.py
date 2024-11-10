import unittest
import sys
sys.path.append('../')
sys.path.append('src')

from src.order import Order
from src.custom_types import OrderExecutionRules, OrderType, BookSide

class TestOrder(unittest.TestCase):

    def test_case_init_order(self):

        gtc_order = Order(type = OrderType.LIMIT, execution_rules = OrderExecutionRules.GOOD_TILL_CANCELLED,
                          side = BookSide.BID, initial_quantity=100.0, price = 100.0)
        
        self.assertEqual(gtc_order.remaining_quantity, gtc_order.initial_quantity)

    def test_case_fill_quantity(self):

        gtc_order = Order(type = OrderType.LIMIT, execution_rules = OrderExecutionRules.GOOD_TILL_CANCELLED,
                          side = BookSide.BID, initial_quantity=100.0, price = 100.0)

        to_fill = 50
        gtc_order.fill_quantity(to_fill)
        self.assertEqual(gtc_order.remaining_quantity, gtc_order.initial_quantity - to_fill)
        self.assertEqual(gtc_order.is_filled(), False)
    
    def test_case_full_fill(self):

        gtc_order = Order(type = OrderType.LIMIT, execution_rules = OrderExecutionRules.GOOD_TILL_CANCELLED,
                          side = BookSide.BID, initial_quantity=100.0, price = 100.0)

        to_fill = gtc_order.remaining_quantity
        gtc_order.fill_quantity(to_fill)
        self.assertEqual(gtc_order.remaining_quantity, 0)
        self.assertEqual(gtc_order.is_filled(), True)

    def test_case_overfill(self):
        gtc_order = Order(type = OrderType.LIMIT, execution_rules = OrderExecutionRules.GOOD_TILL_CANCELLED,
                          side = BookSide.BID, initial_quantity=100.0, price = 100.0)

        to_fill = gtc_order.remaining_quantity * 2
        gtc_order.fill_quantity(to_fill )
        self.assertEqual(gtc_order.remaining_quantity, 0)
        self.assertEqual(gtc_order.is_filled(), True)