import unittest
import sys

#sys.path.append('../')
sys.path.append('src')

from order import Order, MarketOrder, LimitOrder, OrderParameters, OrderID
from custom_types import ExecutionRules, OrderType, Side
from order_execution import LimitOrderExecution, MarketOrderExecution
from orderbook import OrderBook
from order import LimitOrder

class TestLimitOrderExecution(unittest.TestCase):

    def test_case_post(self):
        orderbook = OrderBook()
        order_to_post = LimitOrder(OrderParameters(Side.BID, 100), OrderID(0),
                               limit_price=100, execution_rules = ExecutionRules.GTC)
        
        exec = LimitOrderExecution(order_to_post, orderbook)
        exec.post_order()

        price_levels = orderbook.get_levels(order_to_post.get_side())

        self.assertEqual(order_to_post.limit_price in price_levels.levels, True)

    def test_case_match(self):
        common_price = 100

        orderbook = OrderBook()
        order_to_post = LimitOrder(OrderParameters(Side.BID, 100), OrderID(0),
                               limit_price=common_price, execution_rules = ExecutionRules.GTC)
        
        exec = LimitOrderExecution(order_to_post, orderbook)
        exec.post_order()

        order_to_match = LimitOrder(OrderParameters(Side.ASK, 100), OrderID(1),
                               limit_price=common_price, execution_rules = ExecutionRules.GTC)

        exec = LimitOrderExecution(order_to_match, orderbook)
        exec.match_order()

        price_levels = orderbook.get_opposite_side_levels(order_to_match.get_side())

        self.assertEqual(common_price in price_levels.levels, False)
        self.assertEqual(order_to_post.is_filled(), True)
        self.assertEqual(order_to_match.is_filled(), True)

    def test_case_cannot_match(self):

        orderbook = OrderBook()
        order_to_post = LimitOrder(OrderParameters(Side.BID, 100), OrderID(0),
                               limit_price=100, execution_rules = ExecutionRules.GTC)
        
        exec = LimitOrderExecution(order_to_post, orderbook)
        exec.post_order()

        order_to_match = LimitOrder(OrderParameters(Side.ASK, 100), OrderID(1),
                               limit_price=101, execution_rules = ExecutionRules.GTC)

        exec = LimitOrderExecution(order_to_match, orderbook)
        exec.match_order()

        price_levels = orderbook.get_opposite_side_levels(order_to_match.get_side())

        self.assertEqual(order_to_post.limit_price in price_levels.levels, True)
        self.assertEqual(order_to_post.is_filled(), False)
        self.assertEqual(order_to_match.is_filled(), False)

    def test_case_execute_post_and_match(self):

        common_price = 100

        orderbook = OrderBook()
        order_to_post = LimitOrder(OrderParameters(Side.BID, 100), OrderID(0),
                               limit_price=common_price, execution_rules = ExecutionRules.GTC)
        
        exec = LimitOrderExecution(order_to_post, orderbook)
        exec.post_order()

        order_to_match = LimitOrder(OrderParameters(Side.ASK, 150), OrderID(1),
                               limit_price=common_price, execution_rules = ExecutionRules.GTC)

        exec = LimitOrderExecution(order_to_match, orderbook)
        exec.execute()

        self.assertEqual(common_price in orderbook.bids.levels, False)
        self.assertEqual(common_price in orderbook.asks.levels, True)
        self.assertEqual(order_to_post.is_filled(), True)
        self.assertEqual(order_to_match.is_filled(), False)
        

class TestMarketOrderExecution(unittest.TestCase):

    def test_case_match(self):
        common_price = 100

        orderbook = OrderBook()
        order_to_post = LimitOrder(OrderParameters(Side.BID, 100), OrderID(0),
                               limit_price=common_price, execution_rules = ExecutionRules.GTC)
        
        exec = LimitOrderExecution(order_to_post, orderbook)
        exec.post_order()

        order_to_match = MarketOrder(OrderParameters(Side.ASK, 100), OrderID(1))

        exec = MarketOrderExecution(order_to_match, orderbook)
        exec.execute()

        price_levels = orderbook.get_opposite_side_levels(order_to_match.get_side())

        self.assertEqual(common_price in price_levels.levels, False)
        self.assertEqual(order_to_post.is_filled(), True)
        self.assertEqual(order_to_match.is_filled(), True)

    def test_case_cannot_match(self):

        orderbook = OrderBook()

        order_to_match = MarketOrder(OrderParameters(Side.ASK, 100), OrderID(1))

        exec = MarketOrderExecution(order_to_match, orderbook)
        exec.execute()

        price_levels = orderbook.get_opposite_side_levels(order_to_match.get_side())

        self.assertEqual(order_to_match.is_filled(), False)

if __name__ == '__main__':
    unittest.main()