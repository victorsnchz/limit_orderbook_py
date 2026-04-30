import unittest
from lob.orderbook.orderbook import OrderBook
from lob.orderbook.order_execution import (
    LimitOrderExecution,
    MarketOrderExecution,
    execute_order,
)
from lob.orders.order import Order, OrderID, OrderSpec
from lob.orders.order_id_generator import OrderIdGenerator
from lob.bookkeeping.custom_types import (
    Side,
    OrderType,
    ExecutionRule,
    FillStatus,
    EventKind,
)


class OrderExecutionIntegrationBase(unittest.TestCase):
    def setUp(self):
        self.orderbook = OrderBook()
        self.generator = OrderIdGenerator()


# ======================================================================================
# LimitOrderExecution
# ======================================================================================


class TestLimitOrderExecutionAgainstEmptyBook(OrderExecutionIntegrationBase):
    """
    A LIMIT aggressor against an empty opposite side cannot match and should
    rest in full on its own side.
    """

    def test_bid_aggressor_posts_in_full_when_ask_side_empty(self):
        aggressor = _make_limit(self.generator, Side.BID, limit_price=99, quantity=100)

        LimitOrderExecution(aggressor, self.orderbook).execute()

        self.assertIn(aggressor.order_id, self.orderbook)
        self.assertEqual(aggressor.remaining_quantity, 100)
        self.assertEqual(self.orderbook.bid_side.best_price, 99)

    def test_ask_aggressor_posts_in_full_when_bid_side_empty(self):
        aggressor = _make_limit(self.generator, Side.ASK, limit_price=101, quantity=100)

        LimitOrderExecution(aggressor, self.orderbook).execute()

        self.assertIn(aggressor.order_id, self.orderbook)
        self.assertEqual(aggressor.remaining_quantity, 100)
        self.assertEqual(self.orderbook.ask_side.best_price, 101)

    def test_status_is_unfilled_when_no_match(self):
        aggressor = _make_limit(self.generator, Side.BID, limit_price=99, quantity=100)

        result = LimitOrderExecution(aggressor, self.orderbook).execute()

        self.assertEqual(result.report.status, FillStatus.UNFILLED)

    def test_posted_flag_true_when_no_match(self):
        aggressor = _make_limit(self.generator, Side.BID, limit_price=99, quantity=100)

        result = LimitOrderExecution(aggressor, self.orderbook).execute()

        self.assertTrue(result.report.posted)

    def test_no_filled_events_when_no_match(self):
        aggressor = _make_limit(self.generator, Side.BID, limit_price=99, quantity=100)

        result = LimitOrderExecution(aggressor, self.orderbook).execute()

        self.assertFalse(any(e.kind == EventKind.FILLED for e in result.events))

    def test_posted_event_emitted_when_no_match(self):
        aggressor = _make_limit(self.generator, Side.BID, limit_price=99, quantity=100)

        result = LimitOrderExecution(aggressor, self.orderbook).execute()

        posted = [e for e in result.events if e.kind == EventKind.POSTED]
        self.assertEqual(len(posted), 1)


