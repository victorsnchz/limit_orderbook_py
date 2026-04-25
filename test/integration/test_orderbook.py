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
        self.assertIn(resting.order_id, self.orderbook._order_index)
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


class TestMatching(OrderBookIntegrationBase): ...


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
