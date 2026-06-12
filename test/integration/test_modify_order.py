import unittest
from lob.orderbook.orderbook import OrderBook
from lob.orderbook.modify_order import ModifyOrderExecution
from lob.orders.factory import LimitOrderFactory
from lob.orders.order import Order, OrderID, OrderSpec
from lob.orders.order_id_generator import OrderIdGenerator
from lob.orderbook.order_execution import execute_order
from lob.bookkeeping.exceptions import InvalidModificationError, OrderNotFoundError
from lob.bookkeeping.custom_types import (
    Side,
    OrderType,
    ExecutionRule,
    FillStatus,
    EventKind,
    ModifiedPayload,
)


class ModifyOrderExecutionBase(unittest.TestCase):
    def setUp(self):
        self.orderbook = OrderBook()
        self.generator = OrderIdGenerator()
        # Factory shares the generator so cloned replacements get globally
        # unique ids that never collide with already-resting orders.
        self.factory = LimitOrderFactory(self.generator)

    def _rest_limit(self, side: Side, limit_price: int, quantity: int) -> Order:
        order = self.factory.create_order(
            side=side,
            quantity=quantity,
            user_id=0,
            limit_price=limit_price,
            execution_rule=ExecutionRule.GTC,
        )
        self.orderbook.post_order(order)
        return order

    def _modifier(self, order_id: int) -> ModifyOrderExecution:
        return ModifyOrderExecution(self.orderbook, order_id, self.factory)


# ======================================================================================
# size-down: in-place transition, keeps id and queue priority
# ======================================================================================


class TestSizeDownKeepsPriority(ModifyOrderExecutionBase):
    """
    A strictly-lower quantity at the same price is an in-place book transition:
    one MODIFIED event, the order keeps its id, nothing trades.
    """

    def test_returns_single_modified_event(self):
        original = self._rest_limit(Side.BID, limit_price=100, quantity=100)

        result = self._modifier(original.order_id).modify(
            new_price=None, new_quantity=60
        )

        self.assertEqual(len(result.events), 1)
        self.assertEqual(result.events[0].kind, EventKind.MODIFIED)
        self.assertIsInstance(result.events[0].payload, ModifiedPayload)

    def test_report_is_posted_and_unfilled(self):
        original = self._rest_limit(Side.BID, limit_price=100, quantity=100)

        result = self._modifier(original.order_id).modify(
            new_price=None, new_quantity=60
        )

        self.assertTrue(result.report.posted)
        self.assertEqual(result.report.status, FillStatus.UNFILLED)

    def test_order_kept_in_book_with_same_id_and_reduced_quantity(self):
        original = self._rest_limit(Side.BID, limit_price=100, quantity=100)

        result = self._modifier(original.order_id).modify(
            new_price=None, new_quantity=60
        )

        self.assertIn(original.order_id, self.orderbook)
        self.assertEqual(original.remaining_quantity, 60)
        self.assertEqual(result.report.aggressor.order_id, original.order_id)
        self.assertEqual(result.report.aggressor.remaining_quantity, 60)

    def test_modified_payload_carries_before_and_after_snapshots(self):
        original = self._rest_limit(Side.BID, limit_price=100, quantity=100)

        result = self._modifier(original.order_id).modify(
            new_price=None, new_quantity=60
        )

        payload = result.events[0].payload
        self.assertEqual(payload.original_order.remaining_quantity, 100)
        self.assertEqual(payload.modified_order.remaining_quantity, 60)


# ======================================================================================
# cancel-and-repost: price change / size up, loses priority, one event stream
# ======================================================================================


