import unittest
from unittest.mock import MagicMock, PropertyMock, patch
from src.orderbook.order_execution import (
    OrderExecution,
    LimitOrderExecution,
    MarketOrderExecution,
    map_order_type_to_execution,
    execute_order,
)
from src.orderbook.orderbook import OrderBook
from src.orderbook.book_side import BookSide
from src.orders.order import Order, OrderSnapshot
from src.bookkeeping.custom_types import (
    Side,
    OrderType,
    FillStatus,
    EventKind,
    Event,
    AcceptedPayload,
    FilledPayload,
    PostedPayload,
)


class OrderExecutionBase(unittest.TestCase):
    """
    Shared fixture for OrderExecution tests.

    Provides:
        self.order: MagicMock(spec=Order)
        self.orderbook: MagicMock(spec=OrderBook)
        self.opposite_side: MagicMock(spec=BookSide) returned by
            self.orderbook.get_opposite_book_side()

    Subclasses instantiate a concrete OrderExecution under test (typically
    LimitOrderExecution or MarketOrderExecution) on top of these mocks.
    """

    def setUp(self):
        self.order = MagicMock(spec=Order)
        self.opposite_side = MagicMock(spec=BookSide)
        self.orderbook = MagicMock(spec=OrderBook)
        self.orderbook.get_opposite_book_side.return_value = self.opposite_side


class TestOrderExecutionInit(OrderExecutionBase):
    """
    Construction-time wiring for OrderExecution: stored references and initial
    flags. Uses LimitOrderExecution as a concrete stand-in for the abstract
    base.
    """

    def test_stores_order_reference(self):
        executor = LimitOrderExecution(self.order, self.orderbook)
        self.assertIs(executor.order, self.order)

    def test_stores_orderbook_reference(self):
        executor = LimitOrderExecution(self.order, self.orderbook)
        self.assertIs(executor.orderbook, self.orderbook)

    def test_resolves_opposite_book_side_from_orderbook(self):
        executor = LimitOrderExecution(self.order, self.orderbook)
        self.orderbook.get_opposite_book_side.assert_called_once()
        self.assertIs(executor._opposite_book_side, self.opposite_side)

    def test_posted_flag_initialised_false(self):
        executor = LimitOrderExecution(self.order, self.orderbook)
        self.assertFalse(executor._posted)

    def test_events_initialised_empty_list(self):
        executor = LimitOrderExecution(self.order, self.orderbook)
        self.assertEqual(executor._events, [])

    def test_execution_result_initialised_none(self):
        executor = LimitOrderExecution(self.order, self.orderbook)
        self.assertIsNone(executor._execution_result)

    def test_cannot_instantiate_abstract_base(self):
        with self.assertRaises(TypeError):
            OrderExecution(self.order, self.orderbook)


class TestExecute(OrderExecutionBase):
    """
    Public execute() entry point: delegation to _do_execute / _build_result and
    return value.
    """

    def _make_executor_with_mocked_pipeline(self, execution_result=None):
        executor = LimitOrderExecution(self.order, self.orderbook)
        executor._do_execute = MagicMock()
        executor._validate_order = MagicMock(return_value=AcceptedPayload(self.order))
        executor._build_result = MagicMock()
        executor._execution_result = execution_result
        return executor

    def test_execute_calls_do_execute(self):
        executor = self._make_executor_with_mocked_pipeline()
        executor.execute()
        executor._do_execute.assert_called_once()

    def test_execute_calls_build_result(self):
        executor = self._make_executor_with_mocked_pipeline()
        executor.execute()
        executor._build_result.assert_called_once()

    def test_execute_calls_do_execute_before_build_result(self):
        executor = self._make_executor_with_mocked_pipeline()
        call_log = []
        executor._do_execute.side_effect = lambda: call_log.append("do_execute")
        executor._build_result.side_effect = lambda: call_log.append("build_result")

        executor.execute()

        self.assertEqual(call_log, ["do_execute", "build_result"])

    def test_execute_returns_execution_result(self):
        sentinel = object()
        executor = self._make_executor_with_mocked_pipeline(execution_result=sentinel)
        self.assertIs(executor.execute(), sentinel)


