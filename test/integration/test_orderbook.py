import unittest
from src.orderbook.orderbook import OrderBook
from src.orders.order import Order, OrderID, OrderSpec
from src.bookkeeping.custom_types import Side, OrderType, ExecutionRule
from src.bookkeeping.exceptions import DuplicateOrderError, InvalidOrderError
from src.orders.order_id_generator import OrderIdGenerator
from src.orderbook.book_side import BidSide, AskSide, BookSide


class OrderBookIntegrationBase(unittest.TestCase):
    def setUp(self):
        self.orderbook = OrderBook()
        self.generator = OrderIdGenerator()


class TestPosting(OrderBookIntegrationBase):
    def test_post_single_bid_creates_level(self):
        resting_order = _make_limit(self.generator, Side.BID, limit_price=99)
        self.assertTrue(self.orderbook.get_book_side(Side.BID).is_empty)
        self.orderbook.post_order(resting_order)
        self.assertFalse(self.orderbook.get_book_side(Side.BID).is_empty)

    def test_post_single_ask_creates_level(self):
        resting_order = _make_limit(self.generator, Side.ASK, limit_price=99)
        self.assertTrue(self.orderbook.get_book_side(Side.ASK).is_empty)
        self.orderbook.post_order(resting_order)
        self.assertFalse(self.orderbook.get_book_side(Side.ASK).is_empty)

    def test_post_multiple_same_price_same_side_preserves_fifo(self):
        resting1 = _make_limit(self.generator, Side.BID, limit_price=99)
        resting2 = _make_limit(self.generator, Side.BID, limit_price=99)
        resting3 = _make_limit(self.generator, Side.BID, limit_price=99)

        self.orderbook.post_order(resting1)
        self.orderbook.post_order(resting2)
        queue = self.orderbook.get_book_side(Side.BID).get_level(99)
        self.assertIs(resting1, queue.next_order_to_execute)
        self.orderbook.post_order(resting3)

        self.assertIs(resting1, queue.next_order_to_execute)

    def test_post_multiple_different_prices_orders_levels_correctly(self):
        resting = {
            99 - i: _make_limit(self.generator, side=Side.BID, limit_price=99 - i)
            for i in range(3)
        }
        for order in resting.values():
            self.orderbook.post_order(order)
        self.assertEqual(resting.keys(), self.orderbook.get_book_side(Side.BID).prices)

    def test_post_both_sides_leaves_uncrossed_book(self):
        resting1 = _make_limit(self.generator, Side.ASK, limit_price=100)
        resting2 = _make_limit(self.generator, Side.BID, limit_price=99)
        self.orderbook.post_order(resting1)
        self.orderbook.post_order(resting2)
        self.assertFalse(self.orderbook.get_book_side(Side.BID).is_empty)
        self.assertFalse(self.orderbook.get_book_side(Side.ASK).is_empty)
        self.assertGreater(
            self.orderbook.get_book_side(Side.ASK).best_price,
            self.orderbook.get_book_side(Side.BID).best_price,
        )

    def test_post_duplicate_id_raises_duplicate_error(self):
        resting = _make_limit(self.generator, Side.BID, limit_price=100)
        self.orderbook.post_order(resting)
        with self.assertRaises(DuplicateOrderError):
            self.orderbook.post_order(resting)

    def test_post_non_limit_raises_invalid_order_error(self):
        aggressor = _make_market(self.generator, Side.BID)
        with self.assertRaises(InvalidOrderError):
            self.orderbook.post_order(aggressor)

    def test_post_already_filled_raises_invalid_order_error(self):
        resting = _make_limit(self.generator, Side.BID, quantity=0, limit_price=100)
        with self.assertRaises(InvalidOrderError):
            self.orderbook.post_order(resting)

    def test_post_registers_in_order_index(self):
        resting = _make_limit(self.generator, Side.BID, limit_price=100)
        self.orderbook.post_order(resting)
        self.assertIn(resting.order_id, self.orderbook)
        self.assertEqual(
            (resting.side, resting.limit_price),
            self.orderbook._order_index[resting.order_id],
        )

    @unittest.skip("are invariants checks necessary, what to test")
    def test_post_many_orders_preserves_all_invariants(self): ...


