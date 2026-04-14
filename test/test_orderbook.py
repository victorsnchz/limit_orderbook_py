import unittest
import sys

sys.path.append("src")

from src.orderbook.orderbook import OrderBook
from src.orders.order import Order, OrderID, OrderSpec
from src.bookkeeping.custom_types import (
    Side,
    ExecutionRule,
    OrderType,
    LevelState,
    FilledOrder,
)
from src.orderbook.book_side import BidSide, AskSide
from src.orderbook.orders_queue import OrdersQueue
from src.orderbook.order_execution import LimitOrderExecution
from src.orders.order_id_generator import OrderIdGenerator
# blend of unit-testing and integration testing


class TestOrderBookRouting(unittest.TestCase):
    def setUp(self):
        self.orderbook = OrderBook()

    def test_get_book_side_returns_bid_side(self):
        side = self.orderbook.get_book_side(Side.BID)
        self.assertIsInstance(side, BidSide)

    def test_get_book_side_returns_ask_side(self):
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
        self.generator = OrderIdGenerator()

    def test_get_bid_ask_mid(self):
        resting_bid = _post_order(
            self.generator, self.orderbook, Side.BID, price=99, quantity=100
        )
        resting_ask = _post_order(
            self.generator, self.orderbook, Side.ASK, price=100, quantity=100
        )

        bid, ask, mid = self.orderbook.get_bid_ask_mid()

        self.assertEqual(bid, resting_bid.limit_price)
        self.assertEqual(ask, resting_ask.limit_price)
        self.assertEqual(mid, (resting_bid.limit_price + resting_ask.limit_price) / 2)

    def test_get_bid_ask_mid_empty_book_raises(self):
        with self.assertRaises(RuntimeError):
            self.orderbook.get_bid_ask_mid()

    def test_get_bid_ask_mid_no_bids_raises(self):
        _post_order(self.generator, self.orderbook, Side.ASK, price=100, quantity=100)
        with self.assertRaises(RuntimeError):
            self.orderbook.get_bid_ask_mid()

    def test_get_bid_ask_mid_no_asks_raises(self):
        _post_order(self.generator, self.orderbook, Side.BID, price=100, quantity=100)
        with self.assertRaises(RuntimeError):
            self.orderbook.get_bid_ask_mid()


class TestOrderBookStates(unittest.TestCase):
    def setUp(self):
        self.orderbook = _build_book(100, 0.5, quantity=100, depth=2)

    def test_get_states_returns_tuple_of_two_dicts(self):
        result = self.orderbook.get_states()
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        for state in result:
            self.assertIsInstance(state, dict)

    def test_get_states_returns_level_state(self):
        bids, asks = self.orderbook.get_states()
        for bid_state, ask_state in zip(bids.values(), asks.values()):
            self.assertIsInstance(bid_state, LevelState)
            self.assertIsInstance(ask_state, LevelState)

    def get_states_first_element_is_bids(self):
        bids, _ = self.orderbook.get_states()
        for price in bids:
            self.assertIn(price, self.orderbook.bid_side.levels)

    def get_states_second_element_is_asks(self):
        _, asks = self.orderbook.get_states()
        for price in asks:
            self.assertIn(price, self.orderbook.ask_side.levels)

    @unittest.skip("refactor to return empty dict")
    def test_get_states_empty_book_raises(self):
        empty = OrderBook()
        with self.assertRaises(IndexError):
            empty.get_states()

    def test_get_top_state_returns_tuple_of_two_dicts(self):
        result = self.orderbook.get_top_state()
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        for state in result:
            self.assertIsInstance(state, dict)

    def test_get_top_state_returns_level_state(self):
        bid_state, ask_state = self.orderbook.get_top_state()
        self.assertIsInstance(next(iter(bid_state.values())), LevelState)
        self.assertIsInstance(next(iter(ask_state.values())), LevelState)

    def test_get_top_state_returns_one_level_each_side(self):

        bids, asks = self.orderbook.get_top_state()

        self.assertEqual(len(bids), 1)
        self.assertEqual(len(asks), 1)

    def test_get_top_state_bid_is_highest(self):
        bids, _ = self.orderbook.get_top_state()
        all_bid_prices = list(self.orderbook.bid_side.levels.keys())
        self.assertIn(max(all_bid_prices), bids)

    def test_get_top_state_ask_is_lowest(self):
        _, asks = self.orderbook.get_top_state()
        all_ask_prices = list(self.orderbook.ask_side.levels.keys())
        self.assertIn(min(all_ask_prices), asks)


