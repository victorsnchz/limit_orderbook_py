import unittest
from unittest.mock import MagicMock, PropertyMock
from src.orderbook.orderbook import OrderBook
from src.orders.order import Order, OrderID, OrderSpec, OrderSnapshot
from src.orders.order_id_generator import OrderIdGenerator
from src.orderbook.orders_queue import OrdersQueue
from src.bookkeeping.custom_types import Side, OrderType, FilledPayload
from src.bookkeeping.exceptions import InvalidOrderError, DuplicateOrderError
from src.orderbook.book_side import BookSide
from src.orderbook.orders_queue import OrdersQueue
from dataclasses import replace


class OrderbookBase(unittest.TestCase):
    def setUp(self):
        self.orderbook = OrderBook()
        self.orderbook.bid_side = MagicMock(spec=BookSide)
        self.orderbook.ask_side = MagicMock(spec=BookSide)


class TestPostOrder(OrderbookBase):
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

        self.assertNotIn(order.order_id, self.orderbook)

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
        self.assertNotIn(order.order_id, self.orderbook)

    def test_post_bid_crosses_ask_raises(self):
        order = _make_limit_order(side=Side.BID, limit_price=100)

        self.orderbook.ask_side.best_price = 99
        self.orderbook.ask_side.is_empty = False

        with self.assertRaises(InvalidOrderError):
            self.orderbook.post_order(order)

    def test_post_ask_crosses_bid_raises(self):
        order = _make_limit_order(side=Side.ASK, limit_price=99)

        self.orderbook.bid_side.best_price = 100
        self.orderbook.bid_side.is_empty = False

        with self.assertRaises(InvalidOrderError):
            self.orderbook.post_order(order)


class TestOrderbookInvariants(OrderbookBase):
    def test_contains_returns_true_id_in_index(self):
        self.orderbook._order_index[0] = ()
        self.assertIn(0, self.orderbook)

    def test_contains_returns_false_not_in_index(self):
        self.orderbook._order_index[0] = ()
        self.assertNotIn(1, self.orderbook)

    def test_contains_returns_false_empty_book(self):
        self.assertNotIn(0, self.orderbook)


class TestOrderBookBidAskMid(OrderbookBase):
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


class TestGetBookSide(OrderbookBase):
    def test_bid_returns_bid_side(self):
        self.assertIs(self.orderbook.get_book_side(Side.BID), self.orderbook.bid_side)

    def test_ask_returns_bid_side(self):
        self.assertIs(self.orderbook.get_book_side(Side.ASK), self.orderbook.ask_side)

    def test_invalid_type_raises(self):
        for bad_input in ("BID", 1, None):
            with self.subTest(value=bad_input):
                with self.assertRaises(TypeError):
                    self.orderbook.get_book_side(bad_input)


class TestGetOppositeBookSide(OrderbookBase):
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


class TestGetStates(OrderbookBase):
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


class TestGetTopState(OrderbookBase):
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


class TestGetVolumes(OrderbookBase):
    def test_returns_bid_then_ask(self):
        sentinel_bid = object()
        sentinel_ask = object()
        self.orderbook.bid_side.get_volumes.return_value = sentinel_bid
        self.orderbook.ask_side.get_volumes.return_value = sentinel_ask
        bids, asks = self.orderbook.get_volumes()
        self.assertIs(bids, sentinel_bid)
        self.assertIs(asks, sentinel_ask)


