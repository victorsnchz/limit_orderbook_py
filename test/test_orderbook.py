import unittest
import sys

sys.path.append('src')

from orderbook import OrderBook
from order import Order, LimitOrder, OrderID, OrderParameters
from custom_types import OrderType, Side, ExecutionRules
from price_levels import Bids, Asks

# blend of unit-testing and integration testing

class TestOrderbook(unittest.TestCase):

    def test_case_get_side(self):

        orderbook = OrderBook()
        side_to_get = Side.BID

        side = orderbook.get_levels(side_to_get)

        self.assertEqual(type(side), Bids)

    def test_case_get_opposite_side(self):

        orderbook = OrderBook()
        side_to_get = Side.BID

        side = orderbook.get_opposite_side_levels(side_to_get)

        self.assertEqual(type(side), Asks)
    

if __name__ == '__main__':
    unittest.main()

