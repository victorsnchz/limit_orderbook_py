import unittest
import sys

# sys.path.append('../')
sys.path.append("src")

from src.orderbook.orderbook import OrderBook
from src.orders.order_id_generator import OrderIdGenerator
from src.orders.order import Order, OrderID, OrderSpec
from src.bookkeeping.custom_types import Side, OrderType, ExecutionRule, FilledOrder
from src.orderbook.orders_queue import OrdersQueue
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

    def test_post_rests_order_in_book(self):
        resting = _post_order(
            self.generator, self.orderbook, Side.BID, price=99, quantity=100
        )
        self.assertTrue(_order_in_book(self.orderbook, resting))

    def test_post_creates_level_at_limit_price(self):
        _post_order(self.generator, self.orderbook, Side.BID, price=99, quantity=100)

        self.assertEqual(len(self.orderbook.bid_side.levels), 1)

    def test_post_filled_order_not_rested(self):
        order = _make_limit_order(self.generator, Side.BID, price=99, quantity=100)
        order.fill(100)
        LimitOrderExecution(order, self.orderbook)._post_order()
        self.assertTrue(self.orderbook.bid_side.is_empty)


class TestLimitOrderExecutionMatch(unittest.TestCase):
    def setUp(self):
        self.orderbook = OrderBook()
        self.generator = OrderIdGenerator()

    def test_match_removes_level_when_fully_filled(self):
        resting = _post_order(
            self.generator, self.orderbook, Side.BID, price=99, quantity=100
        )
        aggressor = _make_limit_order(self.generator, Side.ASK, price=99, quantity=100)
        LimitOrderExecution(aggressor, self.orderbook)._match()
        self.assertNotIn(99, self.orderbook.bid_side.levels)
        self.assertTrue(resting.is_filled)
        self.assertTrue(aggressor.is_filled)

    def test_match_leaves_level_when_price_incompatible(self):
        resting = _post_order(
            self.generator, self.orderbook, Side.BID, price=99, quantity=100
        )
        aggressor = _make_limit_order(self.generator, Side.ASK, price=100, quantity=100)
        LimitOrderExecution(aggressor, self.orderbook)._match()
        self.assertIn(99, self.orderbook.bid_side.levels)
        self.assertFalse(resting.is_filled)
        self.assertFalse(aggressor.is_filled)

    def test_match_partial_fill_leaves_remainder_in_book(self):
        resting = _post_order(
            self.generator, self.orderbook, Side.BID, price=99, quantity=100
        )
        aggressor = _make_limit_order(self.generator, Side.ASK, price=99, quantity=50)
        LimitOrderExecution(aggressor, self.orderbook)._match()
        self.assertFalse(resting.is_filled)
        self.assertTrue(aggressor.is_filled)
        self.assertTrue(_order_in_book(self.orderbook, resting))

    def test_match_does_not_post_aggressor(self):
        _post_order(self.generator, self.orderbook, Side.BID, price=99, quantity=100)
        aggressor = _make_limit_order(self.generator, Side.ASK, price=99, quantity=50)
        LimitOrderExecution(aggressor, self.orderbook)._match()
        self.assertTrue(self.orderbook.ask_side.is_empty)
        self.assertFalse(_order_in_book(self.orderbook, aggressor))


class TestLimitOrderExecutionExecute(unittest.TestCase):
    def setUp(self):
        self.orderbook = OrderBook()
        self.generator = OrderIdGenerator()

    def test_execute_fully_matched_not_posted(self):
        _post_order(self.generator, self.orderbook, Side.ASK, price=99, quantity=100)
        aggressor = _make_limit_order(self.generator, Side.BID, price=99, quantity=100)
        LimitOrderExecution(aggressor, self.orderbook).execute()
        self.assertFalse(_order_in_book(self.orderbook, aggressor))

    def test_execute_partially_matched_remainder_posted(self):

        resting = _post_order(self.generator, self.orderbook, Side.ASK, 99, 60)
        aggressor = _make_limit_order(self.generator, Side.BID, 99, 100)
        LimitOrderExecution(aggressor, self.orderbook).execute()
        self.assertTrue(resting.is_filled)
        self.assertFalse(aggressor.is_filled)
        self.assertEqual(aggressor.remaining_quantity, 40)
        self.assertTrue(_order_in_book(self.orderbook, aggressor))

    def test_execute_no_match_posts_to_book(self):
        aggressor = _make_limit_order(self.generator, Side.ASK, price=99, quantity=100)
        LimitOrderExecution(aggressor, self.orderbook).execute()
        self.assertTrue(_order_in_book(self.orderbook, aggressor))
        self.assertFalse(aggressor.is_filled)

    def test_execute_fifo_priority_two_orders_same_price(self):
        first = _post_order(
            self.generator, self.orderbook, Side.BID, price=99, quantity=100
        )
        second = _post_order(
            self.generator, self.orderbook, Side.BID, price=99, quantity=100
        )
        aggressor = _make_limit_order(self.generator, Side.ASK, price=99, quantity=100)
        LimitOrderExecution(aggressor, self.orderbook).execute()
        self.assertTrue(first.is_filled)
        self.assertFalse(second.is_filled)
        self.assertEqual(second.initial_quantity, second.remaining_quantity)
        self.assertTrue(aggressor.is_filled)
        self.assertFalse(_order_in_book(self.orderbook, first))
        self.assertTrue(_order_in_book(self.orderbook, second))

    def test_execute_sweeps_multiple_levels(self):
        resting1 = _post_order(
            self.generator, self.orderbook, Side.ASK, price=99, quantity=100
        )
        resting2 = _post_order(
            self.generator, self.orderbook, Side.ASK, price=100, quantity=100
        )
        aggressor = _make_limit_order(self.generator, Side.BID, price=100, quantity=200)
        LimitOrderExecution(aggressor, self.orderbook).execute()
        self.assertTrue(resting1.is_filled)
        self.assertTrue(resting2.is_filled)
        self.assertTrue(aggressor.is_filled)
        self.assertTrue(self.orderbook.ask_side.is_empty)


