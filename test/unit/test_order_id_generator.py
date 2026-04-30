import unittest
import sys
import threading

from lob.orders.order_id_generator import OrderIdGenerator


class TestOrderIdGeneratorInit(unittest.TestCase):
    def test_first_id_is_one(self):
        generator = OrderIdGenerator()
        self.assertEqual(generator._counter, 0)

    def test_custom_start_offset(self):
        custom_start = 7
        generator = OrderIdGenerator(custom_start)
        self.assertEqual(generator._counter, custom_start)


class TestOrderIdGeneratorIsolation(unittest.TestCase):
    def test_two_instances_have_independent_counter(self):
        generator1 = OrderIdGenerator()
        generator2 = OrderIdGenerator()
        generator1.next_id()
        self.assertNotEqual(generator1._counter, generator2._counter)

    def test_second_instance_starts_from_zero(self):
        generator1 = OrderIdGenerator()
        generator1.next_id()
        generator2 = OrderIdGenerator()
        self.assertEqual(generator2._counter, 0)


class TestOrderIdGeneratorThreadSafety(unittest.TestCase):
    def setUp(self):
        self.generator = OrderIdGenerator()
        self.results = []
        self.results_lock = threading.Lock()

    def _run_workers(self, num_threads: int, calls_per_thread: int) -> None:

        def worker():
            for _ in range(calls_per_thread):
                id_ = self.generator.next_id()
                with self.results_lock:
                    self.results.append(id_)

        threads = [threading.Thread(target=worker) for _ in range(num_threads)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

    def test_no_duplicate_ids_under_concurrent_access(self):
        self._run_workers(num_threads=10, calls_per_thread=100)
        self.assertEqual(len(self.results), len(set(self.results)))

    def test_total_ids_issued_equals_total_calls(self):
        num_threads, calls_per_thread = 10, 1000
        self._run_workers(num_threads=num_threads, calls_per_thread=calls_per_thread)
        self.assertEqual(len(self.results), num_threads * calls_per_thread)


if __name__ == "__main__":
    unittest.main()