class TestLimitOrderExecutionFullyMatches(OrderExecutionIntegrationBase):
    """
    A LIMIT aggressor that crosses sufficient resting liquidity to fully fill
    should not be posted to the book.
    """

    def test_aggressor_fully_filled_at_single_level(self):
        resting = _make_limit(self.generator, Side.ASK, limit_price=100, quantity=200)
        self.orderbook.post_order(resting)
        aggressor = _make_limit(self.generator, Side.BID, limit_price=100, quantity=100)

        LimitOrderExecution(aggressor, self.orderbook).execute()

        self.assertTrue(aggressor.is_filled)
        self.assertEqual(resting.remaining_quantity, 100)

    def test_aggressor_fully_filled_walking_multiple_levels(self):
        resting1 = _make_limit(self.generator, Side.ASK, limit_price=100, quantity=100)
        resting2 = _make_limit(self.generator, Side.ASK, limit_price=101, quantity=100)
        self.orderbook.post_order(resting1)
        self.orderbook.post_order(resting2)
        aggressor = _make_limit(self.generator, Side.BID, limit_price=101, quantity=150)

        LimitOrderExecution(aggressor, self.orderbook).execute()

        self.assertTrue(aggressor.is_filled)
        self.assertTrue(resting1.is_filled)
        self.assertEqual(resting2.remaining_quantity, 50)

    def test_aggressor_not_posted_when_fully_filled(self):
        resting = _make_limit(self.generator, Side.ASK, limit_price=100, quantity=200)
        self.orderbook.post_order(resting)
        aggressor = _make_limit(self.generator, Side.BID, limit_price=100, quantity=100)

        result = LimitOrderExecution(aggressor, self.orderbook).execute()

        self.assertFalse(result.report.posted)

    def test_status_is_filled_when_fully_consumed(self):
        resting = _make_limit(self.generator, Side.ASK, limit_price=100, quantity=200)
        self.orderbook.post_order(resting)
        aggressor = _make_limit(self.generator, Side.BID, limit_price=100, quantity=100)

        result = LimitOrderExecution(aggressor, self.orderbook).execute()

        self.assertEqual(result.report.status, FillStatus.FILLED)

    def test_posted_flag_false_when_fully_filled(self):
        resting = _make_limit(self.generator, Side.ASK, limit_price=100, quantity=200)
        self.orderbook.post_order(resting)
        aggressor = _make_limit(self.generator, Side.BID, limit_price=100, quantity=100)

        result = LimitOrderExecution(aggressor, self.orderbook).execute()

        self.assertFalse(result.report.posted)

    def test_aggressor_not_in_orderbook_after_full_match(self):
        resting = _make_limit(self.generator, Side.ASK, limit_price=100, quantity=200)
        self.orderbook.post_order(resting)
        aggressor = _make_limit(self.generator, Side.BID, limit_price=100, quantity=100)

        LimitOrderExecution(aggressor, self.orderbook).execute()

        self.assertNotIn(aggressor.order_id, self.orderbook)

    def test_filled_events_count_matches_consumed_resting_orders(self):
        resting1 = _make_limit(self.generator, Side.ASK, limit_price=100, quantity=40)
        resting2 = _make_limit(self.generator, Side.ASK, limit_price=100, quantity=40)
        resting3 = _make_limit(self.generator, Side.ASK, limit_price=100, quantity=40)
        self.orderbook.post_order(resting1)
        self.orderbook.post_order(resting2)
        self.orderbook.post_order(resting3)
        aggressor = _make_limit(self.generator, Side.BID, limit_price=100, quantity=100)

        result = LimitOrderExecution(aggressor, self.orderbook).execute()

        filled = [e for e in result.events if e.kind == EventKind.FILLED]
        self.assertEqual(len(filled), 3)

    def test_no_posted_event_when_fully_filled(self):
        resting = _make_limit(self.generator, Side.ASK, limit_price=100, quantity=200)
        self.orderbook.post_order(resting)
        aggressor = _make_limit(self.generator, Side.BID, limit_price=100, quantity=100)

        result = LimitOrderExecution(aggressor, self.orderbook).execute()

        self.assertFalse(any(e.kind == EventKind.POSTED for e in result.events))


class TestLimitOrderExecutionPartiallyMatches(OrderExecutionIntegrationBase):
    """
    A LIMIT aggressor whose limit price stops it before being fully filled
    should rest its residual on its own side.
    """

    def test_residual_posted_at_aggressor_limit_price(self):
        resting = _make_limit(self.generator, Side.ASK, limit_price=100, quantity=40)
        self.orderbook.post_order(resting)
        aggressor = _make_limit(self.generator, Side.BID, limit_price=100, quantity=100)

        LimitOrderExecution(aggressor, self.orderbook).execute()

        self.assertIn(aggressor.order_id, self.orderbook)
        self.assertEqual(self.orderbook.bid_side.best_price, 100)

    def test_residual_quantity_equals_initial_minus_consumed(self):
        resting = _make_limit(self.generator, Side.ASK, limit_price=100, quantity=40)
        self.orderbook.post_order(resting)
        aggressor = _make_limit(self.generator, Side.BID, limit_price=100, quantity=100)

        LimitOrderExecution(aggressor, self.orderbook).execute()

        self.assertEqual(aggressor.remaining_quantity, 60)

    def test_status_is_partially_filled(self):
        resting = _make_limit(self.generator, Side.ASK, limit_price=100, quantity=40)
        self.orderbook.post_order(resting)
        aggressor = _make_limit(self.generator, Side.BID, limit_price=100, quantity=100)

        result = LimitOrderExecution(aggressor, self.orderbook).execute()

        self.assertEqual(result.report.status, FillStatus.PARTIALLY_FILLED)

    def test_posted_flag_true_when_residual_posted(self):
        resting = _make_limit(self.generator, Side.ASK, limit_price=100, quantity=40)
        self.orderbook.post_order(resting)
        aggressor = _make_limit(self.generator, Side.BID, limit_price=100, quantity=100)

        result = LimitOrderExecution(aggressor, self.orderbook).execute()

        self.assertTrue(result.report.posted)

    def test_aggressor_in_orderbook_after_partial_match(self):
        resting = _make_limit(self.generator, Side.ASK, limit_price=100, quantity=40)
        self.orderbook.post_order(resting)
        aggressor = _make_limit(self.generator, Side.BID, limit_price=100, quantity=100)

        LimitOrderExecution(aggressor, self.orderbook).execute()

        self.assertIn(aggressor.order_id, self.orderbook)

    def test_filled_events_precede_posted_event(self):
        resting = _make_limit(self.generator, Side.ASK, limit_price=100, quantity=40)
        self.orderbook.post_order(resting)
        aggressor = _make_limit(self.generator, Side.BID, limit_price=100, quantity=100)

        result = LimitOrderExecution(aggressor, self.orderbook).execute()

        kinds = [e.kind for e in result.events]
        last_filled = max(i for i, k in enumerate(kinds) if k == EventKind.FILLED)
        first_posted = kinds.index(EventKind.POSTED)
        self.assertLess(last_filled, first_posted)