class TestFillTop(OrderbookBase):
    """
    TestFillTop using Order and OrdersQueue instead of mocks.
    Only BookSide mocked: class with most non-trivial logic.

    OrderbookBase.setUp provides:
        self.orderbook.bid_side = MagicMock(spec=BookSide)
        self.orderbook.ask_side = MagicMock(spec=BookSide)

    Per-test typical setup:
        - build real resting orders via self._make_limit_order
        - add to real OrdersQueue self.queue
        - confifure mocked opposite BookSide:
            - opposite.top_level = self.queue
            - opposite.is_empty = False
            - opposite.best_price = <price used by resting>
        - pre-populate self.orderbook._order_index for each resting id (so del inside
         fill does not raise a KeyError)
    """

    def setUp(self):
        super().setUp()

        self.bid_empty_prop = PropertyMock(return_value=False)
        type(self.orderbook.bid_side).is_empty = self.bid_empty_prop
        type(self.orderbook.bid_side).top_level = OrdersQueue()
        type(self.orderbook.bid_side).best_price = 100
        self.orderbook.bid_side.delete_level = PropertyMock()

        self.ask_empty_prop = PropertyMock(return_value=True)
        type(self.orderbook.ask_side).is_empty = self.ask_empty_prop

        self.generator = OrderIdGenerator()

    def _make_limit_order(
        self,
        side: Side,
        limit_price: int = 100,
        initial_quantity: int = 100,
        remaining_quantity: int = 100,
    ):
        if remaining_quantity < 0:
            raise ValueError(f"remaining_quantity must be strictly positive")
        if remaining_quantity > initial_quantity:
            raise ValueError(
                "remaining quantity must be less than or equal to initial quantity"
            )

        if remaining_quantity < initial_quantity:
            initial_quantity = remaining_quantity

        spec = OrderSpec(
            side=side,
            order_type=OrderType.LIMIT,
            quantity=initial_quantity,
            limit_price=limit_price,
        )

        id_ = OrderID(self.generator.next_id(), 0)

        return Order(spec, id_)

    def _make_market_order(
        self,
        side: Side,
        initial_quantity: int = 100,
        remaining_quantity: int = 100,
    ):
        if remaining_quantity < 0:
            raise ValueError(f"remaining_quantity must be strictly positive")
        if remaining_quantity > initial_quantity:
            raise ValueError(
                "remaining quantity must be less than or equal to initial quantity"
            )

        if remaining_quantity < initial_quantity:
            initial_quantity = remaining_quantity

        spec = OrderSpec(
            side=side,
            order_type=OrderType.MARKET,
            quantity=initial_quantity,
        )

        id_ = OrderID(self.generator.next_id(), 0)

        return Order(spec, id_)

    # test core matching loop
    def test_fill_top_queries_opposite_side(self):

        aggressor = self._make_market_order(Side.BID, remaining_quantity=0)
        self.orderbook.fill_top(aggressor)
        self.ask_empty_prop.assert_called_once()
        self.bid_empty_prop.assert_not_called()

    def test_fill_top_consumes_top_level(self):
        # TODO
        # make limit price dependent on mock book top price somehow instead of magic
        # number
        resting1 = self._make_limit_order(
            Side.BID, limit_price=100, initial_quantity=100, remaining_quantity=100
        )
        resting2 = self._make_limit_order(
            Side.BID, limit_price=100, initial_quantity=100, remaining_quantity=100
        )
        self.orderbook.bid_side.top_level.add_order(resting1)
        self.orderbook.bid_side.top_level.add_order(resting2)
        self.orderbook._order_index[resting1.order_id] = (
            resting1.side,
            resting1.limit_price,
        )
        self.orderbook._order_index[resting2.order_id] = (
            resting2.side,
            resting2.limit_price,
        )

        aggressor = self._make_market_order(
            side=Side.ASK, initial_quantity=250, remaining_quantity=250
        )

        self.assertFalse(self.orderbook.bid_side.top_level.is_empty)
        self.orderbook.fill_top(aggressor)

        self.assertTrue(self.orderbook.bid_side.top_level.is_empty)

    def test_fill_top_consumes_multiple_resting_until_aggressor_filled(self):
        resting = [
            self._make_limit_order(Side.BID, limit_price=100, initial_quantity=100)
            for _ in range(5)
        ]

        for order in resting:
            self.orderbook.bid_side.top_level.add_order(order)
            self.orderbook._order_index[order.order_id] = (
                order.side,
                order.limit_price,
            )

        aggressor = self._make_market_order(
            side=Side.ASK, initial_quantity=250, remaining_quantity=250
        )

        self.assertFalse(aggressor.is_filled)
        self.orderbook.fill_top(aggressor)
        self.assertTrue(aggressor.is_filled)
        self.assertFalse(self.orderbook.bid_side.top_level.is_empty)

    def test_fill_top_returns_filled_payloads_with_correct_content(self):

        resting = [
            self._make_limit_order(Side.BID, limit_price=100, initial_quantity=100)
            for _ in range(3)
        ]
        aggressor = self._make_market_order(
            side=Side.ASK, initial_quantity=300, remaining_quantity=300
        )

        target_payloads = []
        for i, order in enumerate(resting):
            snapshot_resting = order.snapshot()
            snapshot_aggressor = aggressor.snapshot()
            aggressor_remaining = aggressor.initial_quantity - 100 * i
            snapshot_aggressor = replace(
                snapshot_aggressor, remaining_quantity=aggressor_remaining
            )
            target_payloads.append(
                FilledPayload(snapshot_aggressor, snapshot_resting, filled_qty=100)
            )

            self.orderbook.bid_side.top_level.add_order(order)
            self.orderbook._order_index[order.order_id] = (
                order.side,
                order.limit_price,
            )
        returned_payloads = self.orderbook.fill_top(aggressor)

        for target_payload, returned_paylaod in zip(target_payloads, returned_payloads):
            self.assertEqual(target_payload, returned_paylaod)

    # book-state invariants (D9)
    def test_fill_top_removes_fully_filled_resting_from_index(self):

        resting = self._make_limit_order(
            Side.BID, limit_price=100, initial_quantity=100
        )
        aggressor = self._make_market_order(
            side=Side.ASK, initial_quantity=200, remaining_quantity=200
        )

        self.orderbook.bid_side.top_level.add_order(resting)
        self.orderbook._order_index[resting.order_id] = (
            resting.side,
            resting.limit_price,
        )

        self.orderbook.fill_top(aggressor)
        self.assertNotIn(resting.order_id, self.orderbook)
        self.assertNotIn(resting.order_id, self.orderbook.bid_side.top_level)

    def test_fill_top_preserves_partially_filled_resting_in_index(self):
        resting = self._make_limit_order(
            Side.BID, limit_price=100, initial_quantity=300, remaining_quantity=300
        )
        aggressor = self._make_market_order(side=Side.ASK, initial_quantity=100)

        self.orderbook.bid_side.top_level.add_order(resting)
        self.orderbook._order_index[resting.order_id] = (
            resting.side,
            resting.limit_price,
        )

        self.orderbook.fill_top(aggressor)

        self.assertIn(resting.order_id, self.orderbook)
        self.assertIn(resting.order_id, self.orderbook.bid_side.top_level)

    def test_fill_top_calls_delete_level_when_queue_empties(self):
        resting = self._make_limit_order(
            Side.BID, limit_price=100, initial_quantity=100
        )
        aggressor = self._make_market_order(
            side=Side.ASK, initial_quantity=200, remaining_quantity=200
        )

        self.orderbook.bid_side.top_level.add_order(resting)
        self.orderbook._order_index[resting.order_id] = (
            resting.side,
            resting.limit_price,
        )

        self.orderbook.fill_top(aggressor)
        self.orderbook.bid_side.delete_level.assert_called_once_with(
            resting.limit_price
        )

    # degenerate inputs
    def test_fill_top_no_op_on_empty_opposite_side(self):
        type(self.orderbook.bid_side).is_empty = PropertyMock(return_value=True)
        aggressor = self._make_market_order(
            side=Side.ASK, initial_quantity=200, remaining_quantity=200
        )

        result = self.orderbook.fill_top(aggressor)

        self.assertListEqual(result, [])
        self.assertTrue(self.orderbook.bid_side.top_level.is_empty)
        self.orderbook.bid_side.delete_level.assert_not_called()
        self.assertEqual(aggressor.initial_quantity, aggressor.remaining_quantity)

    def test_fill_top_no_op_when_aggressor_already_filled(self):

        aggressor = self._make_market_order(
            side=Side.ASK, initial_quantity=200, remaining_quantity=0
        )

        resting = self._make_limit_order(
            Side.BID, limit_price=100, initial_quantity=300, remaining_quantity=300
        )
        self.orderbook.bid_side.top_level.add_order(resting)
        self.orderbook._order_index[resting.order_id] = ()

        result = self.orderbook.fill_top(aggressor)

        self.assertListEqual(result, [])
        self.assertIn(resting.order_id, self.orderbook)
        self.assertIn(resting.order_id, self.orderbook.bid_side.top_level)
        self.orderbook.bid_side.delete_level.assert_not_called()


