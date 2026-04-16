import unittest
from unittest.mock import MagicMock, PropertyMock
from src.orderbook.orderbook import OrderBook
from src.orders.order import Order, OrderID, OrderSpec
from src.bookkeeping.custom_types import (
    Side,
    ExecutionRule,
    OrderType,
)
from test.mocks import StubAskSide, StubBidSide, StubEmptySide, StubLevels
from src.bookkeeping.exceptions import InvalidOrderError, DuplicateOrderError
from src.orderbook.book_side import BidSide, AskSide


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


class TestPostOrder(unittest.TestCase):
    def setUp(self):
        self.orderbook = OrderBook()
        self.orderbook.bid_side = MagicMock()
        self.orderbook.ask_side = MagicMock()

    def test_post_bid_order_delegates_to_bid_side(self):
        order = _make_limit_order()

        self.orderbook.post_order(order)

        self.orderbook.bid_side.post_order.assert_called_once_with(order)
        self.orderbook.ask_side.post_order.assert_not_called()

    def test_post_ask_order_delegatees_to_ask_side(self):
        order = _make_limit_order(side=Side.ASK)

        self.orderbook.post_order(order)

        self.orderbook.ask_side.post_order.assert_called_once_with(order)
        self.orderbook.bid_side.post_order.assert_not_called()

    def test_order_indexed_after_post(self):
        order = _make_limit_order()

        self.orderbook.post_order(order)
        self.assertIn(order.order_id, self.orderbook._order_index)
        self.assertEqual(
            self.orderbook._order_index[order.order_id], (order.side, order.limit_price)
        )

    def test_post_multiple_distinct_orders(self):
        for i in range(3):
            order = _make_limit_order(order_id=i)
            self.orderbook.post_order(order)

        self.assertEqual(len(self.orderbook._order_index), 3)

    def test_post_non_limit_raises(self):
        order = _make_market_order()

        with self.assertRaises(InvalidOrderError):
            self.orderbook.post_order(order)

    def test_post_non_limit_no_effect(self):
        order = _make_market_order()

        with self.assertRaises(InvalidOrderError):
            self.orderbook.post_order(order)

        self.assertNotIn(order.order_id, self.orderbook._order_index)

    def test_post_order_rejects_duplicates(self):
        order = _make_limit_order()
        self.orderbook.post_order(order)

        with self.assertRaises(DuplicateOrderError):
            self.orderbook.post_order(order)

    def test_post_duplicate_no_effect(self):
        order = _make_limit_order(order_id=1, limit_price=100)
        self.orderbook.post_order(order)

        initial_indexed_values = self.orderbook._order_index[order.order_id]
        order = _make_limit_order(order_id=1, limit_price=200)
        with self.assertRaises(DuplicateOrderError):
            self.orderbook.post_order(order)

        self.assertEqual(
            self.orderbook._order_index[order.order_id], initial_indexed_values
        )

    def test_post_order_rejects_filled(self):
        order = _make_limit_order(quantity=0, is_filled=True)
        with self.assertRaises(InvalidOrderError):
            self.orderbook.post_order(order)

    def test_post_filled_order_no_effect(self):
        order = _make_limit_order(quantity=0, is_filled=True)
        with self.assertRaises(InvalidOrderError):
            self.orderbook.post_order(order)
        self.assertNotIn(order.order_id, self.orderbook._order_index)