class TestLimitOrderExecutionNoCross(OrderExecutionIntegrationBase):
    """
    A LIMIT aggressor whose price cannot cross the opposite best should post
    in full without consuming any resting liquidity.
    """

    def test_bid_below_best_ask_posts_without_matching(self):
        resting = _make_limit(self.generator, Side.ASK, limit_price=100, quantity=100)
        self.orderbook.post_order(resting)
        aggressor = _make_limit(self.generator, Side.BID, limit_price=99, quantity=100)

        LimitOrderExecution(aggressor, self.orderbook).execute()

        self.assertIn(aggressor.order_id, self.orderbook)
        self.assertEqual(aggressor.remaining_quantity, 100)
        self.assertEqual(self.orderbook.bid_side.best_price, 99)

    def test_ask_above_best_bid_posts_without_matching(self):
        resting = _make_limit(self.generator, Side.BID, limit_price=99, quantity=100)
        self.orderbook.post_order(resting)
        aggressor = _make_limit(self.generator, Side.ASK, limit_price=100, quantity=100)

        LimitOrderExecution(aggressor, self.orderbook).execute()

        self.assertIn(aggressor.order_id, self.orderbook)
        self.assertEqual(aggressor.remaining_quantity, 100)
        self.assertEqual(self.orderbook.ask_side.best_price, 100)

    def test_opposite_side_unchanged_when_no_cross(self):
        resting = _make_limit(self.generator, Side.ASK, limit_price=100, quantity=100)
        self.orderbook.post_order(resting)
        aggressor = _make_limit(self.generator, Side.BID, limit_price=99, quantity=100)

        LimitOrderExecution(aggressor, self.orderbook).execute()

        self.assertEqual(resting.remaining_quantity, 100)
        self.assertIn(resting.order_id, self.orderbook)

    def test_status_is_unfilled_when_no_cross(self):
        resting = _make_limit(self.generator, Side.ASK, limit_price=100, quantity=100)
        self.orderbook.post_order(resting)
        aggressor = _make_limit(self.generator, Side.BID, limit_price=99, quantity=100)

        result = LimitOrderExecution(aggressor, self.orderbook).execute()

        self.assertEqual(result.report.status, FillStatus.UNFILLED)


class TestLimitOrderExecutionWalksMultipleLevels(OrderExecutionIntegrationBase):
    """
    A LIMIT aggressor sweeps levels in price-time priority order, stopping at
    the first level whose price it cannot cross.
    """

    def test_consumes_levels_in_price_priority(self):
        resting_far = _make_limit(self.generator, Side.ASK, limit_price=102, quantity=100)
        resting_mid = _make_limit(self.generator, Side.ASK, limit_price=101, quantity=100)
        resting_near = _make_limit(self.generator, Side.ASK, limit_price=100, quantity=100)
        # post in non-priority order to verify price priority drives consumption
        self.orderbook.post_order(resting_far)
        self.orderbook.post_order(resting_mid)
        self.orderbook.post_order(resting_near)
        aggressor = _make_limit(self.generator, Side.BID, limit_price=102, quantity=250)

        result = LimitOrderExecution(aggressor, self.orderbook).execute()

        filled = [e for e in result.events if e.kind == EventKind.FILLED]
        prices = [e.payload.resting.limit_price for e in filled]
        self.assertEqual(prices, [100, 101, 102])

    def test_stops_at_first_uncrossable_level(self):
        resting_crossable_1 = _make_limit(
            self.generator, Side.ASK, limit_price=100, quantity=100
        )
        resting_crossable_2 = _make_limit(
            self.generator, Side.ASK, limit_price=101, quantity=100
        )
        resting_uncrossable = _make_limit(
            self.generator, Side.ASK, limit_price=102, quantity=100
        )
        self.orderbook.post_order(resting_crossable_1)
        self.orderbook.post_order(resting_crossable_2)
        self.orderbook.post_order(resting_uncrossable)
        aggressor = _make_limit(self.generator, Side.BID, limit_price=101, quantity=500)

        LimitOrderExecution(aggressor, self.orderbook).execute()

        self.assertTrue(resting_crossable_1.is_filled)
        self.assertTrue(resting_crossable_2.is_filled)
        self.assertEqual(
            resting_uncrossable.remaining_quantity, resting_uncrossable.initial_quantity
        )

    def test_residual_posted_after_partial_walk(self):
        resting1 = _make_limit(self.generator, Side.ASK, limit_price=100, quantity=100)
        resting2 = _make_limit(self.generator, Side.ASK, limit_price=101, quantity=100)
        resting_uncrossable = _make_limit(
            self.generator, Side.ASK, limit_price=102, quantity=100
        )
        self.orderbook.post_order(resting1)
        self.orderbook.post_order(resting2)
        self.orderbook.post_order(resting_uncrossable)
        aggressor = _make_limit(self.generator, Side.BID, limit_price=101, quantity=250)

        result = LimitOrderExecution(aggressor, self.orderbook).execute()

        self.assertTrue(result.report.posted)
        self.assertEqual(aggressor.remaining_quantity, 50)
        self.assertEqual(self.orderbook.bid_side.best_price, 101)

    def test_filled_payloads_ordered_by_consumption(self):
        resting_a = _make_limit(self.generator, Side.ASK, limit_price=100, quantity=50)
        resting_b = _make_limit(self.generator, Side.ASK, limit_price=100, quantity=50)
        resting_c = _make_limit(self.generator, Side.ASK, limit_price=101, quantity=50)
        self.orderbook.post_order(resting_a)
        self.orderbook.post_order(resting_b)
        self.orderbook.post_order(resting_c)
        aggressor = _make_limit(self.generator, Side.BID, limit_price=101, quantity=150)

        result = LimitOrderExecution(aggressor, self.orderbook).execute()

        filled = [e for e in result.events if e.kind == EventKind.FILLED]
        ids = [e.payload.resting.order_id for e in filled]
        self.assertEqual(
            ids, [resting_a.order_id, resting_b.order_id, resting_c.order_id]
        )