class TestMarketOrderExecution(unittest.TestCase):
    def setUp(self):
        self.generator = OrderIdGenerator()
        self.orderbook = OrderBook()

    def test_match_against_resting_limit(self):
        resting = _post_order(
            self.generator, self.orderbook, Side.ASK, price=99, quantity=100
        )
        aggressor = _make_market_order(self.generator, Side.BID, quantity=100)
        MarketOrderExecution(aggressor, self.orderbook).execute()
        self.assertTrue(resting.is_filled)
        self.assertTrue(aggressor.is_filled)
        self.assertTrue(self.orderbook.bid_side.is_empty)

    def test_match_removes_level_when_filled(self):
        _post_order(self.generator, self.orderbook, Side.ASK, price=99, quantity=100)
        aggressor = _make_market_order(self.generator, Side.BID, quantity=100)
        MarketOrderExecution(aggressor, self.orderbook).execute()
        self.assertNotIn(99, self.orderbook.bid_side.levels)

    def test_no_match_on_empty_book(self):
        aggressor = _make_market_order(self.generator, Side.BID, quantity=100)
        MarketOrderExecution(aggressor, self.orderbook).execute()
        self.assertFalse(aggressor.is_filled)
        self.assertTrue(self.orderbook.bid_side.is_empty)

    def test_partial_fill_against_insufficient_liquidity(self):
        resting = _post_order(
            self.generator, self.orderbook, Side.ASK, price=99, quantity=100
        )
        aggressor = _make_market_order(self.generator, Side.BID, quantity=40)
        MarketOrderExecution(aggressor, self.orderbook).execute()
        self.assertEqual(resting.remaining_quantity, 60)
        self.assertTrue(aggressor.is_filled)
        self.assertTrue(aggressor.is_filled)
        self.assertTrue(self.orderbook.bid_side.is_empty)

    def test_sweeps_multiple_levels(self):
        resting1 = _post_order(
            self.generator, self.orderbook, Side.ASK, price=99, quantity=100
        )
        resting2 = _post_order(
            self.generator, self.orderbook, Side.ASK, price=100, quantity=100
        )
        aggressor = _make_market_order(self.generator, Side.BID, quantity=200)
        MarketOrderExecution(aggressor, self.orderbook).execute()
        self.assertTrue(resting1.is_filled)
        self.assertTrue(resting2.is_filled)
        self.assertTrue(aggressor.is_filled)
        self.assertTrue(self.orderbook.ask_side.is_empty)


class TestOrderExecutionMap(unittest.TestCase):
    def test_limit_key_returns_limit_execution_class(self):
        self.assertIs(map_order_type_to_execution[OrderType.LIMIT], LimitOrderExecution)

    def test_market_key_returns_market_execution_class(self):
        self.assertIs(
            map_order_type_to_execution[OrderType.MARKET], MarketOrderExecution
        )


def _queue_at(orderbook, side: Side, price: int) -> OrdersQueue:
    return orderbook.get_book_side(side).levels[price]


def _make_limit_order(
    generator: OrderIdGenerator, side: Side, price: int, quantity: int
) -> Order:
    spec = OrderSpec(side, OrderType.LIMIT, quantity, price, ExecutionRule.GTC)
    return Order(spec, OrderID(generator.next_id(), 0))


def _make_market_order(generator: OrderIdGenerator, side: Side, quantity: int) -> Order:
    spec = OrderSpec(side, OrderType.MARKET, quantity)
    return Order(spec, OrderID(generator.next_id(), 0))


def _post_order(
    generator: OrderIdGenerator,
    orderbook: OrderBook,
    side: Side,
    price: int,
    quantity: int,
) -> Order:
    order = _make_limit_order(generator, side, price, quantity)
    LimitOrderExecution(order, orderbook)._post_order()
    return order


def _order_in_book(orderbook: OrderBook, order: Order) -> bool:
    if order.order_type == OrderType.MARKET:
        raise ValueError("market orders are never posted in book")
    side = orderbook.bid_side if order.side == Side.BID else orderbook.ask_side
    if order.limit_price not in side.levels:
        return False
    # TODO: fix overly exposed queue implementation
    return order.order_id in _queue_at(orderbook, order.side, order.limit_price).queue


if __name__ == "__main__":
    unittest.main()
