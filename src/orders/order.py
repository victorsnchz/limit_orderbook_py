from dataclasses import dataclass
from src.bookkeeping.custom_types import ExecutionRule, Side, OrderType, OrderSnapshot
from typing import Optional


@dataclass(frozen=True)
class OrderSpec:
    side: Side
    order_type: OrderType
    quantity: int
    limit_price: Optional[int] = None
    execution_rule: Optional[ExecutionRule] = None

    def __post_init__(self):
        if self.order_type == OrderType.LIMIT and self.limit_price is None:
            raise ValueError("Limit order expected to receive a limit price not None")


@dataclass(frozen=True)
class OrderID:
    order_id: int
    user_id: int

    def __post_init__(self):
        pass


class Order:
    """
    Store order informations and any relevant order updates.
    """

    def __init__(self, spec: OrderSpec, id: OrderID):

        self._spec = spec
        self._id = id

        self.remaining_quantity = self._spec.quantity

    # --- spec immutable views ---

    @property
    def side(self) -> Side:
        return self._spec.side

    @property
    def initial_quantity(self) -> int:
        return self._spec.quantity

    @property
    def order_type(self) -> OrderType:
        return self._spec.order_type

    @property
    def limit_price(self) -> Optional[int]:
        return self._spec.limit_price

    @property
    def execution_rule(self) -> ExecutionRule:
        return self._spec.execution_rule

    @property
    def is_filled(self) -> bool:
        return not bool(self.remaining_quantity)

    # --- identity immutable views ---

    @property
    def order_id(self) -> int:
        return self._id.order_id

    @property
    def user_id(self) -> int:
        return self._id.user_id

    # --- other methods ---

    def can_cross(self, opposite_best_price: int | None) -> bool:

        if opposite_best_price is None:
            return False

        if self.order_type == OrderType.MARKET:
            return True
        if self.side == Side.BID:
            return self.limit_price >= opposite_best_price
        if self.side == Side.ASK:
            return self.limit_price <= opposite_best_price
        raise ValueError("invalid side {self.side}")

    # --- mutable states ---

    def fill(self, quantity: int) -> int:

        if min(quantity, self.remaining_quantity) <= 0:
            return 0

        filled = min(quantity, self.remaining_quantity)

        self.remaining_quantity -= filled

        return filled

    def reduce(self, new_quantity: int) -> None:

        if new_quantity >= self.remaining_quantity:
            raise ValueError(
                "new_quantity must be less than remaining quantity "
                "else cancel and psot new order."
            )

        self.remaining_quantity = new_quantity

    # --- order snapshot at given time ---

    def snapshot(self):

        return OrderSnapshot(
            self.side,
            self.order_type,
            self.initial_quantity,
            self.remaining_quantity,
            self.order_id,
            self.user_id,
            self.limit_price,
            self.execution_rule,
        )
