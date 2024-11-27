import unittest
from orderbook import OrderBook
from order import Order
from custom_types import OrderType, OrderExecutionRules, BookSide

# blend of unit-testing and integration testing

class TestOrderbook(unittest.TestCase):

    def test_case_match_order(self):

        orderbook = OrderBook()
        new_order = Order(type = OrderType.LIMIT, execution_rules = OrderExecutionRules.GOOD_TILL_CANCELLED,
                          side = BookSide.BID, initial_quantity=100.0, price = 100.0)
        
        
        self.assertEqual(orderbook.can_match_order(new_order), False)

    def test_case_post_order(self):

        new_order = Order(type = OrderType.LIMIT, execution_rules = OrderExecutionRules.GOOD_TILL_CANCELLED,
                          side = BookSide.BID, initial_quantity=100.0, price = 100.0)