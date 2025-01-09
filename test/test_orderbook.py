import unittest
import sys

sys.path.append('src')

from orderbook import OrderBook
from order import Order, LimitOrder, OrderID, OrderParameters
from custom_types import OrderType, Side, ExecutionRules
from price_levels import Bids, Asks
from order_execution import LimitOrderExecution

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

    def test_case_get_bid_ask_mid(self):

        orderbook = OrderBook()
        
        order = LimitOrder(OrderParameters(Side.BID, 100), OrderID(0),
                               limit_price=100, execution_rules = ExecutionRules.GTC)
        order2 = LimitOrder(OrderParameters(Side.ASK, 100), OrderID(1),
                               limit_price=101, execution_rules = ExecutionRules.GTC)

        exec = LimitOrderExecution(order, orderbook)
        exec.post_order()

        exec = LimitOrderExecution(order2, orderbook)
        exec.post_order()

        bid, ask, mid = orderbook.get_bid_ask_mid()

        self.assertEqual((bid, ask, mid), (100, 101, 100.5))
    

if __name__ == '__main__':
    unittest.main()

