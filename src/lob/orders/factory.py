# product = order
# concrete = limit / market orders

from lob.orders.order import Order, OrderID, OrderSpec
from abc import ABC, abstractmethod
from lob.bookkeeping.custom_types import OrderType, Side, ExecutionRule
from lob.orders.order_id_generator import OrderIdGenerator


class OrderFactory(ABC):
    """
    Build `Order`s with ids drawn from a shared `OrderIdGenerator`.
    Concrete subclasses set the `OrderType` and accept type-specific kwargs.
    """

    def __init__(self, generator: OrderIdGenerator):
        self._generator = generator

    @abstractmethod
    def create_order(self, side: Side, quantity: int, user_id: int, **kwargs) -> Order:
        pass


class LimitOrderFactory(OrderFactory):
    def __init__(self, generator: OrderIdGenerator):
        super().__init__(generator)

    def create_order(
        self,
        side: Side,
        quantity: int,
        user_id: int,
        limit_price: int,
        execution_rule: ExecutionRule,
    ) -> Order:

        spec = OrderSpec(side, OrderType.LIMIT, quantity, limit_price, execution_rule)
        id_ = OrderID(self._generator.next_id(), user_id)

        return Order(spec, id_)


class MarketOrderFactory(OrderFactory):
    def __init__(self, generator: OrderIdGenerator):
        super().__init__(generator)

    def create_order(self, side: Side, quantity: int, user_id: int) -> Order:

        spec = OrderSpec(side, OrderType.MARKET, quantity)
        id_ = OrderID(self._generator.next_id(), user_id)

        return Order(spec, id_)


map_type_to_factory = {
    OrderType.LIMIT: LimitOrderFactory,
    OrderType.MARKET: MarketOrderFactory,
}
