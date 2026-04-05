import unittest
import sys
import threading

from src.orders.order_id_generator import OrderIdGenerator


class TestOrderIdGeneratorInit(unittest.TestCase):
    def test_first_id_is_one(self): ...
    def test_custom_start_offset(self): ...


class TTestOrderIdGeneratorIsolation(unittest.TestCase):
    def test_two_instances_have_independent_counter(self): ...
    def test_second_instance_starts_from_one(self): ...


class TestOrderIdGeneratorThreadSafety(unittest.TestCase):
    def test_no_duplicate_ids_under_concurrent_access(self): ...
    def test_total_ids_issued_equals_total_calls(self): ...


if __name__ == "__main__":
    unittest.main()