class TestLimitOrderExecutionExecutionResult(OrderExecutionIntegrationBase):
    """
    The ExecutionResult returned by a LIMIT execution carries an accurate
    report and event stream for the aggressor's lifecycle.
    """

    def test_report_aggressor_snapshot_matches_input_order(self):
        aggressor = _make_limit(self.generator, Side.BID, limit_price=99, quantity=100)

        result = LimitOrderExecution(aggressor, self.orderbook).execute()

        self.assertEqual(result.report.aggressor.order_id, aggressor.order_id)
        self.assertEqual(result.report.aggressor.initial_quantity, 100)
        self.assertEqual(result.report.aggressor.limit_price, 99)
        self.assertEqual(result.report.aggressor.side, Side.BID)

    def test_report_fills_match_emitted_filled_events(self):
        resting1 = _make_limit(self.generator, Side.ASK, limit_price=100, quantity=50)
        resting2 = _make_limit(self.generator, Side.ASK, limit_price=100, quantity=50)
        self.orderbook.post_order(resting1)
        self.orderbook.post_order(resting2)
        aggressor = _make_limit(self.generator, Side.BID, limit_price=100, quantity=100)

        result = LimitOrderExecution(aggressor, self.orderbook).execute()

        filled = [e for e in result.events if e.kind == EventKind.FILLED]
        self.assertEqual(len(filled), 2)
        total = sum(e.payload.filled_qty for e in filled)
        self.assertEqual(
            total, aggressor.initial_quantity - aggressor.remaining_quantity
        )

    def test_report_status_matches_compute_status(self):
        resting = _make_limit(self.generator, Side.ASK, limit_price=100, quantity=40)
        self.orderbook.post_order(resting)
        aggressor = _make_limit(self.generator, Side.BID, limit_price=100, quantity=100)

        executor = LimitOrderExecution(aggressor, self.orderbook)
        result = executor.execute()

        self.assertEqual(result.report.status, executor._compute_status())

    def test_events_stream_contains_filled_then_posted_for_partial(self):
        resting = _make_limit(self.generator, Side.ASK, limit_price=100, quantity=40)
        self.orderbook.post_order(resting)
        aggressor = _make_limit(self.generator, Side.BID, limit_price=100, quantity=100)

        result = LimitOrderExecution(aggressor, self.orderbook).execute()

        kinds = [e.kind for e in result.events]
        self.assertIn(EventKind.FILLED, kinds)
        self.assertIn(EventKind.POSTED, kinds)
        self.assertLess(kinds.index(EventKind.FILLED), kinds.index(EventKind.POSTED))

    def test_events_stream_contains_only_filled_for_full_match(self):
        resting = _make_limit(self.generator, Side.ASK, limit_price=100, quantity=200)
        self.orderbook.post_order(resting)
        aggressor = _make_limit(self.generator, Side.BID, limit_price=100, quantity=100)

        result = LimitOrderExecution(aggressor, self.orderbook).execute()

        kinds = {e.kind for e in result.events if e.kind != EventKind.ACCEPTED}
        self.assertEqual(kinds, {EventKind.FILLED})

    def test_events_stream_empty_of_fills_when_no_cross(self):
        resting = _make_limit(self.generator, Side.ASK, limit_price=100, quantity=100)
        self.orderbook.post_order(resting)
        aggressor = _make_limit(self.generator, Side.BID, limit_price=99, quantity=100)

        result = LimitOrderExecution(aggressor, self.orderbook).execute()

        self.assertFalse(any(e.kind == EventKind.FILLED for e in result.events))