class TestCanMatchOrder(OrderExecutionBase):
    """
    _can_match_order delegates to order.can_cross with the opposite side's best
    price (or None when the opposite side is empty).
    """

    def test_passes_best_price_when_opposite_non_empty(self):
        type(self.opposite_side).is_empty = PropertyMock(return_value=False)
        type(self.opposite_side).best_price = PropertyMock(return_value=99)
        self.order.can_cross.return_value = True
        executor = LimitOrderExecution(self.order, self.orderbook)

        executor._can_match_order()

        self.order.can_cross.assert_called_once_with(99)

    def test_passes_none_when_opposite_empty(self):
        type(self.opposite_side).is_empty = PropertyMock(return_value=True)
        self.order.can_cross.return_value = False
        executor = LimitOrderExecution(self.order, self.orderbook)

        executor._can_match_order()

        self.order.can_cross.assert_called_once_with(None)

    def test_does_not_access_best_price_when_opposite_empty(self):
        type(self.opposite_side).is_empty = PropertyMock(return_value=True)
        type(self.opposite_side).best_price = PropertyMock(
            side_effect=AssertionError("best_price should not be accessed")
        )
        self.order.can_cross.return_value = False
        executor = LimitOrderExecution(self.order, self.orderbook)

        executor._can_match_order()

    def test_returns_can_cross_result(self):
        type(self.opposite_side).is_empty = PropertyMock(return_value=False)
        type(self.opposite_side).best_price = PropertyMock(return_value=99)
        sentinel = object()
        self.order.can_cross.return_value = sentinel
        executor = LimitOrderExecution(self.order, self.orderbook)

        self.assertIs(executor._can_match_order(), sentinel)


class TestMatch(OrderExecutionBase):
    """
    _match loop: repeatedly calls orderbook.fill_top while order is unfilled and
    can match, appending FILLED events for every returned payload.
    """

    def _make_executor(self):
        executor = LimitOrderExecution(self.order, self.orderbook)
        executor._events = []
        return executor

    def test_no_op_when_order_already_filled(self):
        self.order.is_filled = True
        executor = self._make_executor()
        executor._can_match_order = MagicMock(return_value=True)

        executor._match()

        self.orderbook.fill_top.assert_not_called()
        self.assertEqual(executor._events, [])

    def test_no_op_when_cannot_match(self):
        self.order.is_filled = False
        executor = self._make_executor()
        executor._can_match_order = MagicMock(return_value=False)

        executor._match()

        self.orderbook.fill_top.assert_not_called()
        self.assertEqual(executor._events, [])

    def test_calls_fill_top_with_aggressor(self):
        self.order.is_filled = False
        executor = self._make_executor()
        executor._can_match_order = MagicMock(side_effect=[True, False])
        self.orderbook.fill_top.return_value = []

        executor._match()

        self.orderbook.fill_top.assert_called_once_with(self.order)

    def test_appends_filled_event_per_payload(self):
        self.order.is_filled = False
        executor = self._make_executor()
        executor._can_match_order = MagicMock(side_effect=[True, False])
        payload1 = MagicMock(spec=FilledPayload)
        payload2 = MagicMock(spec=FilledPayload)
        self.orderbook.fill_top.return_value = [payload1, payload2]

        executor._match()

        self.assertEqual(len(executor._events), 2)
        self.assertTrue(all(e.kind == EventKind.FILLED for e in executor._events))

    def test_filled_events_carry_returned_payloads(self):
        self.order.is_filled = False
        executor = self._make_executor()
        executor._can_match_order = MagicMock(side_effect=[True, False])
        payload = MagicMock(spec=FilledPayload)
        self.orderbook.fill_top.return_value = [payload]

        executor._match()

        self.assertIs(executor._events[0].payload, payload)

    def test_loops_until_order_filled(self):
        self.order.is_filled = False
        executor = self._make_executor()
        executor._can_match_order = MagicMock(return_value=True)

        def fill_top_side_effect(_):
            if self.orderbook.fill_top.call_count >= 2:
                self.order.is_filled = True
            return []

        self.orderbook.fill_top.side_effect = fill_top_side_effect

        executor._match()

        self.assertEqual(self.orderbook.fill_top.call_count, 2)

    def test_loops_until_cannot_match(self):
        self.order.is_filled = False
        executor = self._make_executor()
        executor._can_match_order = MagicMock(side_effect=[True, True, False])
        self.orderbook.fill_top.return_value = []

        executor._match()

        self.assertEqual(self.orderbook.fill_top.call_count, 2)

    def test_no_filled_events_when_fill_top_returns_empty(self):
        self.order.is_filled = False
        executor = self._make_executor()
        executor._can_match_order = MagicMock(side_effect=[True, False])
        self.orderbook.fill_top.return_value = []

        executor._match()

        self.assertEqual(executor._events, [])


