import unittest
import sys

# TODO
# fix import system accross package
# seems like test_order called first, appends src to path then subsequent test modules can test src
# individual test module will fail import otherwise
sys.path.append('src')

from order import Order, MarketOrder, LimitOrder, OrderParameters, OrderID
from custom_types import ExecutionRules, OrderType, Side

class TestOrder(unittest.TestCase):

    def test_case_init_order(self):

        gtc_order = LimitOrder(OrderParameters(Side.BID, 100), OrderID(0),
                               limit_price=100, execution_rules = ExecutionRules.GTC)
        
        self.assertEqual(gtc_order.remaining_quantity, gtc_order.get_initial_quantity())

    def test_case_fill_quantity(self):

        gtc_order = LimitOrder(OrderParameters(Side.BID, 100), OrderID(0),
                               limit_price=100, execution_rules = ExecutionRules.GTC)

        to_fill = 50
        gtc_order.fill_quantity(to_fill)
        self.assertEqual(gtc_order.remaining_quantity, gtc_order.get_initial_quantity() - to_fill)
        self.assertEqual(gtc_order.is_filled(), False)

    def test_case_full_fill(self):

        gtc_order = LimitOrder(OrderParameters(Side.BID, 100), OrderID(0),
                               limit_price=100, execution_rules = ExecutionRules.GTC)

        to_fill = gtc_order.remaining_quantity
        gtc_order.fill_quantity(to_fill)
        self.assertEqual(gtc_order.remaining_quantity, 0)
        self.assertEqual(gtc_order.is_filled(), True)

    def test_case_overfill(self):
        gtc_order = LimitOrder(OrderParameters(Side.BID, 100), OrderID(0),
                               limit_price=100, execution_rules = ExecutionRules.GTC)

        to_fill = gtc_order.remaining_quantity * 2
        gtc_order.fill_quantity(to_fill )
        self.assertEqual(gtc_order.remaining_quantity, 0)
        self.assertEqual(gtc_order.is_filled(), True)

if __name__ == '__main__':
    unittest.main()