# ======================================================================================
# MarketOrderExecution
# ======================================================================================


class TestMarketOrderExecutionAgainstEmptyBook(OrderExecutionIntegrationBase):
    """
    A MARKET aggressor against an empty opposite side cannot match and is
    discarded — never posted regardless of residual.
    """

    def test_aggressor_not_posted_when_no_liquidity(self):
        aggressor = _make_market(self.generator, Side.BID, quantity=100)

        result = MarketOrderExecution(aggressor, self.orderbook).execute()

        self.assertFalse(result.report.posted)

    def test_aggressor_not_in_orderbook(self):
        aggressor = _make_market(self.generator, Side.BID, quantity=100)

        MarketOrderExecution(aggressor, self.orderbook).execute()

        self.assertNotIn(aggressor.order_id, self.orderbook)

    def test_status_is_unfilled_when_no_liquidity(self):
        aggressor = _make_market(self.generator, Side.BID, quantity=100)

        result = MarketOrderExecution(aggressor, self.orderbook).execute()

        self.assertEqual(result.report.status, FillStatus.UNFILLED)

    def test_posted_flag_false(self):
        aggressor = _make_market(self.generator, Side.BID, quantity=100)

        result = MarketOrderExecution(aggressor, self.orderbook).execute()

        self.assertFalse(result.report.posted)

    def test_no_events_emitted_apart_from_acceptance(self):
        aggressor = _make_market(self.generator, Side.BID, quantity=100)

        result = MarketOrderExecution(aggressor, self.orderbook).execute()

        kinds = [e.kind for e in result.events]
        self.assertEqual(kinds, [EventKind.ACCEPTED])


class TestMarketOrderExecutionFullyMatches(OrderExecutionIntegrationBase):
    """
    A MARKET aggressor consumes opposite-side liquidity until filled.
    """

    def test_aggressor_fully_filled_at_single_level(self):
        resting = _make_limit(self.generator, Side.ASK, limit_price=100, quantity=200)
        self.orderbook.post_order(resting)
        aggressor = _make_market(self.generator, Side.BID, quantity=100)

        MarketOrderExecution(aggressor, self.orderbook).execute()

        self.assertTrue(aggressor.is_filled)
        self.assertEqual(resting.remaining_quantity, 100)

    def test_aggressor_fully_filled_walking_multiple_levels(self):
        resting1 = _make_limit(self.generator, Side.ASK, limit_price=100, quantity=100)
        resting2 = _make_limit(self.generator, Side.ASK, limit_price=200, quantity=100)
        self.orderbook.post_order(resting1)
        self.orderbook.post_order(resting2)
        aggressor = _make_market(self.generator, Side.BID, quantity=150)

        MarketOrderExecution(aggressor, self.orderbook).execute()

        self.assertTrue(aggressor.is_filled)
        self.assertTrue(resting1.is_filled)
        self.assertEqual(resting2.remaining_quantity, 50)

    def test_aggressor_not_posted_when_fully_filled(self):
        resting = _make_limit(self.generator, Side.ASK, limit_price=100, quantity=200)
        self.orderbook.post_order(resting)
        aggressor = _make_market(self.generator, Side.BID, quantity=100)

        MarketOrderExecution(aggressor, self.orderbook).execute()

        self.assertNotIn(aggressor.order_id, self.orderbook)

    def test_status_is_filled(self):
        resting = _make_limit(self.generator, Side.ASK, limit_price=100, quantity=200)
        self.orderbook.post_order(resting)
        aggressor = _make_market(self.generator, Side.BID, quantity=100)

        result = MarketOrderExecution(aggressor, self.orderbook).execute()

        self.assertEqual(result.report.status, FillStatus.FILLED)

    def test_posted_flag_false_when_fully_filled(self):
        resting = _make_limit(self.generator, Side.ASK, limit_price=100, quantity=200)
        self.orderbook.post_order(resting)
        aggressor = _make_market(self.generator, Side.BID, quantity=100)

        result = MarketOrderExecution(aggressor, self.orderbook).execute()

        self.assertFalse(result.report.posted)