class TestRecordAccepted(OrderExecutionBase):
    """
    _record_accepted appends a single ACCEPTED event built from the aggressor
    snapshot.
    """

    def setUp(self):
        super().setUp()

        self.snapshot = _make_snapshot()
        self.order.snapshot.return_value = self.snapshot
        self.executor = LimitOrderExecution(self.order, self.orderbook)
        self.executor._events = []

    def test_appends_single_event(self):

        self.executor._record_accepted(AcceptedPayload(self.snapshot))

        self.assertEqual(len(self.executor._events), 1)

    def test_event_kind_is_accepted(self):

        self.executor._record_accepted(AcceptedPayload(self.snapshot))

        self.assertEqual(self.executor._events[0].kind, EventKind.ACCEPTED)

    def test_event_payload_is_accepted_payload_with_snapshot(self):

        self.executor._record_accepted(AcceptedPayload(self.snapshot))

        self.assertEqual(
            self.executor._events[0].payload, AcceptedPayload(self.snapshot)
        )

    def test_does_not_set_posted_flag(self):

        self.executor._record_accepted(AcceptedPayload(self.snapshot))

        self.assertFalse(self.executor._posted)


class TestRecordPosted(OrderExecutionBase):
    """
    _record_posted appends a single POSTED event and flips the _posted flag.
    """

    def _make_executor(self, snapshot):
        self.order.snapshot.return_value = snapshot
        executor = LimitOrderExecution(self.order, self.orderbook)
        executor._events = []
        return executor

    def test_appends_single_event(self):
        executor = self._make_executor(_make_snapshot())

        executor._record_posted()

        self.assertEqual(len(executor._events), 1)

    def test_event_kind_is_posted(self):
        executor = self._make_executor(_make_snapshot())

        executor._record_posted()

        self.assertEqual(executor._events[0].kind, EventKind.POSTED)

    def test_event_payload_is_posted_payload_with_snapshot(self):
        snapshot = _make_snapshot()
        executor = self._make_executor(snapshot)

        executor._record_posted()

        self.assertEqual(executor._events[0].payload, PostedPayload(snapshot))

    def test_sets_posted_flag_true(self):
        executor = self._make_executor(_make_snapshot())

        executor._record_posted()

        self.assertTrue(executor._posted)


class TestComputeStatus(OrderExecutionBase):
    """
    _compute_status maps the aggressor's residual quantity to a FillStatus.
    """

    def test_returns_filled_when_order_is_filled(self):
        self.order.is_filled = True
        executor = LimitOrderExecution(self.order, self.orderbook)

        self.assertEqual(executor._compute_status(), FillStatus.FILLED)

    def test_returns_unfilled_when_no_quantity_consumed(self):
        self.order.is_filled = False
        self.order.initial_quantity = 100
        self.order.remaining_quantity = 100
        executor = LimitOrderExecution(self.order, self.orderbook)

        self.assertEqual(executor._compute_status(), FillStatus.UNFILLED)

    def test_returns_partially_filled_when_some_quantity_consumed(self):
        self.order.is_filled = False
        self.order.initial_quantity = 100
        self.order.remaining_quantity = 60
        executor = LimitOrderExecution(self.order, self.orderbook)

        self.assertEqual(executor._compute_status(), FillStatus.PARTIALLY_FILLED)


class TestBuildResult(OrderExecutionBase):
    """
    _build_result composes the ExecutionReport / ExecutionResult from the
    aggressor snapshot, recorded fills, posted flag and computed status.
    """

    def _make_executor(self, snapshot, events=None, filled_payloads=None):
        self.order.snapshot.return_value = snapshot
        executor = LimitOrderExecution(self.order, self.orderbook)
        executor._events = [] if events is None else events
        # executor._filled_payloads = [] if filled_payloads is None else filled_payloads
        return executor

    def test_report_aggressor_is_order_snapshot(self):
        snapshot = _make_snapshot()
        executor = self._make_executor(snapshot)
        executor._compute_status = MagicMock(return_value=FillStatus.UNFILLED)

        executor._build_result()

        self.assertEqual(executor._execution_result.report.aggressor, snapshot)

    def test_report_posted_reflects_flag(self):
        executor = self._make_executor(_make_snapshot())
        executor._posted = True
        executor._compute_status = MagicMock(return_value=FillStatus.UNFILLED)

        executor._build_result()

        self.assertTrue(executor._execution_result.report.posted)

    def test_report_status_uses_compute_status(self):
        executor = self._make_executor(_make_snapshot())
        executor._compute_status = MagicMock(return_value=FillStatus.PARTIALLY_FILLED)

        executor._build_result()

        self.assertEqual(
            executor._execution_result.report.status, FillStatus.PARTIALLY_FILLED
        )

    def test_result_events_match_recorded_events(self):
        events = [MagicMock(spec=Event), MagicMock(spec=Event)]
        executor = self._make_executor(_make_snapshot(), events=events)
        executor._compute_status = MagicMock(return_value=FillStatus.FILLED)

        executor._build_result()

        self.assertEqual(executor._execution_result.events, events)

    def test_assigns_execution_result_attribute(self):
        executor = self._make_executor(_make_snapshot())
        executor._compute_status = MagicMock(return_value=FillStatus.UNFILLED)

        executor._build_result()

        self.assertIsNotNone(executor._execution_result)


