import unittest
import sys

sys.path.append("src")

from src.orderbook.orderbook import OrderBook
from src.orders.order import Order, OrderID, OrderSpec
from src.bookkeeping.custom_types import Side, ExecutionRule, OrderType
from src.orderbook.book_side import BidSide, AskSide
from src.orderbook.order_execution import LimitOrderExecution

# blend of unit-testing and integration testing


@unittest.skip
class TestOrderbook(unittest.TestCase):
    def test_case_get_side(self):

        orderbook = OrderBook()
        side_to_get = Side.BID

        side = orderbook.get_levels(side_to_get)

        self.assertEqual(type(side), BidSide)

    def test_case_get_opposite_side(self):

        orderbook = OrderBook()
        side_to_get = Side.BID

        side = orderbook.get_opposite_side_levels(side_to_get)

        self.assertEqual(type(side), AskSide)

    def test_case_get_bid_ask_mid(self):

        orderbook = OrderBook()

        order_spec = OrderSpec(
            Side.BID,
            OrderType.LIMIT,
            quantity=100,
            execution_rule=ExecutionRule.GTC,
            limit_price=100,
        )

        order1 = Order(order_spec, OrderID(0, 0))

        order_spec = OrderSpec(
            Side.ASK,
            OrderType.LIMIT,
            quantity=100,
            execution_rule=ExecutionRule.GTC,
            limit_price=101,
        )

        order2 = Order(order_spec, OrderID(1, 0))

        exec = LimitOrderExecution(order1, orderbook)
        exec.post_order()

        exec = LimitOrderExecution(order2, orderbook)
        exec.post_order()

        bid, ask, mid = orderbook.get_bid_ask_mid()

        self.assertEqual((bid, ask, mid), (100, 101, 100.5))

    def test_get_orderbook_state_two_sides(self):

        orderbook = _build_multiple_states_book(
            mid=100, half_spread=1, quantity=100, depth=2
        )

        states = orderbook.get_orderbook_state()

        target_bids = {101: (100, 1), 102: (100, 1)}
        target_asks = {99: (100, 1), 98: (100, 1)}

        self.assertDictEqual(states[0], target_bids)
        self.assertDictEqual(states[1], target_asks)

    def test_get_orderbook_top_of_book_state(self):

        orderbook = OrderBook()

        orderbook = _build_multiple_states_book(
            mid=100, half_spread=1, quantity=100, depth=1
        )

        states = orderbook.get_top_state()

        target_bids = {99: (100, 1)}
        target_asks = {101: (100, 1)}

        self.assertDictEqual(states[0], target_bids)
        self.assertDictEqual(states[1], target_asks)


def _build_multiple_states_book(
    mid: int = 100, half_spread: int = 1, quantity: int = 100, depth: int = 1
) -> OrderBook:

    orderbook = OrderBook()

    bid_orders, ask_orders = [], []

    for i in range(1, depth):
        bid_specs = OrderSpec(
            Side.BID,
            OrderType.LIMIT,
            quantity=quantity,
            execution_rule=ExecutionRule.GTC,
            limit_price=mid - i,
        )

        ask_specs = OrderSpec(
            Side.ASK,
            OrderType.LIMIT,
            quantity=100,
            execution_rule=ExecutionRule.GTC,
            limit_price=100 + i,
        )

        bid_orders.append(Order(bid_specs, OrderID(depth + i + 1, 0)))
        ask_orders.append(Order(ask_specs, OrderID(2 * depth + i + 1, 0)))

    orders = bid_orders + ask_orders

    for order in orders:
        order_exec = LimitOrderExecution(order, orderbook)
        order_exec.execute()

    return orderbook


if __name__ == "__main__":
    unittest.main()