class TestOrderBookGetVolumes(unittest.TestCase):
    def setUp(self):
        self.orderbook = _build_book(100, 0.5, 100, 2)

    def test_get_volumes_returns_tuple_of_two_of_dicts(self):
        result = self.orderbook.get_volumes()
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        for state in result:
            self.assertIsInstance(state, dict)

    def test_get_volumes_empty_book_returns_empty_dicts(self):
        bid_vols, ask_vols = OrderBook().get_volumes()
        self.assertEqual(bid_vols, {})
        self.assertEqual(ask_vols, {})


class TestFillTop(unittest.TestCase):
    def setUp(self):
        self.orderbook = OrderBook()
        self.generator = OrderIdGenerator()

    def test_returns_empty_lsit_when_incoming_already_filled(self):
        _post_order(self.generator, self.orderbook, Side.ASK, price=99, quantity=100)
        incoming = _make_limit_order(self.generator, Side.BID, price=99, quantity=100)
        incoming.fill(100)

        result = self.orderbook.fill_top(incoming)
        self.assertEqual(result, [])

    def test_single_resting_exact_match_returns_one_filled_order(self):
        resting = _post_order(
            self.generator, self.orderbook, Side.ASK, price=99, quantity=100
        )
        incoming = _make_limit_order(self.generator, Side.BID, price=99, quantity=100)
        result = self.orderbook.fill_top(incoming)

        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], FilledOrder)

    def test_sweep_two_resting_orders_returns_two_filled_orders(self):
        resting1 = _post_order(
            self.generator, self.orderbook, Side.ASK, price=99, quantity=50
        )
        resting2 = _post_order(
            self.generator, self.orderbook, Side.ASK, price=99, quantity=50
        )
        incoming = _make_limit_order(self.generator, Side.BID, price=99, quantity=100)

        result = self.orderbook.fill_top(incoming)

        self.assertEqual(len(result), 2)

    def test_filled_qty_exact_match(self):
        resting = _post_order(
            self.generator, self.orderbook, Side.ASK, price=99, quantity=100
        )
        incoming = _make_limit_order(self.generator, Side.BID, price=99, quantity=100)
        result = self.orderbook.fill_top(incoming)
        self.assertEqual(result[0].filled_qty, resting.initial_quantity)

    def test_filled_qty_when_incoming_smaller_than_resting(self):
        resting = _post_order(
            self.generator, self.orderbook, Side.BID, price=100, quantity=100
        )
        incoming = _make_limit_order(self.generator, Side.ASK, price=100, quantity=40)
        result = self.orderbook.fill_top(incoming)
        self.assertEqual(len(result), 1)
        self.assertEqual(
            result[0].filled_qty, resting.initial_quantity - resting.remaining_quantity
        )

    def test_filled_qty_when_resting_smaller_than_incoming(self):
        resting = _post_order(
            self.generator, self.orderbook, Side.BID, quantity=40, price=100
        )
        incoming = _make_limit_order(self.generator, Side.ASK, quantity=100, price=100)
        result = self.orderbook.fill_top(incoming)
        self.assertEqual(len(result), 1)
        self.assertEqual(
            result[0].filled_qty,
            incoming.initial_quantity - incoming.remaining_quantity,
        )

    def test_fill_qtys_sum_to_total_consumed_accross_sweep(self):

        resting1 = _post_order(
            self.generator, self.orderbook, Side.BID, quantity=50, price=100
        )
        resting2 = _post_order(
            self.generator, self.orderbook, Side.BID, quantity=100, price=100
        )

        incoming = _make_limit_order(self.generator, Side.ASK, quantity=100, price=100)
        result = self.orderbook.fill_top(incoming)

        self.assertEqual(
            sum(filled_order.filled_qty for filled_order in result),
            incoming.initial_quantity - incoming.remaining_quantity,
        )


def _make_limit_order(
    generator: OrderIdGenerator, side: Side, price: int, quantity: int
) -> Order:
    spec = OrderSpec(side, OrderType.LIMIT, quantity, price, ExecutionRule.GTC)
    return Order(spec, OrderID(generator.next_id(), 0))


def _build_book(mid: float, half_spread: float, quantity: int, depth: int) -> OrderBook:
    orderbook = OrderBook()
    generator = OrderIdGenerator()
    for i in range(1, depth + 1):
        resting_bid = _make_limit_order(
            generator, Side.BID, price=mid - i * half_spread, quantity=quantity
        )
        resting_ask = _make_limit_order(
            generator, Side.ASK, price=mid + i * half_spread, quantity=quantity
        )

        LimitOrderExecution(resting_bid, orderbook)._post_order()
        LimitOrderExecution(resting_ask, orderbook)._post_order()
    return orderbook


def _queue_at(orderbook, side: Side, price: int) -> OrdersQueue:
    return orderbook.get_book_side(side).levels[price]


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


if __name__ == "__main__":
    unittest.main()