class TestMarketOrderExecutionPartiallyMatches(OrderExecutionIntegrationBase):
    """
    A MARKET aggressor that exhausts opposite-side liquidity before being
    filled keeps its residual off the book.
    """

    def test_residual_not_posted(self):
        resting = _make_limit(self.generator, Side.ASK, limit_price=100, quantity=40)
        self.orderbook.post_order(resting)
        aggressor = _make_market(self.generator, Side.BID, quantity=100)

        result = MarketOrderExecution(aggressor, self.orderbook).execute()

        self.assertFalse(result.report.posted)

    def test_aggressor_not_in_orderbook(self):
        resting = _make_limit(self.generator, Side.ASK, limit_price=100, quantity=40)
        self.orderbook.post_order(resting)
        aggressor = _make_market(self.generator, Side.BID, quantity=100)

        MarketOrderExecution(aggressor, self.orderbook).execute()

        self.assertNotIn(aggressor.order_id, self.orderbook)

    def test_residual_quantity_equals_initial_minus_consumed(self):
        resting = _make_limit(self.generator, Side.ASK, limit_price=100, quantity=40)
        self.orderbook.post_order(resting)
        aggressor = _make_market(self.generator, Side.BID, quantity=100)

        MarketOrderExecution(aggressor, self.orderbook).execute()

        self.assertEqual(aggressor.remaining_quantity, 60)

    def test_status_is_partially_filled(self):
        resting = _make_limit(self.generator, Side.ASK, limit_price=100, quantity=40)
        self.orderbook.post_order(resting)
        aggressor = _make_market(self.generator, Side.BID, quantity=100)

        result = MarketOrderExecution(aggressor, self.orderbook).execute()

        self.assertEqual(result.report.status, FillStatus.PARTIALLY_FILLED)

    def test_posted_flag_false(self):
        resting = _make_limit(self.generator, Side.ASK, limit_price=100, quantity=40)
        self.orderbook.post_order(resting)
        aggressor = _make_market(self.generator, Side.BID, quantity=100)

        result = MarketOrderExecution(aggressor, self.orderbook).execute()

        self.assertFalse(result.report.posted)


class TestMarketOrderExecutionWalksMultipleLevels(OrderExecutionIntegrationBase):
    """
    A MARKET aggressor crosses every available level — there is no limit price
    to stop it.
    """

    def test_consumes_all_levels_until_filled(self):
        resting1 = _make_limit(self.generator, Side.ASK, limit_price=100, quantity=50)
        resting2 = _make_limit(self.generator, Side.ASK, limit_price=200, quantity=50)
        resting3 = _make_limit(self.generator, Side.ASK, limit_price=300, quantity=50)
        self.orderbook.post_order(resting1)
        self.orderbook.post_order(resting2)
        self.orderbook.post_order(resting3)
        aggressor = _make_market(self.generator, Side.BID, quantity=120)

        MarketOrderExecution(aggressor, self.orderbook).execute()

        self.assertTrue(aggressor.is_filled)
        self.assertTrue(resting1.is_filled)
        self.assertTrue(resting2.is_filled)
        self.assertEqual(resting3.remaining_quantity, 30)

    def test_consumes_all_available_when_book_too_thin(self):
        resting1 = _make_limit(self.generator, Side.ASK, limit_price=100, quantity=50)
        resting2 = _make_limit(self.generator, Side.ASK, limit_price=200, quantity=50)
        self.orderbook.post_order(resting1)
        self.orderbook.post_order(resting2)
        aggressor = _make_market(self.generator, Side.BID, quantity=500)

        MarketOrderExecution(aggressor, self.orderbook).execute()

        self.assertFalse(aggressor.is_filled)
        self.assertEqual(aggressor.remaining_quantity, 400)
        self.assertTrue(self.orderbook.ask_side.is_empty)

    def test_filled_payloads_ordered_by_consumption(self):
        resting_low = _make_limit(self.generator, Side.ASK, limit_price=100, quantity=50)
        resting_mid = _make_limit(self.generator, Side.ASK, limit_price=200, quantity=50)
        resting_high = _make_limit(self.generator, Side.ASK, limit_price=300, quantity=50)
        # post in non-priority order
        self.orderbook.post_order(resting_high)
        self.orderbook.post_order(resting_mid)
        self.orderbook.post_order(resting_low)
        aggressor = _make_market(self.generator, Side.BID, quantity=150)

        result = MarketOrderExecution(aggressor, self.orderbook).execute()

        filled = [e for e in result.events if e.kind == EventKind.FILLED]
        ids = [e.payload.resting.order_id for e in filled]
        self.assertEqual(
            ids, [resting_low.order_id, resting_mid.order_id, resting_high.order_id]
        )


