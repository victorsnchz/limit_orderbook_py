import unittest
import sys

sys.path.append("src")
from src.orderbook.orders_queue import OrdersQueue
from src.orders.order import Order, OrderSpec, OrderID
from src.bookkeeping.custom_types import Side, ExecutionRule, OrderType


class TestOrdersQueue(unittest.TestCase):
    def setUp(self):
        self.queue = OrdersQueue()
        self.order1 = _make_order(1)
        self.order2 = _make_order(2)

    def test_is_empty_true_on_init(self):
        self.assertTrue(self.queue.is_empty)

    def test_is_empty_false_after_add(self):
        self.queue.add_order(self.order1)
        self.assertFalse(self.queue.is_empty)

    def is_empty_true_after_add_then_remove(self):
        self.queue.add_order(self.order1)
        self.queue.remove_order(self.order1)
        self.assertTrue(self.queue.is_empty)

    def test_add_single_order(self):
        self.queue.add_order(self.order1)
        self.assertIn(self.order1.order_id, self.queue.queue)
        self.assertEqual(self.queue.queue[self.order1.order_id], self.order1)

    def test_add_duplicate_id_raises(self):
        # adding two orders with same order_id should raise RuntimeError
        self.queue.add_order(self.order1)
        with self.assertRaises(RuntimeError):
            self.queue.add_order(self.order1)

    def test_add_multiple_orders_all_present(self):
        self.queue.add_order(self.order1)
        self.queue.add_order(self.order2)
        self.assertIn(self.order1.order_id, self.queue.queue)
        self.assertIn(self.order2.order_id, self.queue.queue)
        self.assertEqual(self.queue.queue[self.order1.order_id], self.order1)
        self.assertEqual(self.queue.queue[self.order2.order_id], self.order2)

    def test_remove_returns_the_order(self):

        self.queue.add_order(self.order1)
        self.assertEqual(self.queue.remove_order(self.order1), self.order1)

    def test_remove_last_order_queue_empty(self):
        self.queue.add_order(self.order1)
        self.queue.remove_order(self.order1)
        self.assertTrue(self.queue.is_empty)

    def test_remove_leaves_others_intact(self):
        self.queue.add_order(self.order1)
        self.queue.add_order(self.order2)
        self.queue.remove_order(self.order1)
        self.assertFalse(self.queue.is_empty)
        self.assertIn(self.order2.order_id, self.queue.queue)
        self.assertEqual(self.queue.queue[self.order2.order_id], self.order2)

    def test_remove_non_existent_raises(self):
        self.queue.add_order(self.order1)
        with self.assertRaises(KeyError):
            self.queue.remove_order(self.order2)

    def test_next_returns_first_inserted(self):
        self.queue.add_order(self.order1)
        self.queue.add_order(self.order2)
        self.assertEqual(self.queue.next_order_to_execute, self.order1)

    def test_next_does_not_modify(self):
        self.queue.add_order(self.order1)
        self.queue.add_order(self.order2)
        self.queue.next_order_to_execute
        self.assertEqual(self.queue.next_order_to_execute, self.order1)

    def test_next_on_empty_raises(self):
        with self.assertRaises(StopIteration):
            self.queue.next_order_to_execute


class TestOrdersQueueFIFO(unittest.TestCase):
    def setUp(self):
        self.queue = OrdersQueue()
        self.order1 = _make_order(order_id=1)
        self.order2 = _make_order(order_id=2)
        self.order3 = _make_order(order_id=3)

    def test_fifo_two_orders(self):
        self.queue.add_order(self.order1)
        self.queue.add_order(self.order2)
        self.queue.remove_order(self.order1)
        self.assertEqual(self.queue.next_order_to_execute, self.order2)

    def test_fifo_three_orders_full_drain(self):
        self.queue.add_order(self.order1)
        self.queue.add_order(self.order2)
        self.queue.add_order(self.order3)
        self.assertEqual(self.queue.next_order_to_execute, self.order1)
        self.queue.remove_order(self.order1)
        self.assertEqual(self.queue.next_order_to_execute, self.order2)
        self.queue.remove_order(self.order2)
        self.assertEqual(self.queue.next_order_to_execute, self.order3)

    def test_fifo_not_affected_by_order_id_value(self):
        self.queue.add_order(self.order3)
        self.queue.add_order(self.order1)
        self.assertEqual(self.queue.next_order_to_execute, self.order3)


def _make_order(order_id=1):
    order_spec = OrderSpec(
        side=Side.BID,
        order_type=OrderType.LIMIT,
        quantity=100,
        execution_rule=ExecutionRule.GTC,
        limit_price=100,
    )
    order_id = OrderID(order_id=order_id, user_id=0)
    return Order(order_spec, order_id)


if __name__ == "__main__":
    unittest.main()
