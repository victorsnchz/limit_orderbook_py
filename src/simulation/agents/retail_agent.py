from random_agent import RandomAgent

class RetailAgent(RandomAgent):
    
    def __init__(self, orderbook = None, bankroll = 0):
        super().__init__(orderbook, bankroll)

    