class TestGetOrder(OrderBookIntegrationBase):
    def test_get_order_returns_same_instance_posted(self):
        resting = _make_limit(self.generator, Side.BID, limit_price=100)
        self.orderbook.post_order(resting)
        self.assertEqual(resting, self.orderbook.get_order(resting.order_id))

    def test_get_order_unknown_id_raises_invalid_order_error(self):
        with self.assertRaises(InvalidOrderError):
            self.orderbook.get_order(0)

    def test_get_order_on_bid_and_ask_both_resolve(self):
        resting_bid = _make_limit(self.generator, Side.BID, limit_price=99)
        resting_ask = _make_limit(self.generator, Side.ASK, limit_price=100)
        self.orderbook.post_order(resting_bid)
        self.orderbook.post_order(resting_ask)
        self.assertEqual(resting_bid, self.orderbook.get_order(resting_bid.order_id))
        self.assertEqual(resting_ask, self.orderbook.get_order(resting_ask.order_id))


class TestSideAccessors(OrderBookIntegrationBase):
    def test_get_book_side_bid_returns_bid_side_instance(self):
        self.assertIsInstance(self.orderbook.get_book_side(Side.BID), BidSide)

    def test_get_book_side_ask_returns_ask_side_instance(self):
        self.assertIsInstance(self.orderbook.get_book_side(Side.ASK), AskSide)

    def test_get_opposite_book_side_bid_returns_ask_side(self):
        self.assertIsInstance(self.orderbook.get_opposite_book_side(Side.BID), AskSide)

    def test_get_opposite_book_side_ask_returns_bid_side(self):
        self.assertIsInstance(self.orderbook.get_opposite_book_side(Side.ASK), BidSide)

    def test_get_book_side_invalid_type_raises(self):
        for invalid_type in (None, 1, BookSide, "BID"):
            with self.assertRaises(TypeError):
                self.orderbook.get_book_side(invalid_type)

    def test_get_opposite_book_side_invalid_type_raises(self):
        for invalid_type in (None, 1, BookSide, "BID"):
            with self.assertRaises(TypeError):
                self.orderbook.get_opposite_book_side(invalid_type)


class TestQueries(OrderBookIntegrationBase):
    def test_get_bid_ask_mid_raises_when_bid_side_empty(self):
        resting = _make_limit(self.generator, Side.ASK, limit_price=100)
        self.orderbook.post_order(resting)
        with self.assertRaises(RuntimeError):
            self.orderbook.get_bid_ask_mid()

    def test_get_bid_ask_mid_raises_when_ask_side_empty(self):
        resting = _make_limit(self.generator, Side.BID, limit_price=100)
        self.orderbook.post_order(resting)
        with self.assertRaises(RuntimeError):
            self.orderbook.get_bid_ask_mid()

    def test_get_bid_ask_mid_raises_when_both_empty(self):
        with self.assertRaises(RuntimeError):
            self.orderbook.get_bid_ask_mid()

    def test_get_bid_ask_mid_returns_correct_triple(self):
        resting_bid = _make_limit(self.generator, Side.BID, limit_price=99)
        self.orderbook.post_order(resting_bid)
        resting_ask = _make_limit(self.generator, Side.ASK, limit_price=101)
        self.orderbook.post_order(resting_ask)

        self.assertTupleEqual((99, 101, 100), self.orderbook.get_bid_ask_mid())

    def test_get_states_includes_every_level_on_both_sides(self):
        resting_bid_1 = _make_limit(self.generator, Side.BID, limit_price=99)
        resting_bid_2 = _make_limit(self.generator, Side.BID, limit_price=98)
        self.orderbook.post_order(resting_bid_1)
        self.orderbook.post_order(resting_bid_2)

        resting_ask_1 = _make_limit(self.generator, Side.ASK, limit_price=101)
        resting_ask_2 = _make_limit(self.generator, Side.ASK, limit_price=102)
        self.orderbook.post_order(resting_ask_1)
        self.orderbook.post_order(resting_ask_2)

        bid_states, ask_states = self.orderbook.get_states()
        self.assertListEqual(list(bid_states), [98, 99])
        self.assertListEqual(list(ask_states), [101, 102])

    def test_get_states_empty_book_returns_empty_dicts(self):
        self.assertTupleEqual(self.orderbook.get_states(), ({}, {}))

    def test_get_top_state_only_contains_best_level(self):
        resting_bid_1 = _make_limit(self.generator, Side.BID, limit_price=99)
        resting_bid_2 = _make_limit(self.generator, Side.BID, limit_price=98)
        self.orderbook.post_order(resting_bid_1)
        self.orderbook.post_order(resting_bid_2)

        resting_ask_1 = _make_limit(self.generator, Side.ASK, limit_price=101)
        resting_ask_2 = _make_limit(self.generator, Side.ASK, limit_price=102)
        self.orderbook.post_order(resting_ask_1)
        self.orderbook.post_order(resting_ask_2)
        bid_state, ask_state = self.orderbook.get_top_state()
        self.assertListEqual(
            list(bid_state), [self.orderbook.get_book_side(Side.BID).best_price]
        )
        self.assertListEqual(
            list(ask_state), [self.orderbook.get_book_side(Side.ASK).best_price]
        )

    def test_get_top_state_empty_side_returns_empty_dict(self):
        self.assertTupleEqual(self.orderbook.get_top_state(), ({}, {}))

    def test_get_volumes_sums_per_level_correctly(self):

        self.orderbook.post_order(
            _make_limit(self.generator, Side.BID, limit_price=99, quantity=5)
        )
        self.orderbook.post_order(
            _make_limit(self.generator, Side.BID, limit_price=99, quantity=3)
        )
        self.orderbook.post_order(
            _make_limit(self.generator, Side.BID, limit_price=98, quantity=7)
        )

        self.orderbook.post_order(
            _make_limit(self.generator, Side.ASK, limit_price=101, quantity=4)
        )
        self.orderbook.post_order(
            _make_limit(self.generator, Side.ASK, limit_price=102, quantity=6)
        )
        self.orderbook.post_order(
            _make_limit(self.generator, Side.ASK, limit_price=102, quantity=2)
        )

        bid_volumes, ask_volumes = self.orderbook.get_volumes()

        self.assertEqual(bid_volumes, {99: 8, 98: 7})
        self.assertEqual(ask_volumes, {101: 4, 102: 8})

        def test_queries_match_direct_inspection(self): ...


