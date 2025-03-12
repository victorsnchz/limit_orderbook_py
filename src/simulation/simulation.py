import time

from orderbook.orderbook import OrderBook
from visuals.depth_chart import DepthChart


class Simulation:
    def __init__(self, scenario = None):
        """
        Parent class for managing simulations.
        """
        self.scenario = scenario
        pass

    def send_agents_orders(self):

        bids, asks = order_generator.generate()
        orders = bids + asks

        for order in orders:
            exec = LimitOrderExecution(order, orderbook)
            exec.execute()

        depth_chart._update_orderbook(orderbook)


    def run(self):
        pass

class TimedSimulation(Simulation):
    def __init__(self, duration: int = 1, loop_rest: int = 1):
        """
        Run simulation for a given time.
        """
        super().__init__()

        self._duration = duration
        self._loop_rest = loop_rest

    def run(self):

        start = time.time()

        while(time.time() - start < self._duration):
            pass

class EpochSimulation(Simulation):
    def __init__(self, agents=None):
        """
        Run simulation for a given number of epochs.
        """
        super().__init__(agents)