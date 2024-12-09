import unittest

from price_levels import PriceLevels
from order import Order, LimitOrder, MarketOrder, OrderID, OrderParameters
from custom_types import OrderType, ExecutionRules, Side




class TestPriceLevels(unittest.TestCase):
    
    def test_case_empty(self):

        price_levels = PriceLevels(Side.ASK)

        self.assertEqual(price_levels.is_empty(), True)

    def test_case_add_order(self):

        price_levels = PriceLevels(Side.ASK)
        order = LimitOrder(OrderParameters(Side.BID, 100), OrderID(0),
                            limit_price=100, execution_rules = ExecutionRules.GTC)
        price_levels.post_order(order)

        self.assertEqual(order.id in price_levels.levels[order.price].queue, True)

    def test_case_add_order(self):

        price_levels = PriceLevels(Side.ASK)
        order = LimitOrder(OrderParameters(Side.BID, 100), OrderID(0),
                            limit_price=100, execution_rules = ExecutionRules.GTC)
        
        price_levels.post_order(order)

        self.assertEqual(order.id in price_levels.levels[order.limit_price].queue, True)

    def test_case_best_price(self):

        price_levels = PriceLevels(Side.BID)

        order = LimitOrder(OrderParameters(Side.BID, 100), OrderID(0),
                               limit_price=100, execution_rules = ExecutionRules.GTC)
        order2 = LimitOrder(OrderParameters(Side.BID, 100), OrderID(1),
                               limit_price=101, execution_rules = ExecutionRules.GTC)
        
        price_levels.post_order(order)
        price_levels.post_order(order2)

        self.assertEqual(price_levels.get_best_price(), order2.limit_price)

    def test_case_cancel_order(self):

        order = LimitOrder(OrderParameters(Side.BID, 100), OrderID(0),
                               limit_price=100, execution_rules = ExecutionRules.GTC)
        order2 = LimitOrder(OrderParameters(Side.BID, 100), OrderID(1),
                               limit_price=99, execution_rules = ExecutionRules.GTC)

        order3 = LimitOrder(OrderParameters(Side.BID, 100), OrderID(2),
                               limit_price=98, execution_rules = ExecutionRules.GTC)
        
        price_levels = PriceLevels(Side.BID)
        price_levels.post_order(order)
        price_levels.post_order(order2)
        price_levels.post_order(order3)

        self.assertEqual(order3.id in price_levels.levels[order3.limit_price].queue, True)
        
        price_levels.cancel_order(order3)
        self.assertEqual(order3.id in price_levels.levels_ordered, False)
        self.assertEqual(order3.id in price_levels.levels, False)