class TestOrderBookBidAskMid(unittest.TestCase):
    def setUp(self):
        self.orderbook = OrderBook()
        self.orderbook.bid_side = MagicMock()
        self.orderbook.ask_side = MagicMock()

    def _set_sides(self, bid_empty, ask_empty, bid_price=None, ask_price=None):
        type(self.orderbook.bid_side).is_empty = PropertyMock(return_value=bid_empty)
        type(self.orderbook.ask_side).is_empty = PropertyMock(return_value=ask_empty)
        if bid_price is not None:
            type(self.orderbook.bid_side).best_price = PropertyMock(
                return_value=bid_price
            )
        if ask_price is not None:
            type(self.orderbook.ask_side).best_price = PropertyMock(
                return_value=ask_price
            )

    def test_returns_correct_tuple(self):
        self._set_sides(False, False, 99, 101)
        bid, ask, mid = self.orderbook.get_bid_ask_mid()
        self.assertEqual(bid, 99)
        self.assertEqual(ask, 101)
        self.assertEqual(mid, 100)

    def test_mid_as_float(self):
        self._set_sides(False, False, 99, 101)
        _, _, mid = self.orderbook.get_bid_ask_mid()

        self.assertIsInstance(mid, float)

    def test_zero_spread(self):
        self._set_sides(False, False, 100, 100)
        bid, ask, mid = self.orderbook.get_bid_ask_mid()
        self.assertEqual(bid, ask)
        self.assertEqual(mid, 100.0)

    def test_odd_spread_half_tick_mid(self):
        self._set_sides(False, False, 99, 100)
        _, _, mid = self.orderbook.get_bid_ask_mid()
        self.assertEqual(mid, 99.5)

    def test_both_sides_empty_raises(self):

        self._set_sides(True, True)
        with self.assertRaises(RuntimeError):
            self.orderbook.get_bid_ask_mid()

    def test_bid_empty_raises(self):
        self._set_sides(True, False)
        with self.assertRaises(RuntimeError):
            self.orderbook.get_bid_ask_mid()

    def test_ask_empty_raises(self):
        self._set_sides(False, True)
        with self.assertRaises(RuntimeError):
            self.orderbook.get_bid_ask_mid()

    def test_empty_does_not_access_best_price(self):
        self._set_sides(True, True)
        with self.assertRaises(RuntimeError):
            self.orderbook.get_bid_ask_mid()
        type(self.orderbook.bid_side).best_price = PropertyMock(
            side_effect=AssertionError("should not be called")
        )
        type(self.orderbook.ask_side).best_price = PropertyMock(
            side_effect=AssertionError("should not be called")
        )


class TestGetBookSide(unittest.TestCase):
    def setUp(self):
        self.orderbook = OrderBook()
        self.orderbook.bid_side = MagicMock()
        self.orderbook.ask_side = MagicMock()

    def test_bid_returns_bid_side(self):
        self.assertIs(self.orderbook.get_book_side(Side.BID), self.orderbook.bid_side)

    def test_ask_returns_bid_side(self):
        self.assertIs(self.orderbook.get_book_side(Side.ASK), self.orderbook.ask_side)

    def test_invalid_type_raises(self):
        for bad_input in ("BID", 1, None):
            with self.subTest(value=bad_input):
                with self.assertRaises(TypeError):
                    self.orderbook.get_book_side(bad_input)


class TestGetOppositeBookSide(unittest.TestCase):
    def setUp(self):
        self.orderbook = OrderBook()
        self.orderbook.bid_side = MagicMock()
        self.orderbook.ask_side = MagicMock()

    def test_bid_returns_ask_side(self):
        self.assertIs(
            self.orderbook.get_opposite_book_side(Side.BID), self.orderbook.ask_side
        )

    def test_ask_returns_bid_side(self):
        self.assertIs(
            self.orderbook.get_opposite_book_side(Side.ASK), self.orderbook.bid_side
        )

    def test_invalid_type_raises(self):

        for bad_input in ("BID", 1, None):
            with self.subTest(value=bad_input):
                with self.assertRaises(TypeError):
                    self.orderbook.get_opposite_book_side(bad_input)

    def test_symmetry(self):

        self.orderbook.get_opposite_book_side(Side.BID)
        second = self.orderbook.get_opposite_book_side(Side.ASK)
        self.assertIs(second, self.orderbook.bid_side)


class TestGetStates(unittest.TestCase):
    def setUp(self):
        self.orderbook = OrderBook()
        self.orderbook.bid_side = MagicMock()
        self.orderbook.ask_side = MagicMock()

    def test_delegates_to_both_sides(self):
        self.orderbook.get_states()
        self.orderbook.bid_side.get_states.assert_called_once()
        self.orderbook.ask_side.get_states.assert_called_once()

    def test_returns_bid_then_ask(self):
        self.orderbook.bid_side.get_states.return_value = {"bid_data": True}
        self.orderbook.ask_side.get_states.return_value = {"ask_data": True}
        bids, asks = self.orderbook.get_states()
        self.assertEqual(bids, {"bid_data": True})
        self.assertEqual(asks, {"ask_data": True})


