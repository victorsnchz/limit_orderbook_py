import unittest
import sys
import datetime
import os
import csv

#sys.path.append('../')
sys.path.append('src')

from price_levels import Bids
from order import LimitOrder, OrderParameters, OrderID
from custom_types import Side, ExecutionRules
from order_execution import LimitOrderExecution
from analytics import Analytics
from orderbook import OrderBook
from saver import Saver

import shutil
import files_manager


test_saver_data_dir = f'{os.path.abspath(os.path.dirname(__file__))}/../test_data/test_saver'
saver = Saver(data_directory=test_saver_data_dir)

class TestSaverBookState(unittest.TestCase):

    test_case_dir = 'book_state'

    def test_case_one_state(self):

        orderbook = OrderBook()

        bid1 = LimitOrder(OrderParameters(Side.BID, 100), OrderID(0),
                                limit_price=100, execution_rules = ExecutionRules.GTC)

        ask1 = LimitOrder(OrderParameters(Side.ASK, 100), OrderID(2),
                                limit_price=110, execution_rules = ExecutionRules.GTC)

        orders = [bid1, ask1]

        for order in orders:
            exec = LimitOrderExecution(order, orderbook)
            exec.execute()

        test_dir = 'one_state'
        saver.orderbook_state_to_csv(orderbook, path = f'{self.test_case_dir}/{test_dir}/results')

        target_bid, target_ask = files_manager.get_target_names_bid_ask(test_saver_data_dir, self.test_case_dir, test_dir)
        result_bid, result_ask = files_manager.get_results_names_bid_ask(test_saver_data_dir, self.test_case_dir, test_dir)

        for target_bid_state, results_bid_state in files_manager.read_two_csvs(f'{target_bid}.csv', f'{result_bid}.csv'):
            self.assertEqual(target_bid_state, results_bid_state)

        for target_ask_state, results_ask_state in files_manager.read_two_csvs(f'{target_ask}.csv', f'{result_ask}.csv'):
            self.assertEqual(target_ask_state, results_ask_state)

        shutil.rmtree(f'{test_saver_data_dir}/{self.test_case_dir}/{test_dir}/results')

    def test_case_multiple_states(self):

        orderbook = OrderBook()

        bid1 = LimitOrder(OrderParameters(Side.BID, 100), OrderID(0),
                            limit_price=100, execution_rules = ExecutionRules.GTC)
        bid2 = LimitOrder(OrderParameters(Side.BID, 200), OrderID(1),
                                limit_price=100, execution_rules = ExecutionRules.GTC)
        bid3 = LimitOrder(OrderParameters(Side.BID, 100), OrderID(0),
                                limit_price=105, execution_rules = ExecutionRules.GTC)

        ask1 = LimitOrder(OrderParameters(Side.ASK, 100), OrderID(2),
                                limit_price=110, execution_rules = ExecutionRules.GTC)
        ask2 = LimitOrder(OrderParameters(Side.ASK, 100), OrderID(3),
                                limit_price=120, execution_rules = ExecutionRules.GTC)

        orders = [bid1, bid2, bid3, ask1, ask2]

        for order in orders:
            exec = LimitOrderExecution(order, orderbook)
            exec.execute()


        test_dir = 'multiple_states'
        saver.orderbook_state_to_csv(orderbook, path = f'{self.test_case_dir}/{test_dir}/results')

        target_bid, target_ask = files_manager.get_target_names_bid_ask(test_saver_data_dir, self.test_case_dir, test_dir)
        result_bid, result_ask = files_manager.get_results_names_bid_ask(test_saver_data_dir, self.test_case_dir, test_dir)

        for target_bid_state, results_bid_state in files_manager.read_two_csvs(f'{target_bid}.csv', f'{result_bid}.csv'):
            self.assertEqual(target_bid_state, results_bid_state)

        for target_ask_state, results_ask_state in files_manager.read_two_csvs(f'{target_ask}.csv', f'{result_ask}.csv'):
            self.assertEqual(target_ask_state, results_ask_state)

        shutil.rmtree(f'{test_saver_data_dir}/{self.test_case_dir}/{test_dir}/results')

