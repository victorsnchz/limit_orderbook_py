import unittest
import sys

sys.path.append('src')

from orderbook.orders_queue import OrdersQueue
from orders.order import Order, LimitOrder, MarketOrder, OrderID, OrderParameters
from bookkeeping.custom_types import ExecutionRules, OrderType, Side

class  TestOrdersQueue(unittest.TestCase):

    def test_case_add(self):

        orders_queue = OrdersQueue()

        order = LimitOrder(OrderParameters(Side.BID, 100), OrderID(0),
                               limit_price=100, execution_rules = ExecutionRules.GTC)
        orders_queue.add_order(order)

        self.assertEqual(order.get_id() in orders_queue.queue, True)

    def test_case_remove(self):

        orders_queue = OrdersQueue()
        order = LimitOrder(OrderParameters(Side.BID, 100), OrderID(0),
                               limit_price=100, execution_rules = ExecutionRules.GTC)
        
        orders_queue.add_order(order)

        orders_queue.remove_order(order)

        self.assertEqual(bool(orders_queue.queue), False)

    
if __name__ == '__main__':
    unittest.main()