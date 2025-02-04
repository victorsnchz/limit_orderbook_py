from order import Order
from orderbook import OrderBook

from files_manager import write_dict_to_csv
import os
import datetime
import csv

class Saver:

    def __init__(self, data_directory: str = f'../data'):
        
        self._data_directory = data_directory
        self.date = datetime.datetime.today()

    def order_to_csv(self, order: Order, path: str = None) -> None:
        
        pass

    def orderbook_state_to_csv(self, orderbook: OrderBook, path: str = 'orderbook_states') -> None:        

        date = datetime.datetime.now().date().strftime('%Y_%m_%d')
        dir = f'{self._data_directory}/{path}/{date}' if path is not None else f'{self._data_directory}/{date}'

        if not os.path.exists(dir):
            os.makedirs(dir)

        bids_state, asks_state = orderbook.get_orderbook_state()
        timestamp = datetime.datetime.now().time().strftime('%H_%M_%S')

        with open(f'{dir}/bid_{timestamp}.csv', 'w') as csv_file:
            
            writer = csv.writer(csv_file)
            write_dict_to_csv(writer, bids_state)

        with open(f'{dir}/ask_{timestamp}.csv', 'w') as csv_file:
            
            writer = csv.writer(csv_file)
            write_dict_to_csv(writer, asks_state)

    def top_of_book_state_to_csv(self, orderbook: OrderBook, path: str = 'top_of_book_states') -> None:        

        date = datetime.datetime.now().date().strftime('%Y_%m_%d')
        dir = f'{self._data_directory}/{path}/{date}' if path else f'{self._data_directory}/{date}'
        
        if not os.path.exists(dir):
            os.makedirs(dir)

        top_bid_state, top_ask_state = orderbook.get_top_of_book_state()
        timestamp = datetime.datetime.now().time().strftime('%H_%M_%S')
        with open(f'{dir}/bid_{timestamp}.csv', 'w') as csv_file:
            
            writer = csv.writer(csv_file)
            write_dict_to_csv(writer, top_bid_state)
        
        with open(f'{dir}/ask_{timestamp}.csv', 'w') as csv_file:
            
            writer = csv.writer(csv_file)
            write_dict_to_csv(writer, top_ask_state)