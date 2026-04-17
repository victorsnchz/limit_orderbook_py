class OrderBookError(Exception):
    pass


class DuplicateOrderError(OrderBookError):
    pass


class InvalidOrderError(OrderBookError):
    pass


class EmptyBookSideError(OrderBookError):
    pass


class EmptyQueueError(OrderBookError):
    pass
