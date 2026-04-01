import unittest
import sys

# TODO
# fix import system accross package
# seems like test_order called first, appends src to path then subsequent test modules can test src
# individual test module will fail import otherwise
sys.path.append('src')

from orders.order import OrderSpec, Order, OrderID
from bookkeeping.custom_types import ExecutionRule, OrderType, Side

class TestOrder(unittest.TestCase):

    def test_case_init_order(self):

        order_spec = OrderSpec(Side.BID, OrderType.LIMIT, 
                         quantity=100, execution_rule=ExecutionRule.GTC,
                         limit_price=99)

        order = Order(order_spec, OrderID(0, 0))
        
        self.assertEqual(order.remaining_quantity, order.initial_quantity)

    def test_case_fill_quantity(self):

        order_spec = OrderSpec(Side.BID, OrderType.LIMIT, 
                         quantity=100, execution_rule=ExecutionRule.GTC,
                         limit_price = 99)
        
        order = Order(order_spec, OrderID(0, 0))
        
        to_fill = 50

        order.fill(to_fill)
        
        self.assertEqual(order.remaining_quantity, order.initial_quantity - to_fill)
        self.assertEqual(order.is_filled, False)

    def test_case_full_fill(self):

        order_spec = OrderSpec(Side.BID, OrderType.LIMIT, 
                         quantity=100, execution_rule=ExecutionRule.GTC,
                         limit_price = 99)
        
        order = Order(order_spec, OrderID(0, 0))
    
        to_fill = order.remaining_quantity
        order.fill(to_fill)

        self.assertEqual(order.remaining_quantity, 0)
        self.assertEqual(order.is_filled, True)
    
    def test_case_overfill(self):
        
        order_spec = OrderSpec(Side.BID, OrderType.LIMIT, 
                         quantity=100, execution_rule=ExecutionRule.GTC,
                         limit_price = 99)
        
        order = Order(order_spec, OrderID(0, 0))
        
        to_fill = order.remaining_quantity * 2
        order.fill(to_fill)
        self.assertEqual(order.remaining_quantity, 0)
        self.assertEqual(order.is_filled, True)

if __name__ == '__main__':
    unittest.main()