class TestPriceTimePriorityStructural(OrderBookIntegrationBase):
    """
    Without matching or cancel, we can only verify the STRUCTURAL half of
    price-time priority: that posts land in the right level and in the
    right FIFO position. The behavioural half (who gets filled first)
    is tested in test_order_execution.py.
    """

    def test_posts_at_same_price_queue_in_post_order(self):
        resting1 = _make_limit(self.generator, Side.ASK, limit_price=100)
        self.orderbook.post_order(resting1)
        resting2 = _make_limit(self.generator, Side.ASK, limit_price=100)
        self.orderbook.post_order(resting2)

        self.assertIn(
            resting2.order_id, self.orderbook.get_book_side(Side.ASK).get_level(100)
        )

    def test_new_post_joins_tail_of_existing_level(self):
        resting1 = _make_limit(self.generator, Side.ASK, limit_price=100)
        self.orderbook.post_order(resting1)
        resting2 = _make_limit(self.generator, Side.ASK, limit_price=100)
        self.orderbook.post_order(resting2)
        resting3 = _make_limit(self.generator, Side.ASK, limit_price=100)
        self.orderbook.post_order(resting3)

        self.assertIs(
            resting3, self.orderbook.get_book_side(Side.ASK).get_level(100).tail
        )

    def test_best_bid_is_highest_posted_price(self):
        resting1 = _make_limit(self.generator, Side.BID, limit_price=99)
        self.orderbook.post_order(resting1)
        resting2 = _make_limit(self.generator, Side.BID, limit_price=98)
        self.orderbook.post_order(resting2)
        resting3 = _make_limit(self.generator, Side.BID, limit_price=97)
        self.orderbook.post_order(resting3)
        orders_best_price = max(
            resting1.limit_price, resting2.limit_price, resting3.limit_price
        )
        self.assertEqual(
            self.orderbook.get_book_side(Side.BID).best_price, orders_best_price
        )

    def test_best_ask_is_lowest_posted_price(self):
        resting1 = _make_limit(self.generator, Side.ASK, limit_price=100)
        self.orderbook.post_order(resting1)
        resting2 = _make_limit(self.generator, Side.ASK, limit_price=101)
        self.orderbook.post_order(resting2)
        resting3 = _make_limit(self.generator, Side.ASK, limit_price=102)
        self.orderbook.post_order(resting3)

        orders_best_price = min(
            resting1.limit_price, resting2.limit_price, resting3.limit_price
        )
        self.assertEqual(
            self.orderbook.get_book_side(Side.ASK).best_price, orders_best_price
        )


@unittest.skip("wait until implementation")
class TestCancel(OrderBookIntegrationBase):
    def test_cancel_removes_from_book_and_index(self): ...