class TestGetTopState(unittest.TestCase):
    def setUp(self):
        self.orderbook = OrderBook()
        self.orderbook.bid_side = MagicMock()
        self.orderbook.ask_side = MagicMock()

    def test_delegates_to_both_sides(self):
        self.orderbook.get_top_state()
        self.orderbook.bid_side.get_top_state.assert_called_once()
        self.orderbook.ask_side.get_top_state.assert_called_once()

    def test_returns_bid_then_ask(self):
        sentinel_bid = object()
        sentinel_ask = object()
        self.orderbook.bid_side.get_top_state.return_value = sentinel_bid
        self.orderbook.ask_side.get_top_state.return_value = sentinel_ask
        bids, asks = self.orderbook.get_top_state()
        self.assertIs(bids, sentinel_bid)
        self.assertIs(asks, sentinel_ask)


class TestGetVolumes(unittest.TestCase):
    def setUp(self):
        self.orderbook = OrderBook()
        self.orderbook.bid_side = MagicMock()
        self.orderbook.ask_side = MagicMock()

    def test_delegates_to_both_sides(self):
        self.orderbook.get_volumes()
        self.orderbook.bid_side.get_volumes.assert_called_once()
        self.orderbook.ask_side.get_volumes.assert_called_once()

    def test_returns_bid_then_ask(self):
        sentinel_bid = object()
        sentinel_ask = object()
        self.orderbook.bid_side.get_volumes.return_value = sentinel_bid
        self.orderbook.ask_side.get_volumes.return_value = sentinel_ask
        bids, asks = self.orderbook.get_volumes()
        self.assertIs(bids, sentinel_bid)
        self.assertIs(asks, sentinel_ask)


def _make_limit_order(
    order_id=1,
    side: Side = Side.BID,
    limit_price: int = 100,
    quantity=100,
    is_filled=False,
    execution_rule: ExecutionRule = ExecutionRule.GTC,
):

    order = MagicMock(spec=Order)
    order.order_id = order_id
    order.side = side
    order.order_type = OrderType.LIMIT
    order.limit_price = limit_price
    order.initial_quantity = quantity
    order.remaining_quantity = quantity
    order.is_filled = is_filled
    order.execution_rule = execution_rule

    return order


class TestGetOrder(unittest.TestCase):
    def setUp(self):
        self.orderbook = OrderBook()
        self.orderbook.bid_side = MagicMock()
        self.orderbook.ask_side = MagicMock()

    def test_unknown_order_raises(self):
        with self.assertRaises(InvalidOrderError):
            self.orderbook.get_order(0)

    def test_retrieves_from_correct_side_and_level(self):
        sentinel_order = object()
        self.orderbook._order_index[0] = (Side.BID, 99)

        mock_queue = MagicMock()
        mock_queue.queue = {0: sentinel_order}
        self.orderbook.bid_side.levels = {99: mock_queue}
        result = self.orderbook.get_order(0)
        self.assertIs(result, sentinel_order)

    def test_does_not_touch_opposite_side(self):
        self.orderbook._order_index[1] = (Side.ASK, 100)

        mock_queue = MagicMock()
        mock_queue.queue = {1: MagicMock()}
        self.orderbook.ask_side.levels = {100: mock_queue}

        self.orderbook.get_order(1)
        self.orderbook.bid_side.assert_not_called()


def _make_market_order(
    order_id=1,
    side: Side = Side.BID,
    quantity=100,
    is_filled=False,
):

    order = MagicMock(spec=Order)
    order_id = order_id
    order.side = side
    order.order_type = OrderType.MARKET
    order.initial_quantity = quantity
    order.remaining_quantity = quantity
    order.is_filled = is_filled

    return order


if __name__ == "__main__":
    unittest.main()
