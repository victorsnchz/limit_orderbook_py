import unittest
from orders_queue import OrdersQueue
from order import Order
from custom_types import TradeSide, OrderExecutionRules, BookSide

class TestBookSide(unittest.TestCase):
    
    queue = OrdersQueue()
    
    def test_case_add_order(self):
        order = Order(TradeSide.BUY, execution_rules= OrderExecutionRules.FILL_OR_KILL, 
                      side = BookSide.ASK, initial_quantity=100, price = 100)
        
        self.queue.add_order(order)

        self.assertEqual(order.id in self.queue.levels, True)
