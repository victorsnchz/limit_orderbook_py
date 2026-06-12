"""Exception hierarchy for the order book; all errors derive from OrderBookError."""


class OrderBookError(Exception):
    """Base class for all order book errors."""


# --- Order errors and exceptions ------------------------------------------------------


class DuplicateOrderError(OrderBookError):
    """An order id already present on the book was submitted again."""


class InvalidOrderError(OrderBookError):
    """An order failed validation of its fields or invariants."""


class InvalidModificationError(OrderBookError):
    """A modification would violate an order's invariants."""


# --- Book_side errors and exceptions --------------------------------------------------


class EmptyBookSideError(OrderBookError):
    """An operation required a level but the book side held none."""


class PriceLevelNotFoundError(OrderBookError):
    """The requested price level does not exist on this side."""


# --- OrdersQueue errors and exceptions ------------------------------------------------
class EmptyQueueError(OrderBookError):
    """An operation required an order but the queue was empty."""


class OrderNotFoundError(OrderBookError):
    """No order with the requested id exists in this scope."""