class TestGetExecutionResult(OrderExecutionBase):
    """
    get_execution_result returns the cached ExecutionResult, or raises if
    execute() has not yet been called.
    """

    def test_raises_runtime_error_before_execute(self):
        executor = LimitOrderExecution(self.order, self.orderbook)
        executor._execution_result = None

        with self.assertRaises(RuntimeError):
            executor.get_execution_result()

    def test_returns_execution_result_after_execute(self):
        executor = LimitOrderExecution(self.order, self.orderbook)
        sentinel = object()
        executor._execution_result = sentinel

        self.assertIs(executor.get_execution_result(), sentinel)

    def test_returns_same_instance_on_repeat_calls(self):
        executor = LimitOrderExecution(self.order, self.orderbook)
        sentinel = object()
        executor._execution_result = sentinel

        first = executor.get_execution_result()
        second = executor.get_execution_result()

        self.assertIs(first, second)


class LimitOrderExecutionBase(OrderExecutionBase):
    """
    Fixture for LimitOrderExecution: aggressor is a LIMIT order; orderbook
    mocks fill_top and post_order.
    """

    def setUp(self):
        super().setUp()
        self.order.order_type = OrderType.LIMIT


class TestLimitOrderExecutionDoExecute(LimitOrderExecutionBase):
    """
    LimitOrderExecution._do_execute: matches first, then posts the residual if
    not fully filled.
    """

    def _make_executor(self):
        executor = LimitOrderExecution(self.order, self.orderbook)
        executor._events = []
        executor._match = MagicMock()
        return executor

    def test_calls_match(self):
        self.order.is_filled = True
        executor = self._make_executor()

        executor._do_execute()

        executor._match.assert_called_once()

    def test_posts_residual_when_not_filled(self):
        self.order.is_filled = False
        executor = self._make_executor()

        executor._do_execute()

        self.orderbook.post_order.assert_called_once_with(self.order)

    def test_does_not_post_when_fully_filled(self):
        self.order.is_filled = True
        executor = self._make_executor()

        executor._do_execute()

        self.orderbook.post_order.assert_not_called()

    def test_records_posted_event_when_posted(self):
        self.order.is_filled = False
        self.order.snapshot.return_value = _make_snapshot()
        executor = self._make_executor()

        executor._do_execute()

        self.assertTrue(executor._posted)
        self.assertTrue(any(e.kind == EventKind.POSTED for e in executor._events))

    def test_does_not_record_posted_event_when_fully_filled(self):
        self.order.is_filled = True
        executor = self._make_executor()

        executor._do_execute()

        self.assertFalse(executor._posted)
        self.assertFalse(any(e.kind == EventKind.POSTED for e in executor._events))

    def test_match_runs_before_post_order(self):
        self.order.is_filled = False
        executor = self._make_executor()
        call_log = []
        executor._match.side_effect = lambda: call_log.append("match")
        self.orderbook.post_order.side_effect = lambda *a, **kw: call_log.append(
            "post_order"
        )

        executor._do_execute()

        self.assertEqual(call_log, ["match", "post_order"])


class MarketOrderExecutionBase(OrderExecutionBase):
    """
    Fixture for MarketOrderExecution: aggressor is a MARKET order; orderbook
    mocks fill_top.
    """

    def setUp(self):
        super().setUp()
        self.order.order_type = OrderType.MARKET


class TestMarketOrderExecutionDoExecute(MarketOrderExecutionBase):
    """
    MarketOrderExecution._do_execute: only matches; never posts to the book
    regardless of residual quantity.
    """

    def _make_executor(self):
        executor = MarketOrderExecution(self.order, self.orderbook)
        executor._events = []
        executor._match = MagicMock()
        return executor

    def test_calls_match(self):
        executor = self._make_executor()

        executor._do_execute()

        executor._match.assert_called_once()

    def test_does_not_post_when_partially_filled(self):
        self.order.is_filled = False
        self.order.initial_quantity = 100
        self.order.remaining_quantity = 60
        executor = self._make_executor()

        executor._do_execute()

        self.orderbook.post_order.assert_not_called()

    def test_does_not_post_when_fully_unfilled(self):
        self.order.is_filled = False
        self.order.initial_quantity = 100
        self.order.remaining_quantity = 100
        executor = self._make_executor()

        executor._do_execute()

        self.orderbook.post_order.assert_not_called()

    def test_does_not_record_posted_event(self):
        self.order.is_filled = False
        executor = self._make_executor()

        executor._do_execute()

        self.assertFalse(any(e.kind == EventKind.POSTED for e in executor._events))

    def test_posted_flag_remains_false(self):
        self.order.is_filled = False
        executor = self._make_executor()

        executor._do_execute()

        self.assertFalse(executor._posted)


