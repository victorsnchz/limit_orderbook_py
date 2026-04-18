class OrderBookError(Exception):
    pass


# --- Order errors and exceptions ------------------------------------------------------


class DuplicateOrderError(OrderBookError):
    pass


class InvalidOrderError(OrderBookError):
    pass


# --- Book_side errors and exceptions --------------------------------------------------


class EmptyBookSideError(OrderBookError):
    pass


class PriceLevelNotFoundError(OrderBookError):
    pass


# --- OrdersQueue errors and exceptions ------------------------------------------------
class EmptyQueueError(OrderBookError):
    pass


class OrderNotFoundError(OrderBookError):
    pass
