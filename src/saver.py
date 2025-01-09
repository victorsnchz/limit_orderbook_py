from order import Order
from orderbook import OrderBook

import datetime
import csv

class Saver:

    def __init__(self, master_directory: str = 'data/'):
        self.date = datetime.datetime.today()

    def order_to_csv(self, order: Order, path: str = None) -> None:
        
        pass

    def state_to_csv(self, orderbook: OrderBook, path: str = None) -> None:
        
        # support only sec precision for demo
        # go into millis or micro for the Cpp version?
        timestamp = datetime.datetime.now().time().strftime('%H:%M%S')

        levels_info = {}

        with open(f'{timestamp}.csv', 'w') as csv_file:
            
            writer = csv.writer(csv_file)

            for price_level, data in levels_info.items():
                row_data = [price_level] + data
                writer.writerow(row_data)