class TestCancelAndRepostNonCrossing(ModifyOrderExecutionBase):
    """
    A price change that does not cross is cancel-and-repost: the original is
    cancelled and a fresh-id replacement rests. Both transitions live in one
    event stream, CANCELLED first.
    """

    def test_cancelled_event_precedes_repost_events(self):
        original = self._rest_limit(Side.BID, limit_price=100, quantity=50)

        result = self._modifier(original.order_id).modify(
            new_price=99, new_quantity=None
        )

        kinds = [e.kind for e in result.events]
        self.assertEqual(kinds[0], EventKind.CANCELLED)
        self.assertIn(EventKind.ACCEPTED, kinds)
        self.assertIn(EventKind.POSTED, kinds)
        self.assertLess(
            kinds.index(EventKind.CANCELLED), kinds.index(EventKind.ACCEPTED)
        )

    def test_old_order_removed_new_order_rests_with_fresh_id(self):
        original = self._rest_limit(Side.BID, limit_price=100, quantity=50)

        result = self._modifier(original.order_id).modify(
            new_price=99, new_quantity=None
        )

        cancelled_id = result.events[0].payload.aggressor.order_id
        posted = next(e for e in result.events if e.kind == EventKind.POSTED)
        new_id = posted.payload.aggressor.order_id

        self.assertEqual(cancelled_id, original.order_id)
        self.assertNotEqual(new_id, original.order_id)
        self.assertNotIn(original.order_id, self.orderbook)
        self.assertIn(new_id, self.orderbook)

    def test_report_describes_the_replacement(self):
        original = self._rest_limit(Side.BID, limit_price=100, quantity=50)

        result = self._modifier(original.order_id).modify(
            new_price=99, new_quantity=None
        )

        self.assertTrue(result.report.posted)
        self.assertEqual(result.report.status, FillStatus.UNFILLED)
        self.assertEqual(result.report.aggressor.limit_price, 99)


class TestCancelAndRepostQuantityIncrease(ModifyOrderExecutionBase):
    """
    A quantity increase (>= current remaining) is cancel-and-repost, not an
    in-place transition — it would gain queue position otherwise.
    """

    def test_increase_reposts_at_larger_size(self):
        original = self._rest_limit(Side.BID, limit_price=100, quantity=50)

        result = self._modifier(original.order_id).modify(
            new_price=None, new_quantity=80
        )

        kinds = [e.kind for e in result.events]
        self.assertEqual(kinds[0], EventKind.CANCELLED)
        posted = next(e for e in result.events if e.kind == EventKind.POSTED)
        self.assertEqual(posted.payload.aggressor.initial_quantity, 80)
        self.assertNotIn(original.order_id, self.orderbook)
        self.assertIn(posted.payload.aggressor.order_id, self.orderbook)


class TestCancelAndRepostCrossing(ModifyOrderExecutionBase):
    """
    A price change whose replacement crosses routes through the matcher like
    any aggressor: the crossing fills surface as FILLED events inside the same
    ExecutionResult (D12), still led by the CANCELLED of the original.
    """

    def test_crossing_replacement_fills_in_one_stream(self):
        resting_ask = self._rest_limit(Side.ASK, limit_price=100, quantity=50)
        original = self._rest_limit(Side.BID, limit_price=99, quantity=50)

        result = self._modifier(original.order_id).modify(
            new_price=100, new_quantity=None
        )

        kinds = [e.kind for e in result.events]
        self.assertEqual(kinds[0], EventKind.CANCELLED)
        self.assertIn(EventKind.FILLED, kinds)
        self.assertEqual(result.report.status, FillStatus.FILLED)
        self.assertFalse(result.report.posted)

        new_id = result.report.aggressor.order_id
        self.assertNotEqual(new_id, original.order_id)
        self.assertNotIn(original.order_id, self.orderbook)
        self.assertNotIn(new_id, self.orderbook)  # fully filled, never rested
        self.assertNotIn(resting_ask.order_id, self.orderbook)


# ======================================================================================
# defensive guarantee: a rejected replacement never loses the original
# ======================================================================================


