import unittest
import sys

#sys.path.append('../')
sys.path.append('src')

from orders.order import Order, OrderID, OrderSpec
from bookkeeping.custom_types import ExecutionRule, OrderType, Side
from orderbook.order_execution import LimitOrderExecution, MarketOrderExecution
from orderbook.orderbook import OrderBook

class TestLimitOrderExecution(unittest.TestCase):

    def test_case_post(self):
        orderbook = OrderBook()

        spec = OrderSpec(Side.BID, OrderType.LIMIT, 
                         quantity=100, execution_rule=ExecutionRule.GTC,
                         limit_price=100)
        


        order_to_post = Order(spec, OrderID(0, 0))
        
        exec = LimitOrderExecution(order_to_post, orderbook)
        exec.post_order()

        price_levels = orderbook.get_levels(order_to_post.side)

        self.assertEqual(order_to_post.limit_price in price_levels.levels, True)

    def test_case_match(self):
        common_price = 100

        orderbook = OrderBook()

        spec = OrderSpec(Side.BID, OrderType.LIMIT, 
                         quantity = 100, execution_rule=ExecutionRule.GTC,
                         limit_price = common_price)

        order_to_post = Order(spec, OrderID(0, 0))
        
        exec = LimitOrderExecution(order_to_post, orderbook)
        exec.post_order()

        spec = OrderSpec(Side.ASK, OrderType.LIMIT, 
                         quantity = 100, execution_rule=ExecutionRule.GTC,
                         limit_price = common_price)

        order_to_match = Order(spec, OrderID(1, 0))

        exec = LimitOrderExecution(order_to_match, orderbook)
        exec.match_order()

        price_levels = orderbook.get_opposite_side_levels(order_to_match.side)

        self.assertEqual(common_price in price_levels.levels, False)
        self.assertEqual(order_to_post.is_filled(), True)
        self.assertEqual(order_to_match.is_filled(), True)

    def test_case_cannot_match(self):

        orderbook = OrderBook()

        spec = OrderSpec(Side.BID, OrderType.LIMIT, 
                         quantity = 100, execution_rule=ExecutionRule.GTC,
                         limit_price = 100)
        
        order_to_post = Order(spec, OrderID(0, 0))
        
        exec = LimitOrderExecution(order_to_post, orderbook)
        exec.post_order()

        spec = OrderSpec(Side.ASK, OrderType.LIMIT, 
                         quantity = 100, execution_rule=ExecutionRule.GTC,
                         limit_price = 105)

        order_to_match = Order(spec, OrderID(1, 0))

        exec = LimitOrderExecution(order_to_match, orderbook)
        exec.match_order()

        price_levels = orderbook.get_opposite_side_levels(order_to_match.side)

        self.assertEqual(order_to_post.limit_price in price_levels.levels, True)
        self.assertEqual(order_to_post.is_filled(), False)
        self.assertEqual(order_to_match.is_filled(), False)

    def test_case_execute_post_and_match(self):

        common_price = 100

        orderbook = OrderBook()

        spec = OrderSpec(Side.BID, OrderType.LIMIT, 
                         quantity = 100, execution_rule=ExecutionRule.GTC,
                         limit_price = common_price)


        order_to_post = Order(spec, OrderID(0, 0))
        
        exec = LimitOrderExecution(order_to_post, orderbook)
        exec.post_order()

        spec = OrderSpec(Side.ASK, OrderType.LIMIT, 
                         quantity = 150, execution_rule=ExecutionRule.GTC,
                         limit_price = common_price)

        order_to_match = Order(spec, OrderID(1, 0))

        exec = LimitOrderExecution(order_to_match, orderbook)
        exec.execute()

        self.assertEqual(common_price in orderbook.bids.levels, False)
        self.assertEqual(common_price in orderbook.asks.levels, True)
        self.assertEqual(order_to_post.is_filled(), True)
        self.assertEqual(order_to_match.is_filled(), False)
        

class TestMarketOrderExecutionAgainstLimit(unittest.TestCase):
    def test_case_match(self):
        common_price = 100

        orderbook = OrderBook()
        
        spec = OrderSpec(Side.BID, OrderType.LIMIT, 
                         quantity = 100, execution_rule=ExecutionRule.GTC,
                         limit_price = common_price)

        order_to_post = Order(spec, OrderID(0, 0))
        
        exec = LimitOrderExecution(order_to_post, orderbook)
        exec.post_order()

        spec = OrderSpec(Side.ASK, OrderType.MARKET, 
                         quantity = 100, execution_rule=ExecutionRule.GTC,
                         limit_price = common_price)

        order_to_match = Order(spec, OrderID(1, 0))

        exec = MarketOrderExecution(order_to_match, orderbook)
        exec.execute()

        price_levels = orderbook.get_opposite_side_levels(order_to_match.side)

        self.assertEqual(common_price in price_levels.levels, False)
        self.assertEqual(order_to_post.is_filled(), True)
        self.assertEqual(order_to_match.is_filled(), True)

    def test_case_cannot_match(self):

        orderbook = OrderBook()

        spec = OrderSpec(Side.BID, OrderType.MARKET, 
                         quantity = 100, execution_rule=ExecutionRule.GTC,
                         limit_price = 100)

        order_to_match = Order(spec, OrderID(0, 0))

        exec = MarketOrderExecution(order_to_match, orderbook)
        exec.execute()

        price_levels = orderbook.get_opposite_side_levels(order_to_match.side)

        self.assertEqual(order_to_match.is_filled(), False)

if __name__ == '__main__':
    unittest.main()