class TestFillTop(OrderBookIntegrationBase):
    # ----------------------------------------------------------------------------------
    # single-level
    # ----------------------------------------------------------------------------------

    def test_aggressor_fully_consumes_single_resting_at_one_level(self):

        resting = _make_limit(self.generator, Side.BID, limit_price=100, quantity=100)
        self.orderbook.post_order(resting)

        aggressor = _make_market(self.generator, Side.ASK, quantity=200)

        payloads = self.orderbook.fill_top(aggressor)

        self.assertTrue(resting.is_filled)
        self.assertTrue(self.orderbook.bid_side.is_empty)
        self.assertNotIn(resting.order_id, self.orderbook)

        self.assertFalse(aggressor.is_filled)

        self.assertEqual(len(payloads), 1)
        self.assertEqual(aggressor.remaining_quantity, 100)

    def test_aggressor_partially_consumes_single_resting(self):

        resting = _make_limit(self.generator, Side.BID, limit_price=100, quantity=1000)
        self.orderbook.post_order(resting)

        aggressor = _make_market(self.generator, Side.ASK, quantity=100)

        payloads = self.orderbook.fill_top(aggressor)

        self.assertTrue(aggressor.is_filled)
        self.assertFalse(resting.is_filled)
        self.assertFalse(self.orderbook.bid_side.is_empty)
        self.assertFalse(self.orderbook.bid_side.top_level.is_empty)
        self.assertIn(resting.order_id, self.orderbook)
        self.assertIn(resting.order_id, self.orderbook.bid_side.top_level)
        self.assertEqual(len(payloads), 1)

    def test_aggressor_consumes_multiple_resting_at_same_level_fifo(self):

        resting1 = _make_limit(self.generator, Side.BID, limit_price=100, quantity=100)
        resting2 = _make_limit(self.generator, Side.BID, limit_price=100, quantity=200)
        resting3 = _make_limit(self.generator, Side.BID, limit_price=100, quantity=100)

        aggressor = _make_market(self.generator, Side.ASK, quantity=200)

        self.orderbook.post_order(resting1)
        self.orderbook.post_order(resting2)
        payloads = self.orderbook.fill_top(aggressor)

        self.assertTrue(aggressor.is_filled)

        self.assertTrue(resting1.is_filled)
        self.assertNotIn(resting1.order_id, self.orderbook)

        self.assertFalse(resting2.is_filled)
        self.assertIn(resting2.order_id, self.orderbook)
        self.assertEqual(resting2.remaining_quantity, 100)
        self.assertIs(self.orderbook.bid_side.top_level.next_order_to_execute, resting2)

        self.assertEqual(resting3.initial_quantity, resting3.remaining_quantity)

        self.assertEqual(len(payloads), 2)

    def test_aggressor_larger_than_level_stops_at_exhaustion(self):
        resting_orders = [
            _make_limit(self.generator, Side.BID, limit_price=100, quantity=100)
            for _ in range(5)
        ]

        aggressor = _make_limit(self.generator, Side.ASK, limit_price=99, quantity=1000)

        for order in resting_orders:
            self.orderbook.post_order(order)

        top_level = self.orderbook.bid_side.top_level

        payloads = self.orderbook.fill_top(aggressor)

        self.assertFalse(aggressor.is_filled)

        for order in resting_orders:
            self.assertTrue(order.is_filled)
            self.assertNotIn(order.order_id, self.orderbook)

        self.assertEqual(len(payloads), len(resting_orders))
        self.assertTrue(top_level.is_empty)

        self.assertEqual(aggressor.remaining_quantity, 500)
        self.assertNotIn(aggressor.order_id, self.orderbook)
        self.assertEqual(len(payloads), 5)

    # ----------------------------------------------------------------------------------
    # multiple-levels
    # ----------------------------------------------------------------------------------
    def test_fill_top_only_consumes_top_level_not_lower(self):
        resting_orders_top_level = [
            _make_limit(self.generator, Side.BID, limit_price=100, quantity=100)
            for _ in range(5)
        ]

        resting_sublevel = _make_limit(
            self.generator, Side.BID, limit_price=99, quantity=100
        )

        aggressor = _make_limit(self.generator, Side.ASK, limit_price=99, quantity=1000)

        for order in resting_orders_top_level:
            self.orderbook.post_order(order)
        self.orderbook.post_order(resting_sublevel)

        initial_top_level = self.orderbook.bid_side.top_level

        payloads = self.orderbook.fill_top(aggressor)

        self.assertFalse(aggressor.is_filled)

        for order in resting_orders_top_level:
            self.assertTrue(order.is_filled)
            self.assertNotIn(order.order_id, self.orderbook)

        self.assertEqual(len(payloads), len(resting_orders_top_level))
        self.assertTrue(initial_top_level.is_empty)
        self.assertIsNot(self.orderbook.bid_side.top_level, initial_top_level)

        self.assertEqual(aggressor.remaining_quantity, 500)
        self.assertNotIn(aggressor.order_id, self.orderbook)

        self.assertEqual(
            resting_sublevel.initial_quantity, resting_sublevel.remaining_quantity
        )
        self.assertEqual(len(payloads), 5)

    def test_consecutive_fill_top_calls_walk_down_bids(self):

        aggressor = _make_limit(self.generator, Side.ASK, limit_price=0, quantity=1000)
        # build 3 layers of 5 orders

        resting_orders = [
            [
                _make_limit(self.generator, Side.BID, limit_price=100 - i, quantity=100)
                for _ in range(5)
            ]
            for i in range(3)
        ]

        levels = []

        # post orders and get the three levels in order
        for same_price_orders in resting_orders:
            for order in same_price_orders:
                self.orderbook.post_order(order)

            levels.append(self.orderbook.bid_side.get_level(order.limit_price))

        # fill top layer
        payloads_top = self.orderbook.fill_top(aggressor)

        self.assertFalse(aggressor.is_filled)
        self.assertIsNot(levels[0], self.orderbook.bid_side.top_level)

        for order in resting_orders[0]:
            self.assertTrue(order.is_filled)
            self.assertNotIn(order.order_id, self.orderbook)

        self.assertEqual(len(payloads_top), 5)

        payloads_second = self.orderbook.fill_top(aggressor)

        self.assertTrue(aggressor.is_filled)
        self.assertIsNot(levels[1], self.orderbook.bid_side.top_level)

        for order in resting_orders[1]:
            self.assertTrue(order.is_filled)
            self.assertNotIn(order.order_id, self.orderbook)

        self.assertEqual(len(payloads_second), 5)

        payloads_third = self.orderbook.fill_top(aggressor)
        self.assertListEqual(payloads_third, [])
        self.assertIs(levels[2], self.orderbook.bid_side.top_level)

        for order in resting_orders[2]:
            self.assertFalse(order.is_filled)
            self.assertIn(order.order_id, self.orderbook)

    def test_consecutive_fill_top_calls_walks_up_asks(self):

        aggressor = _make_limit(
            self.generator, Side.BID, limit_price=200, quantity=1000
        )
        # build 3 layers of 5 orders

        resting_orders = [
            [
                _make_limit(self.generator, Side.ASK, limit_price=100 + i, quantity=100)
                for _ in range(5)
            ]
            for i in range(3)
        ]

        levels = []

        # post orders and get the three levels in order
        for same_price_orders in resting_orders:
            for order in same_price_orders:
                self.orderbook.post_order(order)

            levels.append(self.orderbook.ask_side.get_level(order.limit_price))

        # fill top layer
        payloads_top = self.orderbook.fill_top(aggressor)

        self.assertFalse(aggressor.is_filled)
        self.assertIsNot(levels[0], self.orderbook.ask_side.top_level)

        for order in resting_orders[0]:
            self.assertTrue(order.is_filled)
            self.assertNotIn(order.order_id, self.orderbook)

        self.assertEqual(len(payloads_top), 5)

        payloads_second = self.orderbook.fill_top(aggressor)

        self.assertTrue(aggressor.is_filled)
        self.assertIsNot(levels[1], self.orderbook.ask_side.top_level)

        for order in resting_orders[1]:
            self.assertTrue(order.is_filled)
            self.assertNotIn(order.order_id, self.orderbook)

        self.assertEqual(len(payloads_second), 5)

        payloads_third = self.orderbook.fill_top(aggressor)
        self.assertListEqual(payloads_third, [])
        self.assertIs(levels[2], self.orderbook.ask_side.top_level)

        for order in resting_orders[2]:
            self.assertFalse(order.is_filled)
            self.assertIn(order.order_id, self.orderbook)


def _make_limit(
    generator: OrderIdGenerator,
    side: Side,
    limit_price: int,
    quantity: int = 100,
    execution_rule: ExecutionRule = ExecutionRule.GTC,
) -> Order:
    spec = OrderSpec(
        side=side,
        order_type=OrderType.LIMIT,
        quantity=quantity,
        limit_price=limit_price,
        execution_rule=execution_rule,
    )
    id_ = OrderID(generator.next_id(), 0)

    return Order(spec, id_)


def _make_market(
    generator: OrderIdGenerator,
    side: Side,
    quantity: int = 100,
) -> Order:
    spec = OrderSpec(side=side, order_type=OrderType.MARKET, quantity=quantity)
    id_ = OrderID(generator.next_id(), 0)

    return Order(spec, id_)


if __name__ == "__main__":
    unittest.main()
