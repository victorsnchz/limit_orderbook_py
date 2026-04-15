import unittest

from src.orderbook.orderbook import OrderBook
from src.orders.order import Order, OrderID, OrderSpec
from src.bookkeeping.custom_types import (
    Side,
    ExecutionRule,
    OrderType,
)
from src.bookkeeping.exceptions import InvalidOrderError, DuplicateOrderError
from src.orderbook.book_side import BidSide, AskSide
from src.orders.order_id_generator import OrderIdGenerator


class TestOrderBookRouting(unittest.TestCase):
    def setUp(self):
        self.orderbook = OrderBook()

    def test_get_book_side_bid_returns_bid_side(self):
        side = self.orderbook.get_book_side(Side.BID)
        self.assertIsInstance(side, BidSide)

    def test_get_book_side_ask_returns_ask_side(self):
        side = self.orderbook.get_book_side(Side.ASK)
        self.assertIsInstance(side, AskSide)

    def test_get_opposite_book_side_bid_returns_ask(self):
        side = self.orderbook.get_opposite_book_side(Side.BID)
        self.assertIsInstance(side, AskSide)

    def test_get_opposite_book_side_ask_returns_bid(self):
        side = self.orderbook.get_opposite_book_side(Side.ASK)
        self.assertIsInstance(side, BidSide)

    def test_get_book_side_invalid_raises(self):
        with self.assertRaises(TypeError):
            self.orderbook.get_book_side("BID")

    def test_get_opposite_book_side_invalid_raises(self):
        with self.assertRaises(TypeError):
            self.orderbook.get_opposite_book_side("BID")


class TestOrderBookBidAskMid(unittest.TestCase):
    def setUp(self):
        self.orderbook = OrderBook()
        self.orderbook.bid_side = StubBidSide()
        self.orderbook.ask_side = StubAskSide()
        self.generator = OrderIdGenerator()

    def test_returns_correct_bid_ask_mid(self):

        bid, ask, mid = self.orderbook.get_bid_ask_mid()

        self.assertEqual(bid, StubBidSide.best_price)
        self.assertEqual(ask, StubAskSide.best_price)
        self.assertEqual(mid, (StubBidSide.best_price + StubAskSide.best_price) / 2)

    def test_empty_book_raises(self):
        self.orderbook.bid_side = StubEmptySide()
        self.orderbook.ask_side = StubEmptySide()
        with self.assertRaises(RuntimeError):
            self.orderbook.get_bid_ask_mid()

    def test_no_bids_raises(self):
        self.orderbook.bid_side = StubEmptySide()
        with self.assertRaises(RuntimeError):
            self.orderbook.get_bid_ask_mid()

    def test_no_asks_raises(self):
        self.orderbook.ask_side = StubEmptySide()
        with self.assertRaises(RuntimeError):
            self.orderbook.get_bid_ask_mid()


class TestPostOrder(unittest.TestCase):
    def setUp(self):
        self.orderbook = OrderBook()
        self.orderbook.bid_side = StubBidSide()
        self.orderbook.ask_side = StubAskSide()
        self.generator = OrderIdGenerator()

    def test_post_non_limit_order_raises(self):
        market_order = _make_market_order(self.generator, Side.ASK, quantity=100)
        with self.assertRaises(InvalidOrderError):
            self.orderbook.post_order(market_order)

    def test_post_duplicate_order_raises(self):
        order = _make_limit_order(self.generator, Side.BID, price=100, quantity=100)

        self.orderbook.post_order(order)
        with self.assertRaises(DuplicateOrderError):
            self.orderbook.post_order(order)

    def test_post_filled_order_raises(self):
        order = _make_limit_order(self.generator, Side.BID, price=100, quantity=0)
        with self.assertRaises(InvalidOrderError):
            self.orderbook.post_order(order)

    def test_post_order_sets_correct_order_index_entry(self):
        order = _make_limit_order(self.generator, Side.BID, price=100, quantity=100)
        self.orderbook.post_order(order)
        self.assertIn(order.order_id, self.orderbook._order_index)
        self.assertEqual(
            self.orderbook._order_index[order.order_id], (order.side, order.limit_price)
        )


def _make_limit_order(
    generator: OrderIdGenerator, side: Side, price: int, quantity: int
) -> Order:
    spec = OrderSpec(side, OrderType.LIMIT, quantity, price, ExecutionRule.GTC)
    return Order(spec, OrderID(generator.next_id(), 0))


def _make_market_order(generator: OrderIdGenerator, side: Side, quantity: int) -> Order:
    spec = OrderSpec(side, OrderType.MARKET, quantity)
    return Order(spec, OrderID(generator.next_id(), 0))


class StubSide:
    def post_order(self, order: Order) -> None:
        return

    def get_states(self) -> dict[int, int]:
        return {0, 0}

    def get_top_states(self) -> dict[int, int]:
        return {0, 0}

    def get_volumes(self) -> dict[int, int]:
        return {0, 0}


class StubBidSide(StubSide):
    is_empty = False
    best_price = 99


class StubAskSide(StubSide):
    is_empty = False
    best_price = 100


class StubEmptySide(StubSide):
    is_empty = True
    best_price = None


if __name__ == "__main__":
    unittest.main()