class TestOrderTypeExecutionMap(unittest.TestCase):
    """
    map_order_type_to_execution wires OrderType values to their concrete
    OrderExecution subclasses.
    """

    def test_limit_maps_to_limit_order_execution(self):
        self.assertIs(map_order_type_to_execution[OrderType.LIMIT], LimitOrderExecution)

    def test_market_maps_to_market_order_execution(self):
        self.assertIs(
            map_order_type_to_execution[OrderType.MARKET], MarketOrderExecution
        )

    def test_map_covers_all_order_types(self):
        self.assertEqual(set(map_order_type_to_execution.keys()), set(OrderType))


class TestExecuteOrder(unittest.TestCase):
    """
    Module-level execute_order dispatches to the appropriate OrderExecution
    subclass based on the aggressor's order_type.
    """

    def setUp(self):
        self.order = MagicMock(spec=Order)
        self.orderbook = MagicMock(spec=OrderBook)
        self.orderbook.get_opposite_book_side.return_value = MagicMock(spec=BookSide)

    def test_dispatches_limit_order_to_limit_execution(self):
        self.order.order_type = OrderType.LIMIT
        mock_cls = MagicMock()

        with patch.dict(
            "src.orderbook.order_execution.map_order_type_to_execution",
            {OrderType.LIMIT: mock_cls},
        ):
            execute_order(self.order, self.orderbook)

        mock_cls.assert_called_once_with(self.order, self.orderbook)

    def test_dispatches_market_order_to_market_execution(self):
        self.order.order_type = OrderType.MARKET
        mock_cls = MagicMock()

        with patch.dict(
            "src.orderbook.order_execution.map_order_type_to_execution",
            {OrderType.MARKET: mock_cls},
        ):
            execute_order(self.order, self.orderbook)

        mock_cls.assert_called_once_with(self.order, self.orderbook)

    def test_calls_execute_on_executor(self):
        self.order.order_type = OrderType.LIMIT
        mock_cls = MagicMock()

        with patch.dict(
            "src.orderbook.order_execution.map_order_type_to_execution",
            {OrderType.LIMIT: mock_cls},
        ):
            execute_order(self.order, self.orderbook)

        mock_cls.return_value.execute.assert_called_once()

    def test_unknown_order_type_raises(self):
        self.order.order_type = "UNKNOWN"

        with self.assertRaises(KeyError):
            execute_order(self.order, self.orderbook)


def _make_limit_order(
    order_id=1,
    side: Side = Side.BID,
    limit_price: int = 100,
    initial_quantity: int = 100,
    remaining_quantity: int = 100,
    is_filled: bool = False,
):
    order = MagicMock(spec=Order)
    order.order_id = order_id
    order.side = side
    order.order_type = OrderType.LIMIT
    order.limit_price = limit_price
    order.initial_quantity = initial_quantity
    order.remaining_quantity = remaining_quantity
    order.is_filled = is_filled
    return order


def _make_market_order(
    order_id=1,
    side: Side = Side.BID,
    initial_quantity: int = 100,
    remaining_quantity: int = 100,
    is_filled: bool = False,
):
    order = MagicMock(spec=Order)
    order.order_id = order_id
    order.side = side
    order.order_type = OrderType.MARKET
    order.initial_quantity = initial_quantity
    order.remaining_quantity = remaining_quantity
    order.is_filled = is_filled
    return order


def _make_snapshot(
    side: Side = Side.BID,
    order_type: OrderType = OrderType.LIMIT,
    initial_quantity: int = 100,
    remaining_quantity: int = 100,
    order_id: int = 1,
    user_id: int = 0,
    limit_price: int = 100,
):
    return OrderSnapshot(
        side=side,
        order_type=order_type,
        initial_quantity=initial_quantity,
        remaining_quantity=remaining_quantity,
        order_id=order_id,
        user_id=user_id,
        limit_price=limit_price,
    )


if __name__ == "__main__":
    unittest.main()