class TestRejectedReplacementKeepsOriginal(ModifyOrderExecutionBase):
    """
    The original is cancelled LAST, only after the replacement is accepted. If
    the replacement is rejected the original stays resting and no CANCELLED
    event is emitted — `is_rejected` is the whole signal. Driven through the
    private composer because the public modify validates inputs before cloning,
    so a rejection cannot arise from a well-formed modify call.
    """

    def test_rejected_repost_leaves_original_untouched(self):
        original = self._rest_limit(Side.BID, limit_price=100, quantity=50)
        modifier = self._modifier(original.order_id)

        # A replacement that duplicates a live id is rejected by validation.
        duplicate = Order(
            OrderSpec(Side.BID, OrderType.LIMIT, 50, 99, ExecutionRule.GTC),
            OrderID(original.order_id, 0),
        )
        result = modifier._cancel_and_post(duplicate)

        self.assertTrue(result.is_rejected)
        self.assertFalse(any(e.kind == EventKind.CANCELLED for e in result.events))
        self.assertIn(original.order_id, self.orderbook)
        self.assertEqual(original.remaining_quantity, 50)


class TestModifyPriceAndQuantityTogether(ModifyOrderExecutionBase):
    """price+quantity in one modify is a single cancel-and-repost honoring BOTH (no fallback)."""

    def test_reposts_at_new_price_and_new_quantity(self):
        # modify(99, 80) on BID 100/50 -> CANCELLED first; posted price=99, initial_qty=80; orig gone, new rests.
        original = self._rest_limit(Side.BID, limit_price=100, quantity=50)

        result = self._modifier(original.order_id).modify(new_price=99, new_quantity=80)

        kinds = [e.kind for e in result.events]
        self.assertEqual(kinds[0], EventKind.CANCELLED)
        posted = next(e for e in result.events if e.kind == EventKind.POSTED)
        self.assertEqual(posted.payload.aggressor.limit_price, 99)
        self.assertEqual(posted.payload.aggressor.initial_quantity, 80)
        self.assertNotIn(original.order_id, self.orderbook)
        self.assertIn(posted.payload.aggressor.order_id, self.orderbook)


class TestModifyPriceWithSmallerQuantityReposts(ModifyOrderExecutionBase):
    """a price change with qty<remaining REPOSTS — it is NOT an in-place size-down (no MODIFIED)."""

    def test_price_plus_smaller_quantity_reposts_not_inplace(self):
        # modify(99, 30) -> CANCELLED+POSTED, no MODIFIED, fresh id, posted initial_qty=30.
        original = self._rest_limit(Side.BID, limit_price=100, quantity=50)

        result = self._modifier(original.order_id).modify(new_price=99, new_quantity=30)

        kinds = [e.kind for e in result.events]
        self.assertEqual(kinds[0], EventKind.CANCELLED)
        self.assertIn(EventKind.POSTED, kinds)
        self.assertNotIn(EventKind.MODIFIED, kinds)
        posted = next(e for e in result.events if e.kind == EventKind.POSTED)
        self.assertNotEqual(posted.payload.aggressor.order_id, original.order_id)
        self.assertEqual(posted.payload.aggressor.initial_quantity, 30)


class TestModifyPriceWithEqualQuantityReposts(ModifyOrderExecutionBase):
    """price change + qty==remaining does NOT raise 'no quantity to modify' (guard is price-conditional)."""

    def test_price_plus_equal_quantity_does_not_raise_reposts(self):
        # modify(99, 50) -> reposts; the ==remaining no-op guard lives only in _modify_quantity, bypassed here.
        original = self._rest_limit(Side.BID, limit_price=100, quantity=50)

        result = self._modifier(original.order_id).modify(new_price=99, new_quantity=50)

        kinds = [e.kind for e in result.events]
        self.assertEqual(kinds[0], EventKind.CANCELLED)
        self.assertIn(EventKind.POSTED, kinds)
        posted = next(e for e in result.events if e.kind == EventKind.POSTED)
        self.assertEqual(posted.payload.aggressor.limit_price, 99)
        self.assertEqual(posted.payload.aggressor.initial_quantity, 50)
        self.assertNotIn(original.order_id, self.orderbook)


