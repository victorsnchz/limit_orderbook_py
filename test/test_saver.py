import unittest
import sys
import os
from pathlib import Path

# sys.path.append('../')
sys.path.append("src")

from src.orders.order import OrderID, Order, OrderSpec
from src.bookkeeping.custom_types import Side, ExecutionRule, OrderType
from src.orderbook.order_execution import LimitOrderExecution
from src.orderbook.orderbook import OrderBook
from src.bookkeeping.saver import Saver

import shutil
import bookkeeping.files_manager as files_manager


test_saver_data_dir = (
    f"{os.path.abspath(os.path.dirname(__file__))}/../test_data/test_saver"
)
saver = Saver(data_directory=test_saver_data_dir)


class SaverTestBase(unittest.TestCase):
    test_case_dir: str

    def setUp(self):

        base_dir = Path(test_saver_data_dir) / self.test_case_dir
        for entry in base_dir.iterdir():
            results_path = entry / "results"
            if results_path.is_dir():
                shutil.rmtree(results_path)

    def assert_saver_output(self, orderbook: OrderBook, save_fn, test_dir: str):

        save_fn(orderbook, path=f"{self.test_case_dir}/{test_dir}/results")

        base = Path(test_saver_data_dir) / self.test_case_dir / test_dir

        for side in ("bid", "ask"):
            pairs = list(
                files_manager.read_two_csvs(
                    base / "targets" / f"{side}.csv",
                    base / "results" / f"{side}.csv",
                )
            )

        self.assertGreater(len(pairs), 0, f"{side} CSV comparison yielded no rows")

        for target, result in pairs:
            self.assertEqual(target, result)


@unittest.skip
class TestSaverBookState(SaverTestBase):
    test_case_dir = "book_state"

    def test_case_one_state(self):

        orderbook = _build_one_state_book()
        self.assert_saver_output(orderbook, saver.orderbook_state_to_csv, "one_state")

    def test_case_multiple_states(self):

        orderbook = _build_multiple_states_book()
        self.assert_saver_output(
            orderbook, saver.orderbook_state_to_csv, "multiple_states"
        )


@unittest.skip
class TestSaverTopOfBookState(SaverTestBase):
    test_case_dir = "top_of_book_state"

    def test_case_one_state(self):

        orderbook = _build_one_state_book()
        self.assert_saver_output(orderbook, saver.orderbook_state_to_csv, "one_state")

    def test_case_multiple_states(self):

        orderbook = _build_multiple_states_book()
        self.assert_saver_output(
            orderbook, saver.orderbook_state_to_csv, "multiple_states"
        )


@unittest.skip
class TestSaverOrders(unittest.TestCase):
    pass


def _build_one_state_book() -> OrderBook:
    orderbook = OrderBook()

    bid_spec = OrderSpec(
        Side.BID,
        OrderType.LIMIT,
        quantity=100,
        execution_rule=ExecutionRule.GTC,
        limit_price=99,
    )

    ask_spec = OrderSpec(
        Side.ASK,
        OrderType.LIMIT,
        quantity=100,
        execution_rule=ExecutionRule.GTC,
        limit_price=101,
    )

    bid1 = Order(bid_spec, OrderID(0, 0))

    ask1 = Order(ask_spec, OrderID(1, 0))

    orders = [bid1, ask1]

    for order in orders:
        order_exec = LimitOrderExecution(order, orderbook)
        order_exec.execute()

    return orderbook


def _build_multiple_states_book() -> OrderBook:
    orderbook = OrderBook()

    bid_specs = [
        OrderSpec(
            Side.BID,
            OrderType.LIMIT,
            quantity=100,
            execution_rule=ExecutionRule.GTC,
            limit_price=100 - i,
        )
        for i in range(1, 4)
    ]

    ask_specs = [
        OrderSpec(
            Side.ASK,
            OrderType.LIMIT,
            quantity=100,
            execution_rule=ExecutionRule.GTC,
            limit_price=100 + i,
        )
        for i in range(1, 4)
    ]

    bid_orders = [
        Order(bid_spec, OrderID(100 + 1, 0)) for i, bid_spec in enumerate(bid_specs)
    ]

    ask_orders = [
        Order(ask_spec, OrderID(1000 + i, 0)) for i, ask_spec in enumerate(ask_specs)
    ]

    orders = bid_orders + ask_orders

    for order in orders:
        order_exec = LimitOrderExecution(order, orderbook)
        order_exec.execute()

    return orderbook


if __name__ == "__main__":
    unittest.main()
