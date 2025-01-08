import unittest
import sys

sys.path.append('src')

from price_levels import Bids, Asks
from order import Order, LimitOrder, MarketOrder, OrderID, OrderParameters
from custom_types import OrderType, ExecutionRules, Side




class TestPriceLevels(unittest.TestCase):
    
    def test_case_empty(self):

        price_levels = Asks()

        self.assertEqual(price_levels.is_empty(), True)

    def test_case_add_order(self):

        price_levels = Asks()
        order = LimitOrder(OrderParameters(Side.ASK, 100), OrderID(0),
                            limit_price=100, execution_rules = ExecutionRules.GTC)
        
        self.assertEqual(order.limit_price in price_levels.levels, False)

        price_levels.post_order(order)

        self.assertEqual(order.limit_price in price_levels.levels, True)
        self.assertEqual(order.get_id() in price_levels.levels[order.limit_price].queue, True)

    def test_case_best_price(self):

        price_levels = Bids()

        order = LimitOrder(OrderParameters(Side.BID, 100), OrderID(0),
                               limit_price=100, execution_rules = ExecutionRules.GTC)
        order2 = LimitOrder(OrderParameters(Side.BID, 100), OrderID(1),
                               limit_price=101, execution_rules = ExecutionRules.GTC)
        
        price_levels.post_order(order)
        price_levels.post_order(order2)

        self.assertEqual(price_levels.get_best_price(), order2.limit_price)


if __name__ == '__main__':
    unittest.main()