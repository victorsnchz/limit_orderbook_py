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
import helper

test_saver_data_dir = 'test_data/test_saver'

class TestSaverBookState(unittest.TestCase):

    abs_path = os.path.dirname(__file__)

    test_data_directory = f'{abs_path}/{test_saver_data_dir}/book_state'

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

        results_data_directory = f'{self.test_data_directory}/one_state/results'
        targets_data_directory = f'{self.test_data_directory}/one_state/targets'
        
        saver = Saver(data_directory=results_data_directory)
        saver.orderbook_state_to_csv(orderbook, path = None)

        date = datetime.datetime.now().date().strftime('%Y_%m_%d')
        timestamp = datetime.datetime.now().time().strftime('%H_%M_%S')

        target_bid_file = f'{targets_data_directory}/bid'
        results_bid_file = f'{results_data_directory}/{date}/bid_{timestamp}'

        for target_bid_state, results_bid_state in helper.read_two_csvs(target_bid_file, results_bid_file):
            self.assertEqual(target_bid_state, results_bid_state)

        target_ask_file = f'{targets_data_directory}/ask'
        results_ask_file = f'{results_data_directory}/{date}/ask_{timestamp}'

        for target_ask_state, results_ask_state in helper.read_two_csvs(target_ask_file, results_ask_file):
            self.assertEqual(target_ask_state, results_ask_state)

        shutil.rmtree(f'{results_data_directory}/{date}')

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

        results_data_directory = f'{self.test_data_directory}/multiple_states/results'
        targets_data_directory = f'{self.test_data_directory}/multiple_states/targets'
        
        saver = Saver(data_directory=results_data_directory)
        saver.orderbook_state_to_csv(orderbook, path = None)

        date = datetime.datetime.now().date().strftime('%Y_%m_%d')
        timestamp = datetime.datetime.now().time().strftime('%H_%M_%S')

        target_bid_file = f'{targets_data_directory}/bid'
        results_bid_file = f'{results_data_directory}/{date}/bid_{timestamp}'

        for target_bid_state, results_bid_state in helper.read_two_csvs(target_bid_file, results_bid_file):
            self.assertEqual(target_bid_state, results_bid_state)

        target_ask_file = f'{targets_data_directory}/ask'
        results_ask_file = f'{results_data_directory}/{date}/ask_{timestamp}'

        for target_ask_state, results_ask_state in helper.read_two_csvs(target_ask_file, results_ask_file):
            self.assertEqual(target_ask_state, results_ask_state)

        shutil.rmtree(f'{results_data_directory}/{date}') 

class TestSaverTopOfBook(unittest.TestCase):
    abs_path = os.path.dirname(__file__)

    test_data_directory = f'{abs_path}/{test_saver_data_dir}/top_of_book_state'

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

        results_data_directory = f'{self.test_data_directory}/one_state/results'
        targets_data_directory = f'{self.test_data_directory}/one_state/targets'
        
        saver = Saver(data_directory=results_data_directory)
        saver.top_of_book_state_to_csv(orderbook, path = None)

        date = datetime.datetime.now().date().strftime('%Y_%m_%d')
        timestamp = datetime.datetime.now().time().strftime('%H_%M_%S')

        target_bid_file = f'{targets_data_directory}/bid'
        results_bid_file = f'{results_data_directory}/{date}/bid_{timestamp}'

        for target_bid_state, results_bid_state in helper.read_two_csvs(target_bid_file, results_bid_file):
            self.assertEqual(target_bid_state, results_bid_state)

        target_ask_file = f'{targets_data_directory}/ask'
        results_ask_file = f'{results_data_directory}/{date}/ask_{timestamp}'

        for target_ask_state, results_ask_state in helper.read_two_csvs(target_ask_file, results_ask_file):
            self.assertEqual(target_ask_state, results_ask_state)

        shutil.rmtree(f'{results_data_directory}/{date}')

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

        results_data_directory = f'{self.test_data_directory}/multiple_states/results'
        targets_data_directory = f'{self.test_data_directory}/multiple_states/targets'
        
        saver = Saver(data_directory=results_data_directory)
        saver.top_of_book_state_to_csv(orderbook, path = None)

        date = datetime.datetime.now().date().strftime('%Y_%m_%d')
        timestamp = datetime.datetime.now().time().strftime('%H_%M_%S')

        target_bid_file = f'{targets_data_directory}/bid'
        results_bid_file = f'{results_data_directory}/{date}/bid_{timestamp}'

        for target_bid_state, results_bid_state in helper.read_two_csvs(target_bid_file, results_bid_file):
            self.assertEqual(target_bid_state, results_bid_state)

        target_ask_file = f'{targets_data_directory}/ask'
        results_ask_file = f'{results_data_directory}/{date}/ask_{timestamp}'

        for target_ask_state, results_ask_state in helper.read_two_csvs(target_ask_file, results_ask_file):
            self.assertEqual(target_ask_state, results_ask_state)

        shutil.rmtree(f'{results_data_directory}/{date}') 
    
class TestSaverOrders(unittest.TestCase):
    pass

if __name__ == '__main__':
    unittest.main()