class TestMarketOrderExecutionExecutionResult(OrderExecutionIntegrationBase):
    """
    The ExecutionResult returned by a MARKET execution carries an accurate
    report and event stream — never includes a POSTED event.
    """

    def test_report_aggressor_snapshot_matches_input_order(self):
        aggressor = _make_market(self.generator, Side.BID, quantity=100)

        result = MarketOrderExecution(aggressor, self.orderbook).execute()

        self.assertEqual(result.report.aggressor.order_id, aggressor.order_id)
        self.assertEqual(result.report.aggressor.initial_quantity, 100)
        self.assertEqual(result.report.aggressor.order_type, OrderType.MARKET)

    def test_report_fills_match_emitted_filled_events(self):
        resting1 = _make_limit(self.generator, Side.ASK, limit_price=100, quantity=30)
        resting2 = _make_limit(self.generator, Side.ASK, limit_price=200, quantity=30)
        self.orderbook.post_order(resting1)
        self.orderbook.post_order(resting2)
        aggressor = _make_market(self.generator, Side.BID, quantity=60)

        result = MarketOrderExecution(aggressor, self.orderbook).execute()

        filled = [e for e in result.events if e.kind == EventKind.FILLED]
        self.assertEqual(len(filled), 2)
        total = sum(e.payload.filled_qty for e in filled)
        self.assertEqual(
            total, aggressor.initial_quantity - aggressor.remaining_quantity
        )

    def test_report_posted_is_always_false(self):
        resting = _make_limit(self.generator, Side.ASK, limit_price=100, quantity=40)
        self.orderbook.post_order(resting)
        aggressor = _make_market(self.generator, Side.BID, quantity=100)

        result = MarketOrderExecution(aggressor, self.orderbook).execute()

        self.assertFalse(result.report.posted)

    def test_events_stream_never_contains_posted_event(self):
        resting = _make_limit(self.generator, Side.ASK, limit_price=100, quantity=40)
        self.orderbook.post_order(resting)
        aggressor = _make_market(self.generator, Side.BID, quantity=100)

        result = MarketOrderExecution(aggressor, self.orderbook).execute()

        self.assertFalse(any(e.kind == EventKind.POSTED for e in result.events))


# ======================================================================================
# execute_order dispatcher
# ======================================================================================


class TestExecuteOrderDispatch(OrderExecutionIntegrationBase):
    """
    Module-level execute_order picks the right execution strategy based on
    order_type and produces the same end-state as invoking the strategy
    directly.
    """

    def test_limit_order_routed_through_limit_execution(self):
        aggressor = _make_limit(self.generator, Side.BID, limit_price=99, quantity=100)

        result = execute_order(aggressor, self.orderbook)

        # only LimitOrderExecution posts residuals
        self.assertTrue(result.report.posted)
        self.assertIn(aggressor.order_id, self.orderbook)

    def test_market_order_routed_through_market_execution(self):
        aggressor = _make_market(self.generator, Side.BID, quantity=100)

        result = execute_order(aggressor, self.orderbook)

        # MarketOrderExecution never posts
        self.assertFalse(result.report.posted)
        self.assertNotIn(aggressor.order_id, self.orderbook)

    def test_limit_order_residual_rests_on_book(self):
        resting = _make_limit(self.generator, Side.ASK, limit_price=100, quantity=40)
        self.orderbook.post_order(resting)
        aggressor = _make_limit(self.generator, Side.BID, limit_price=100, quantity=100)

        execute_order(aggressor, self.orderbook)

        self.assertIn(aggressor.order_id, self.orderbook)
        self.assertEqual(aggressor.remaining_quantity, 60)

    def test_market_order_residual_discarded(self):
        resting = _make_limit(self.generator, Side.ASK, limit_price=100, quantity=40)
        self.orderbook.post_order(resting)
        aggressor = _make_market(self.generator, Side.BID, quantity=100)

        execute_order(aggressor, self.orderbook)

        self.assertNotIn(aggressor.order_id, self.orderbook)
        self.assertEqual(aggressor.remaining_quantity, 60)

    def test_resting_orders_consumed_in_price_time_priority(self):
        resting_high = _make_limit(self.generator, Side.ASK, limit_price=200, quantity=30)
        resting_low = _make_limit(self.generator, Side.ASK, limit_price=100, quantity=30)
        self.orderbook.post_order(resting_high)
        self.orderbook.post_order(resting_low)
        aggressor = _make_market(self.generator, Side.BID, quantity=60)

        result = execute_order(aggressor, self.orderbook)

        filled = [e for e in result.events if e.kind == EventKind.FILLED]
        ids = [e.payload.resting.order_id for e in filled]
        self.assertEqual(ids, [resting_low.order_id, resting_high.order_id])


# ======================================================================================
# price-time priority (behavioural half of what test_orderbook covers structurally)
# ======================================================================================


