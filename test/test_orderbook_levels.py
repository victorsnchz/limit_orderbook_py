import unittest
import sys

sys.path.append('src')

from orderbook.price_levels import Bids, Asks
from orders.order import Order, LimitOrder, MarketOrder, OrderID, OrderParameters
from bookkeeping.custom_types import OrderType, ExecutionRules, Side




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

    def test_get_price_levels_state(self):

        bids = Bids()
        
        bid1 = LimitOrder(OrderParameters(Side.BID, 100), OrderID(0),
                               limit_price=100, execution_rules = ExecutionRules.GTC)
        bid2 = LimitOrder(OrderParameters(Side.BID, 200), OrderID(1),
                               limit_price=100, execution_rules = ExecutionRules.GTC)
        bid3 = LimitOrder(OrderParameters(Side.BID, 100), OrderID(0),
                               limit_price=105, execution_rules = ExecutionRules.GTC)

        
        bids.post_order(bid1)
        bids.post_order(bid2)
        bids.post_order(bid3)

        
        bids_state = bids.get_price_levels_state()

        target = {100: (300, 2), 105: (100, 1)}

        self.assertDictEqual(bids_state, target)

    def test_get_top_of_book_state_bids(self):

        bids = Bids()
        
        bid1 = LimitOrder(OrderParameters(Side.BID, 100), OrderID(0),
                               limit_price=100, execution_rules = ExecutionRules.GTC)
        bid2 = LimitOrder(OrderParameters(Side.BID, 200), OrderID(1),
                               limit_price=100, execution_rules = ExecutionRules.GTC)
        bid3 = LimitOrder(OrderParameters(Side.BID, 100), OrderID(0),
                               limit_price=105, execution_rules = ExecutionRules.GTC)

        
        bids.post_order(bid1)
        bids.post_order(bid2)
        bids.post_order(bid3)

        
        bids_state = bids.get_top_of_book_state()

        target = {105: (100, 1)}

        self.assertDictEqual(bids_state, target)

    def test_get_top_of_book_state_asks(self):

        asks = Asks()
        
        ask1 = LimitOrder(OrderParameters(Side.ASK, 100), OrderID(0),
                               limit_price=100, execution_rules = ExecutionRules.GTC)
        ask2 = LimitOrder(OrderParameters(Side.ASK, 200), OrderID(1),
                               limit_price=100, execution_rules = ExecutionRules.GTC)
        ask3 = LimitOrder(OrderParameters(Side.ASK, 100), OrderID(0),
                               limit_price=105, execution_rules = ExecutionRules.GTC)

        
        asks.post_order(ask1)
        asks.post_order(ask2)
        asks.post_order(ask3)

        
        asks_state = asks.get_top_of_book_state()

        target = {100: (300, 2)}

        self.assertDictEqual(asks_state, target)


if __name__ == '__main__':
    unittest.main()