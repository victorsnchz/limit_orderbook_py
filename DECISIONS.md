Design Decisions

Recorded befor implementation begins on fix/core-refactor.

D1. OrderID Generation

Decision: monotonically incrementing atomic counter, global to session.

Rejected alternatives:
- hash of user_id + timestamp: collision-prone (time-precision), non-deterministic in tests, breaks replay and backtesting
- UUID: non-sortable, overkill for local simulation with no persistent req.

Implementation:
# src/orders/order_id_generator.py
import threading

class OrderIdGenerator:
    def __init__(self, start: int = 0):
        self._counter = start
        self._lock = threading.Lock()

    def next_id(self) -> int:
        with self._lock:
            self._counter += 1
            return self._counter

A single instance created at session start and injected into the factory.
Keeps generator off global state, making it injectable and testable.

Consequences:
- OrderID(order_id, user_id): order_id always produced by OrderGenerator.next_id()
- OrderFactory receives an OrderIdGenerator as a constructor argument
- IDs are sortable by arrival order: sequence order == arrival order
- thread-safe: lock ensures no two concurrent order submissions collide

Miscellaneous:
- real exchanges generate sequence numbers in matching engine at ingestion (not by client)
- C++: implement using std::atomic<uint64_t>

D2. is_empty Convention

Decision: is_empty is a @property everywhere

Rationale:
- no arg required
- result is pure lookup / cheap boolean derivation
- reads as an attribute when called: if foo.is_empty

Both BookSide.is_empty and OrdersQueue.is_empty satisfy these conditions.

D3. Price Level Naming

Decision: public interface uses levels. Internal data structure class retains name OrdersQueue.

Rationale:
- level is the domain concept
- queue is an implementation detail (how orders are stored at each level)
- public method name expose domain concept not implementation
- book_side.get_level(price) and book_side.levels natural + easy to grasp
- book_side.get_queue(price) reveals too much internal implementation

Naming map
- dict mapping pricce->queue: BookSide.levels
- return top-of-book queue: BookSide.get_top_level()
- return best price: BookSide.get_best_price()
- check if price level exists: BookSide.has_level(price)
- delete price level: BookSide.delete_level(price)
- internal queue class: OrdersQueue

D4. Price Representation: Integer Ticks

Decision: order book operates entirely in integer ticks. Decimal prices only used at boundary (input/output).

Rationale:
- eliminates floating-point comparison bugs in matching logic (100.1 + 0.2 != 100.3 IEEE754)
- aligns with how real exchanges represent prices internally
- prepares for C++ port where integer arithmetic trivially fast
- makes tick-size arithmetic exact

Implementation
# src/bookkeeping/settings.py
TICK_SIZE = 1        # 1 tick = 0.01 currency units — change per instrument
TICK_SCALE = 100     # multiply decimal price by this to get ticks

# Conversion utilities (boundary only)
def to_ticks(decimal_price: float) -> int:
    return round(decimal_price * TICK_SCALE)

def to_decimal(ticks: int) -> float:
    return ticks / TICK_SCALE

Rule: limit_price in OrderSpec is int. ALl price comparisons in BookSide and OrderExecution operate on int. Conversion to decimal happens only at display/output boundaries.

