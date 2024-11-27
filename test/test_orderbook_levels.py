import unittest

from price_levels import PriceLevels
from order import Order
from custom_types import OrderType,OrderExecutionRules, BookSide



class TestPriceLevels(unittest.TestCase):
    
    def test_case_empty(self):

        price_levels = PriceLevels(BookSide.ASK)

        self.assertEqual(price_levels.is_empty(), True)

    def test_case_add_order(self):

        price_levels = PriceLevels(BookSide.ASK)
        order = Order(type =  OrderType.LIMIT, execution_rules= OrderExecutionRules.GOOD_TILL_CANCELLED, 
                      side = BookSide.ASK, initial_quantity=100, price = 100)
        price_levels.post_order(order)

        self.assertEqual(order.id in price_levels.levels[order.price].queue, True)

    def test_case_add_order(self):

        price_levels = PriceLevels(BookSide.ASK)
        order = Order(type =  OrderType.LIMIT, execution_rules= OrderExecutionRules.GOOD_TILL_CANCELLED, 
                      side = BookSide.ASK, initial_quantity=100, price = 100)
        
        price_levels.post_order(order)

        self.assertEqual(order.id in price_levels.levels[order.price].queue, True)

    def test_case_top_of_book(self):

        price_levels = PriceLevels(BookSide.ASK)

        order = Order(type =  OrderType.LIMIT, execution_rules= OrderExecutionRules.GOOD_TILL_CANCELLED, 
                      side = BookSide.ASK, initial_quantity=100, price = 101)
        order2 = Order(type =  OrderType.LIMIT, execution_rules= OrderExecutionRules.GOOD_TILL_CANCELLED, 
                      side = BookSide.ASK, initial_quantity=99, price = 100)
        
        price_levels.post_order(order)
        price_levels.post_order(order2)

        self.assertEqual(price_levels.top_of_book(), order2.price)

    def test_case_cancel_order(self):

        order = Order(type =  OrderType.LIMIT, execution_rules= OrderExecutionRules.GOOD_TILL_CANCELLED, 
                      side = BookSide.ASK, initial_quantity=100, price = 101)
        order2 = Order(type =  OrderType.LIMIT, execution_rules= OrderExecutionRules.GOOD_TILL_CANCELLED, 
                      side = BookSide.ASK, initial_quantity=99, price = 100)

        order3 = Order(type =  OrderType.LIMIT, execution_rules= OrderExecutionRules.GOOD_TILL_CANCELLED, 
                      side = BookSide.ASK, initial_quantity=99, price = 98)
        
        price_levels = PriceLevels(BookSide.ASK)
        price_levels.post_order(order)
        price_levels.post_order(order2)
        price_levels.post_order(order3)

        self.assertEqual(order3.id in price_levels.levels[order3.price].queue, True)
        
        price_levels.cancel_order(order3)
        self.assertEqual(order3.id in price_levels.levels_ordered, False)
        self.assertEqual(order3.id in price_levels.levels, False)