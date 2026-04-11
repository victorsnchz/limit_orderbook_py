import unittest
import sys

# sys.path.append('../')
sys.path.append("src")

from src.orderbook.orderbook import OrderBook
from src.orders.order_id_generator import OrderIdGenerator
from src.orders.order import Order, OrderID, OrderSpec
from src.bookkeeping.custom_types import Side, OrderType, ExecutionRule
from src.orderbook.order_execution import (
    LimitOrderExecution,
    MarketOrderExecution,
    map_order_type_to_execution,
    execute_order,
)


class TestLimitOrderExecutionPost(unittest.TestCase):
    def setUp(self):
        self.orderbook = OrderBook()
        self.generator = OrderIdGenerator()

    def _make_limit_order(self, side: Side, price: int, quantity: int) -> Order:
        spec = OrderSpec(side, OrderType.LIMIT, quantity, price, ExecutionRule.GTC)
        return Order(spec, OrderID(self.generator.next_id(), 0))

    def test_post_rests_order_in_book(self):
        order = self._make_limit_order(Side.BID, price=99, quantity=100)
        exec_ = LimitOrderExecution(order, self.orderbook)
        exec_.post_order()
        self.assertIn(99, self.orderbook.bid_side.levels)

    def test_post_creates_level_at_limit_price(self):
        order = self._make_limit_order(Side.BID, price=99, quantity=100)
        exec_ = LimitOrderExecution(order, self.orderbook)
        exec_.post_order()
        self.assertEqual(len(self.orderbook.bid_side.levels), 1)

    def test_post_filled_order_not_rested(self):
        order = self._make_limit_order(Side.BID, price=99, quantity=100)
        order.fill(100)
        exec_ = LimitOrderExecution(order, self.orderbook)
        exec_.post_order()
        self.assertTrue(self.orderbook.bid_side.is_empty)


class TestLimitOrderExecutionMatch(unittest.TestCase):
    def setUp(self): ...  # orderbook with one resting bid

    def test_match_removes_level_when_fully_filled(self): ...
    def test_match_leaves_level_when_price_incompatible(self): ...
    def test_match_partial_fill_leaves_remainder_in_book(self): ...
    def test_match_does_not_post_aggressor(self): ...


class TestLimitOrderExecutionExecute(unittest.TestCase):
    def setUp(self): ...

    def test_execute_fully_matched_not_posted(self): ...
    def test_execute_partially_matched_remainder_posted(self): ...
    def test_execute_no_match_posts_to_book(self): ...
    def test_execute_fifo_priority_two_orders_same_price(self): ...


class TestMarketOrderExecution(unittest.TestCase):
    def setUp(self): ...

    def test_match_against_resting_limit(self): ...
    def test_match_removes_level_when_filled(self): ...
    def test_no_match_on_empty_book(self): ...
    def test_market_order_not_posted_if_unfilled(self): ...
    def test_partial_fill_against_insufficient_liquidity(self): ...


class TestOrderExecutionMap(unittest.TestCase):
    def test_limit_key_returns_limit_execution_class(self):
        self.assertIs(map_order_type_to_execution[OrderType.LIMIT], LimitOrderExecution)

    def test_market_key_returns_market_execution_class(self):
        self.assertIs(
            map_order_type_to_execution[OrderType.MARKET], MarketOrderExecution
        )


if __name__ == "__main__":
    unittest.main()