class TestSizeDownConsumesNoFreshId(ModifyOrderExecutionBase):
    """size-down is in-place: no clone, the shared OrderIdGenerator is not advanced."""

    def test_size_down_does_not_advance_id_generator(self):
        # after modify(None, 60): self.generator.next_id() == original.order_id + 1 (only the rest consumed an id).
        original = self._rest_limit(Side.BID, limit_price=100, quantity=100)

        self._modifier(original.order_id).modify(new_price=None, new_quantity=60)

        self.assertEqual(self.generator.next_id(), original.order_id + 1)


class TestPriceOnlyRepostInheritsRemainingQuantity(ModifyOrderExecutionBase):
    """price-only repost clones the original's REMAINING quantity (not initial) when new_quantity is None."""

    def test_price_only_repost_uses_remaining_after_partial_fill(self):
        # partially fill original 50 -> remaining 30; assert original.remaining_quantity == 30 (Order, not int);
        # then modify(99, None) -> posted initial_quantity == 30 (not 50).
        original = self._rest_limit(Side.BID, limit_price=100, quantity=50)

        # Crossing ASK consumes 20 of the resting BID in place: 50 -> 30, original keeps its id.
        aggressor = self.factory.create_order(
            side=Side.ASK,
            quantity=20,
            user_id=0,
            limit_price=100,
            execution_rule=ExecutionRule.GTC,
        )
        execute_order(aggressor, self.orderbook)
        self.assertEqual(original.remaining_quantity, 30)

        result = self._modifier(original.order_id).modify(
            new_price=99, new_quantity=None
        )

        posted = next(e for e in result.events if e.kind == EventKind.POSTED)
        self.assertEqual(posted.payload.aggressor.initial_quantity, 30)


class TestAskSideSizeDownKeepsPriority(ModifyOrderExecutionBase):
    """size-down is side-symmetric: an ASK reduces in-place, keeps its id."""

    def test_ask_size_down_in_place_keeps_id(self):
        # ASK 105/100 -> modify(None, 60): one MODIFIED, same id, remaining 60, side ASK.
        original = self._rest_limit(Side.ASK, limit_price=105, quantity=100)

        result = self._modifier(original.order_id).modify(
            new_price=None, new_quantity=60
        )

        self.assertEqual(len(result.events), 1)
        self.assertEqual(result.events[0].kind, EventKind.MODIFIED)
        self.assertIn(original.order_id, self.orderbook)
        self.assertEqual(original.remaining_quantity, 60)
        self.assertEqual(result.report.aggressor.side, Side.ASK)


class TestAskSidePriceRepostNonCrossing(ModifyOrderExecutionBase):
    """price change is side-symmetric: raising an ASK's price reposts, CANCELLED first."""

    def test_ask_price_repost_non_crossing(self):
        # ASK 105 -> modify(106, None): CANCELLED+POSTED, posted price=106 side=ASK, fresh id.
        original = self._rest_limit(Side.ASK, limit_price=105, quantity=100)

        result = self._modifier(original.order_id).modify(
            new_price=106, new_quantity=None
        )

        kinds = [e.kind for e in result.events]
        self.assertEqual(kinds[0], EventKind.CANCELLED)
        self.assertIn(EventKind.POSTED, kinds)
        posted = next(e for e in result.events if e.kind == EventKind.POSTED)
        self.assertEqual(posted.payload.aggressor.limit_price, 106)
        self.assertEqual(posted.payload.aggressor.side, Side.ASK)
        self.assertNotEqual(posted.payload.aggressor.order_id, original.order_id)
        self.assertIn(posted.payload.aggressor.order_id, self.orderbook)