class TestSaverTopOfBookState(unittest.TestCase):
    test_case_dir = 'top_of_book_state'

    def test_case_one_state(self):
        
        orderbook = OrderBook()

        bid1 = LimitOrder(OrderParameters(Side.BID, 100), OrderID(0),
                                limit_price=100, execution_rules = ExecutionRules.GTC)

        ask1 = LimitOrder(OrderParameters(Side.ASK, 100), OrderID(2),
                                limit_price=110, execution_rules = ExecutionRules.GTC)

        orders = [bid1, ask1]

        for order in orders:
            exec = LimitOrderExecution(order, orderbook)
            exec.execute()


        test_dir = 'one_state'
        saver.top_of_book_state_to_csv(orderbook, path = f'{self.test_case_dir}/{test_dir}/results')

        target_bid, target_ask = files_manager.get_target_names_bid_ask(test_saver_data_dir, self.test_case_dir, test_dir)
        result_bid, result_ask = files_manager.get_results_names_bid_ask(test_saver_data_dir, self.test_case_dir, test_dir)

        for target_bid_state, results_bid_state in files_manager.read_two_csvs(f'{target_bid}.csv', f'{result_bid}.csv'):
            self.assertEqual(target_bid_state, results_bid_state)

        for target_ask_state, results_ask_state in files_manager.read_two_csvs(f'{target_ask}.csv', f'{result_ask}.csv'):
            self.assertEqual(target_ask_state, results_ask_state)

        shutil.rmtree(f'{test_saver_data_dir}/{self.test_case_dir}/{test_dir}/results')

    def test_case_multiple_states(self):

        orderbook = OrderBook()

        bid1 = LimitOrder(OrderParameters(Side.BID, 100), OrderID(0),
                            limit_price=100, execution_rules = ExecutionRules.GTC)
        bid2 = LimitOrder(OrderParameters(Side.BID, 200), OrderID(1),
                                limit_price=100, execution_rules = ExecutionRules.GTC)
        bid3 = LimitOrder(OrderParameters(Side.BID, 100), OrderID(0),
                                limit_price=105, execution_rules = ExecutionRules.GTC)

        ask1 = LimitOrder(OrderParameters(Side.ASK, 100), OrderID(2),
                                limit_price=110, execution_rules = ExecutionRules.GTC)
        ask2 = LimitOrder(OrderParameters(Side.ASK, 100), OrderID(3),
                                limit_price=120, execution_rules = ExecutionRules.GTC)

        orders = [bid1, bid2, bid3, ask1, ask2]

        for order in orders:
            exec = LimitOrderExecution(order, orderbook)
            exec.execute()

        test_dir = 'multiple_states'
        saver.top_of_book_state_to_csv(orderbook, path = f'{self.test_case_dir}/{test_dir}/results')

        target_bid, target_ask = files_manager.get_target_names_bid_ask(test_saver_data_dir, self.test_case_dir, test_dir)
        result_bid, result_ask = files_manager.get_results_names_bid_ask(test_saver_data_dir, self.test_case_dir, test_dir)

        for target_bid_state, results_bid_state in files_manager.read_two_csvs(f'{target_bid}.csv', f'{result_bid}.csv'):
            self.assertEqual(target_bid_state, results_bid_state)

        for target_ask_state, results_ask_state in files_manager.read_two_csvs(f'{target_ask}.csv', f'{result_ask}.csv'):
            self.assertEqual(target_ask_state, results_ask_state)

        shutil.rmtree(f'{test_saver_data_dir}/{self.test_case_dir}/{test_dir}/results')
    
class TestSaverOrders(unittest.TestCase):
    pass

if __name__ == '__main__':
    unittest.main()