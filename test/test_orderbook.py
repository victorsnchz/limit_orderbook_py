import unittest
import sys

sys.path.append('src')

from orderbook.orderbook import OrderBook
from orders.order import Order, LimitOrder, OrderID, OrderParameters
from bookkeeping.custom_types import OrderType, Side, ExecutionRules
from orderbook.price_levels import Bids, Asks
from orderbook.order_execution import LimitOrderExecution

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

    def test_get_orderbook_state_two_sides(self):

        orderbook = OrderBook()

        bid1 = LimitOrder(OrderParameters(Side.BID, 100), OrderID(0),
                               limit_price=100, execution_rules = ExecutionRules.GTC)
        bid2 = LimitOrder(OrderParameters(Side.BID, 200), OrderID(1),
                               limit_price=100, execution_rules = ExecutionRules.GTC)
        bid3 = LimitOrder(OrderParameters(Side.BID, 100), OrderID(0),
                               limit_price=105, execution_rules = ExecutionRules.GTC)

        ask1 = LimitOrder(OrderParameters(Side.ASK, 100), OrderID(2),
                               limit_price=110, execution_rules = ExecutionRules.GTC)
        ask2 = LimitOrder(OrderParameters(Side.ASK, 100), OrderID(3),
                               limit_price=120, execution_rules = ExecutionRules.GTC)

        orders = [bid1, bid2, bid3, ask1, ask2]

        for order in orders:
            exec = LimitOrderExecution(order, orderbook)
            exec.execute()

        states = orderbook.get_orderbook_state()

        target_bids = {105: (100, 1), 100: (300, 2)}
        target_asks = {110: (100, 1), 120: (100, 1)}

        self.assertDictEqual(states[0], target_bids)
        self.assertDictEqual(states[1], target_asks)

    def test_get_orderbook_top_of_book_state(self):

        orderbook = OrderBook()

        bid1 = LimitOrder(OrderParameters(Side.BID, 100), OrderID(0),
                               limit_price=100, execution_rules = ExecutionRules.GTC)
        bid2 = LimitOrder(OrderParameters(Side.BID, 200), OrderID(1),
                               limit_price=100, execution_rules = ExecutionRules.GTC)
        bid3 = LimitOrder(OrderParameters(Side.BID, 100), OrderID(0),
                               limit_price=105, execution_rules = ExecutionRules.GTC)

        ask1 = LimitOrder(OrderParameters(Side.ASK, 100), OrderID(2),
                               limit_price=110, execution_rules = ExecutionRules.GTC)
        ask2 = LimitOrder(OrderParameters(Side.ASK, 100), OrderID(3),
                               limit_price=120, execution_rules = ExecutionRules.GTC)

        orders = [bid1, bid2, bid3, ask1, ask2]

        for order in orders:
            exec = LimitOrderExecution(order, orderbook)
            exec.execute()

        states = orderbook.get_top_of_book_state()

        target_bids = {105: (100, 1)}
        target_asks = {110: (100, 1)}

        self.assertDictEqual(states[0], target_bids)
        self.assertDictEqual(states[1], target_asks)


if __name__ == '__main__':
    unittest.main()