class TestGetOrder(OrderbookBase):
    def test_unknown_order_raises(self):
        with self.assertRaises(InvalidOrderError):
            self.orderbook.get_order(0)

    def test_retrieves_from_correct_side_and_level(self):
        sentinel_order = object()
        self.orderbook._order_index[0] = (Side.BID, 99)

        self.orderbook.bid_side = MagicMock()
        self.orderbook.bid_side.get_order.return_value = sentinel_order

        self.assertIs(self.orderbook.get_order(0), sentinel_order)
        self.orderbook.bid_side.get_order.assert_called_with(99, 0)

    def test_does_not_touch_opposite_side(self):
        self.orderbook._order_index[1] = (Side.ASK, 100)
        self.orderbook.ask_side = MagicMock()
        self.orderbook.get_order(1)
        self.orderbook.bid_side.assert_not_called()


def _make_limit_order(
    order_id=1,
    side: Side = Side.BID,
    limit_price: int = 100,
    quantity=100,
    is_filled=False,
):

    order = MagicMock(spec=Order)
    order.order_id = order_id
    order.side = side
    order.order_type = OrderType.LIMIT
    order.limit_price = limit_price
    order.remaining_quantity = quantity
    order.is_filled = is_filled

    return order


def _make_market_order(
    order_id=1,
    side: Side = Side.BID,
    quantity=100,
    is_filled=False,
):

    order = MagicMock(spec=Order)
    order.order_id = order_id
    order.side = side
    order.order_type = OrderType.MARKET
    order.remaining_quantity = quantity
    order.is_filled = is_filled

    return order


if __name__ == "__main__":
    unittest.main()