class TestPriceTimePriorityBehavioural(OrderExecutionIntegrationBase):
    """
    With matching wired in, verify the BEHAVIOURAL half of price-time
    priority: who gets filled first when multiple resting orders compete.
    """

    def test_earlier_resting_order_at_same_price_filled_first(self):
        first = _make_limit(self.generator, Side.ASK, limit_price=100, quantity=50)
        second = _make_limit(self.generator, Side.ASK, limit_price=100, quantity=50)
        self.orderbook.post_order(first)
        self.orderbook.post_order(second)
        aggressor = _make_limit(self.generator, Side.BID, limit_price=100, quantity=50)

        LimitOrderExecution(aggressor, self.orderbook).execute()

        self.assertTrue(first.is_filled)
        self.assertEqual(second.remaining_quantity, second.initial_quantity)

    def test_better_priced_resting_filled_before_worse_priced(self):
        worse = _make_limit(self.generator, Side.ASK, limit_price=101, quantity=50)
        better = _make_limit(self.generator, Side.ASK, limit_price=100, quantity=50)
        # post worse first to ensure the test isolates price priority from FIFO
        self.orderbook.post_order(worse)
        self.orderbook.post_order(better)
        aggressor = _make_limit(self.generator, Side.BID, limit_price=101, quantity=50)

        LimitOrderExecution(aggressor, self.orderbook).execute()

        self.assertTrue(better.is_filled)
        self.assertEqual(worse.remaining_quantity, worse.initial_quantity)

    def test_partial_fill_leaves_head_of_queue_with_residual(self):
        head = _make_limit(self.generator, Side.ASK, limit_price=100, quantity=100)
        tail = _make_limit(self.generator, Side.ASK, limit_price=100, quantity=100)
        self.orderbook.post_order(head)
        self.orderbook.post_order(tail)
        aggressor = _make_limit(self.generator, Side.BID, limit_price=100, quantity=40)

        LimitOrderExecution(aggressor, self.orderbook).execute()

        self.assertEqual(head.remaining_quantity, 60)
        self.assertIs(
            self.orderbook.ask_side.get_level(100).next_order_to_execute, head
        )
        self.assertEqual(tail.remaining_quantity, tail.initial_quantity)


# ======================================================================================
# successive executions (state evolution across multiple aggressors)
# ======================================================================================


class TestSuccessiveExecutions(OrderExecutionIntegrationBase):
    """
    Multiple aggressors executed in sequence should leave the book in a
    consistent state — each execution sees the residual of the previous one.
    """

    def test_second_aggressor_sees_residual_of_first(self):
        resting = _make_limit(self.generator, Side.BID, limit_price=99, quantity=200)
        self.orderbook.post_order(resting)

        aggressor1 = _make_limit(self.generator, Side.ASK, limit_price=99, quantity=100)
        LimitOrderExecution(aggressor1, self.orderbook).execute()
        self.assertEqual(resting.remaining_quantity, 100)

        aggressor2 = _make_limit(self.generator, Side.ASK, limit_price=99, quantity=50)
        LimitOrderExecution(aggressor2, self.orderbook).execute()

        self.assertEqual(resting.remaining_quantity, 50)
        self.assertIn(resting.order_id, self.orderbook)

    def test_resting_residual_from_partial_fill_visible_to_next_aggressor(self):
        small_resting = _make_limit(
            self.generator, Side.ASK, limit_price=100, quantity=40
        )
        self.orderbook.post_order(small_resting)

        aggressor1 = _make_limit(self.generator, Side.BID, limit_price=100, quantity=100)
        LimitOrderExecution(aggressor1, self.orderbook).execute()
        self.assertIn(aggressor1.order_id, self.orderbook)
        self.assertEqual(aggressor1.remaining_quantity, 60)

        aggressor2 = _make_limit(self.generator, Side.ASK, limit_price=100, quantity=30)
        LimitOrderExecution(aggressor2, self.orderbook).execute()

        self.assertTrue(aggressor2.is_filled)
        self.assertEqual(aggressor1.remaining_quantity, 30)
        self.assertIn(aggressor1.order_id, self.orderbook)

    def test_book_state_consistent_after_mixed_limit_and_market_aggressors(self):
        resting_ask_1 = _make_limit(
            self.generator, Side.ASK, limit_price=100, quantity=50
        )
        resting_ask_2 = _make_limit(
            self.generator, Side.ASK, limit_price=101, quantity=50
        )
        resting_bid = _make_limit(self.generator, Side.BID, limit_price=98, quantity=80)
        self.orderbook.post_order(resting_ask_1)
        self.orderbook.post_order(resting_ask_2)
        self.orderbook.post_order(resting_bid)

        market_buyer = _make_market(self.generator, Side.BID, quantity=70)
        execute_order(market_buyer, self.orderbook)

        limit_seller = _make_limit(self.generator, Side.ASK, limit_price=98, quantity=50)
        execute_order(limit_seller, self.orderbook)

        self.assertTrue(resting_ask_1.is_filled)
        self.assertEqual(resting_ask_2.remaining_quantity, 30)
        self.assertEqual(resting_bid.remaining_quantity, 30)
        self.assertEqual(self.orderbook.ask_side.best_price, 101)
        self.assertEqual(self.orderbook.bid_side.best_price, 98)
        self.assertNotIn(market_buyer.order_id, self.orderbook)
        self.assertNotIn(limit_seller.order_id, self.orderbook)


# ======================================================================================
# helpers
# ======================================================================================


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