class TestCrossingRepostPartialFillRestsResidual(ModifyOrderExecutionBase):
    """a crossing repost that only PARTIALLY fills leaves the residual resting: PARTIALLY_FILLED, posted True."""

    def test_crossing_repost_partial_fill_rests_residual(self):
        # resting ASK 30@100, original BID 50@99 -> modify(100, None): CANCELLED,FILLED,POSTED;
        # status PARTIALLY_FILLED, posted True, residual qty 20 rests under fresh id, ASK consumed.
        resting_ask = self._rest_limit(Side.ASK, limit_price=100, quantity=30)
        original = self._rest_limit(Side.BID, limit_price=99, quantity=50)

        result = self._modifier(original.order_id).modify(
            new_price=100, new_quantity=None
        )

        kinds = [e.kind for e in result.events]
        self.assertEqual(kinds[0], EventKind.CANCELLED)
        self.assertIn(EventKind.FILLED, kinds)
        self.assertIn(EventKind.POSTED, kinds)
        self.assertEqual(result.report.status, FillStatus.PARTIALLY_FILLED)
        self.assertTrue(result.report.posted)

        new_id = result.report.aggressor.order_id
        self.assertNotEqual(new_id, original.order_id)
        self.assertEqual(result.report.aggressor.remaining_quantity, 20)
        self.assertIn(new_id, self.orderbook)
        self.assertNotIn(original.order_id, self.orderbook)
        self.assertNotIn(resting_ask.order_id, self.orderbook)


class TestSizeDownToOneBoundary(ModifyOrderExecutionBase):
    """decreasing to quantity 1 is a valid in-place reduce (lower edge of reduce()'s >0 assert)."""

    def test_decrease_to_one_in_place(self):
        # qty 2 -> modify(None, 1): one MODIFIED, remaining 1.
        original = self._rest_limit(Side.BID, limit_price=100, quantity=2)

        result = self._modifier(original.order_id).modify(
            new_price=None, new_quantity=1
        )

        self.assertEqual(len(result.events), 1)
        self.assertEqual(result.events[0].kind, EventKind.MODIFIED)
        self.assertEqual(original.remaining_quantity, 1)


class TestModifyRejectsInvalidInputsThroughPublicApi(ModifyOrderExecutionBase):
    """public modify raises InvalidModificationError for no-target / no-op / bad-type / non-positive, with no book mutation."""

    def test_invalid_inputs_raise_and_leave_book_unchanged(self):
        # (None,None) 'nothing to modify...'; (None,50) 'no quantity to modify'; (99.0,None) '... not float.';
        # (None,60.0) '... not float' (no period); (0,None) '... strictly positive.'; original still rests at 50.
        original = self._rest_limit(Side.BID, limit_price=100, quantity=50)

        cases = [
            ((None, None), r"nothing to modify"),
            ((None, 50), r"no quantity to modify"),
            ((99.0, None), r"new_price must be int, not float\.$"),
            (
                (None, 60.0),
                r"new_quantity must be int, not float$",
            ),  # no trailing period
            ((0, None), r"new_price must be strictly positive\.$"),
        ]
        for (new_price, new_quantity), message in cases:
            with self.assertRaisesRegex(InvalidModificationError, message):
                self._modifier(original.order_id).modify(new_price, new_quantity)

        self.assertIn(original.order_id, self.orderbook)
        self.assertEqual(original.remaining_quantity, 50)


class TestModifyValidationOrdering(ModifyOrderExecutionBase):
    """price is validated before quantity: both-invalid surfaces the PRICE error."""

    def test_price_validated_before_quantity(self):
        # modify(-1, -1) -> 'new_price must be strictly positive.' (not the quantity message).
        original = self._rest_limit(Side.BID, limit_price=100, quantity=50)

        with self.assertRaisesRegex(
            InvalidModificationError, r"new_price must be strictly positive\."
        ):
            self._modifier(original.order_id).modify(new_price=-1, new_quantity=-1)


class TestModifierConstructionOnAbsentId(ModifyOrderExecutionBase):
    """constructing a modifier for an id absent from the book raises OrderNotFoundError."""

    def test_absent_id_raises_order_not_found(self):
        # ModifyOrderExecution(self.orderbook, 999999, self.factory) -> OrderNotFoundError.
        with self.assertRaises(OrderNotFoundError):
            ModifyOrderExecution(self.orderbook, 999999, self.factory)


if __name__ == "__main__":
    unittest.main()
