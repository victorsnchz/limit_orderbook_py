# Design Decisions

Living record. Decisions are added when the choice is non-obvious or
irreversible, not for every line of code. Status is one of: **current** (in
code), **pending** (planned on roadmap), **superseded** (kept for history).

---

## D1 — OrderID Generation

**Status:** current.

**Decision:** monotonically incrementing atomic counter, global to session.
Single `OrderIdGenerator` instance injected into the factory.

**Rejected alternatives:**
- `hash(user_id + timestamp)`: collision-prone, non-deterministic in tests,
  breaks replay and backtesting.
- UUID: non-sortable, overkill for a single-process simulator.

**Consequences:**
- IDs are sortable by arrival order (sequence == arrival).
- Generator is injectable, therefore testable.
- Thread-safe via `threading.Lock` — no collisions on concurrent submission.

**C++ note:** map to `std::atomic<uint64_t>` — no lock needed.

**Trivia:** real exchanges typically generate sequence numbers in the
matching engine at ingestion, not client-side. Kept here for simplicity.

---

## D2 — `is_empty` Convention

**Status:** current.

**Decision:** `is_empty` is a `@property` on every container-like type
(`BookSide`, `OrdersQueue`).

**Rationale:** no argument required, pure boolean derivation, reads as an
attribute: `if side.is_empty`. Applied uniformly to avoid the
`.is_empty` / `.is_empty()` mismatch trap.

---

## D3 — Price Level Naming

**Status:** current.

**Decision:** public interface exposes *levels* (the domain concept).
Internal data structure keeps the name `OrdersQueue` (the implementation).

**Rationale:** `level` is what a trader or a reviewer sees. `queue` is how
orders are stored at each level. Public API should speak the domain.

**Naming map (current):**
| concept                          | binding                     |
|----------------------------------|-----------------------------|
| level container                  | `BookSide._levels`          |
| level price set                  | `BookSide.prices` (`KeysView`) |
| lookup by price                  | `BookSide.get_level(price)` |
| top-of-book queue                | `BookSide.top_level`        |
| top-of-book price                | `BookSide.best_price`       |
| delete a price level             | `BookSide.delete_level(price)` |
| per-level state snapshot         | `OrdersQueue.get_state() -> LevelState` |

---

## D4 — Integer Tick Prices

**Status:** partially current — type-level enforcement done, `settings.py`
migration pending.

**Decision:** the order book operates entirely in integer ticks. Decimal
prices are only used at the input/output boundary.

**Rationale:**
- Eliminates floating-point comparison bugs in matching
  (`100.1 + 0.2 != 100.3` under IEEE-754).
- Mirrors real exchange internals.
- Prepares the C++ port — integer arithmetic is trivially fast and exact.

**Rule:** `OrderSpec.limit_price` is `int`. All comparisons in `BookSide` and
`OrderExecution` are integer. Conversion happens only at display boundaries.

**Pending:** replace `tick_size = 0.001` in `settings.py` with integer
`TICK_SIZE` / `TICK_SCALE` constants and a pair of boundary converters.

---

## D5 — Level State Representation

**Status:** current.

**Decision:** `BookSide.get_states()` returns `dict[int, LevelState]`, where
`LevelState` is a frozen dataclass:

```python
@dataclass(frozen=True)
class LevelState:
    total_volume: int
    order_count: int
    participant_count: int
```

**Rejected alternative:** tuple `(volume, participants)` — opaque,
positional, and drops `order_count`, which is useful for simulation analysis
and for catching extension regressions via whole-value equality.

**Consequences:**
- Tests assert `state == LevelState(...)`, catching missing fields when the
  struct is extended.
- `Saver` must unpack fields explicitly (no positional aliasing).

---

## D6 — State transitions vs policy: `OrderBook` and `OrderExecution`

**Status:** current.

**Decision:** `OrderBook` owns state transitions. `OrderExecution` owns
policy. The two remain in separate modules, but the split is behavioural,
not "data vs algorithm".

**State transitions (OrderBook):** operations that atomically mutate book
state and must preserve its invariants — `post_order`, `cancel_order`,
`modify_order`, and `fill_top` (consume the opposite top-of-book against
an aggressor until one side is exhausted, removing depleted orders and
empty levels as it goes). These methods own the index (D9) and the
queue-and-level cleanup in a single place.

**Policy (OrderExecution):** when to call the transitions, against what,
and how many times. `LimitOrderExecution` loops `fill_top` while the
aggressor's limit price crosses the opposite best, then posts any
residual. `MarketOrderExecution` loops `fill_top` until the aggressor is
filled or the book is exhausted, never posts. Future `IOCExecution`,
`FOKExecution`, and pegged strategies plug in here without touching the
book.

**Rationale:**
- `fill_top` mutates three coupled things at once — resting remaining
  quantity, queue membership, level existence, and (per D9) the order
  index. Centralising that mutation in `OrderBook` keeps the invariant
  enforceable in one place. If execution strategies owned the mutation,
  each new strategy would have to reimplement the cleanup correctly, and
  eventually one wouldn't.
- Policy is where execution strategies genuinely differ. Keeping policy
  thin and mutation-free makes new strategies cheap to add and trivial
  to unit-test with a mocked book.

**Rejected alternative:** `OrderBook` as a pure data structure exposing
only `add`/`remove`/`peek`, with `OrderExecution` running the match loop
itself. Cleaner on paper, but forces every execution strategy to
replicate the resting-order fill, the depleted-order removal, and the
empty-level deletion. Duplication grows linearly in strategy count; the
invariant becomes harder to defend with each addition.

**Boundary rule:** if an operation must leave the book in a consistent
state regardless of how it's called, it belongs on `OrderBook`. If it
decides *whether* to call such an operation, it belongs on
`OrderExecution`.

**C++ note:** maps to `LimitOrderBook` (state + transitions) and a
`MatchingStrategy` hierarchy (policy) — the strategies hold a reference
to the book and orchestrate its transition methods.

---

## D7 — Exception Hierarchy

**Status:** current.

**Decision:** all domain errors inherit from a single base
`OrderBookError`. Assertions are reserved for invariant violations and
debug-only preconditions; user-facing error conditions raise typed
exceptions.

**Hierarchy:**
```
OrderBookError
├── DuplicateOrderError
├── InvalidOrderError
├── OrderNotFoundError
├── PriceLevelNotFoundError
├── EmptyBookSideError
└── EmptyQueueError
```

**Rationale:**
- A single root lets callers write one `except OrderBookError:` at a
  boundary without catching unrelated `KeyError` or `ValueError`.
- Typed children make the failure mode self-documenting at the call site.

**`assert` vs. `raise` split:**
- `assert` — invariant violation, never triggered in correct code (e.g.
  `remove_order` called on an empty queue).
- `raise TypedError` — legitimate runtime condition the caller may handle
  (e.g. duplicate order submission, cancelling an unknown id).

Tests assert on the specific exception type — `AssertionError` for
invariants, typed errors for runtime conditions.

---

## D8 — `OrdersQueue` Encapsulation

**Status:** current.

**Decision:** the underlying `OrderedDict` is private (`_queue`). All access
goes through explicit public methods or dunders.

**Public surface:**
| method / property           | purpose                                      |
|-----------------------------|----------------------------------------------|
| `add_order(order)`          | append; raises `DuplicateOrderError`         |
| `remove_order(order_id)`    | pop by id; asserts queue non-empty and id present |
| `get_order(order_id)`       | lookup; raises `OrderNotFoundError`          |
| `next_order_to_execute`     | head (FIFO front); raises `EmptyQueueError`  |
| `tail`                      | last inserted; raises `EmptyQueueError`      |
| `get_state() -> LevelState` | aggregate snapshot                           |
| `get_volume() -> int`       | aggregate remaining volume                   |
| `__contains__(order_id)`    | membership by id (int), not by `Order`       |
| `__len__()`                 | order count                                  |
| `is_empty` (property)       | cheap predicate                              |

**Rationale:**
- `__contains__` takes an `int` because callers genuinely have the id, not
  the object. Accepting `Order` would force callers to do a pointless
  lookup first.
- `next_order_to_execute` is read-only (peek). Matching logic calls it,
  then calls `remove_order` if the head was consumed.
- `get_state` returns the whole `LevelState` — see D5.

**Rule:** internal methods route through the public surface (`order_id in
self`) rather than reaching into `_queue` directly. This keeps the
encapsulation honest and invariant changes localised.

---

## D9 — `OrderBook` maintains an order index

**Status:** current (partial — cleanup on fill pending, see roadmap).

**Decision:** `OrderBook` owns a `dict[int, tuple[Side, int]]` mapping
`order_id` to `(side, price)`. Populated on `post_order`, consulted on
`get_order` / `cancel_order` / `modify_order`.

**Rationale:** without it, cancel and modify are O(levels) — the book would
have to scan every price level on every side to find the order. With it,
they're O(1) lookup + O(1) removal from the queue.

**Invariant:** an order is in the book iff its id is in the index. The two
must move together:
- `post_order` → add to both.
- `cancel_order` → remove from both.
- `fill_top` → when a resting order clears, remove from both. *(Pending —
  currently only removed from the queue, leaving the index to drift.)*

**Distinction worth naming:**
- `OrderNotFoundError` (id absent from index) — expected, user-facing.
- Index-vs-book inconsistency (id in index, not in book) — invariant
  violation, must surface loudly, never swallowed.

---

## D10 — Execution output via `ExecutionReport`

**Status:** pending.

**Decision:** `OrderExecution.execute()` will return an `ExecutionReport`
carrying the filled orders, the terminal state of the aggressor, and
whether the residual was posted or cancelled.

**Rationale:** execution currently has no output channel. Callers that need
to know what happened (agents, loggers, tests) either introspect the book
afterwards or accumulate internal state the executor never returns. Both
are leaks. A return value is the minimal honest contract.

**Shape:**
```python
@dataclass(frozen=True)
class ExecutionReport:
    aggressor: OrderSnapshot
    fills: list[FilledOrder]
    posted: bool          # residual rested in book
    status: FillStatus    # FILLED | PARTIALLY_FILLED | UNFILLED
```

**Consequences:** unblocks structured logging, agent feedback loops, and
the event log (D11).

---

## D11 — Event log as the source of truth

**Status:** pending (roadmap phase 2).

**Decision:** replace the snapshot-based `Saver` with an append-only event
log carrying monotonically increasing sequence numbers. Every state
transition (accept, fill, cancel, modify, reject) becomes one event. The
current `Saver` becomes a derived view over the log.

**Rationale:**
- Snapshots lose the causal chain. The log keeps it.
- Replayable: a test or a debugger can rebuild any past state from a
  prefix of the log.
- Matches how real exchanges publish market data (ITCH, FIX).

**Consequences:**
- Saver no longer the primary persistence layer — reader, not writer.
- Integration tests become event-stream diffs, which are more precise
  than directory-of-CSV comparison.

---

## D12 — Modify Semantics

**Status:** pending.

**Decision:** follow real-exchange behaviour. A modify at the same price
with strictly lower quantity keeps queue priority. Any other modify —
price change, quantity increase, any side change — is cancel-and-repost
and loses priority. Modifies that would cross the book route through the
matching engine as the replaced order would.

**Rationale:** this is what Nasdaq, NYSE, LSE, and CME implement. The
fairness argument: you cannot improve queue position without paying for
it with a fresh timestamp. Size-down is harmless and preserves priority.

**Rejected alternative:** always cancel-and-repost. Simpler to implement,
but penalises benign size reductions and diverges from every major venue.

**Crossing modifies:** mechanically identical to `cancel_order` followed
by `execute_order` on the new aggressor. No dedicated code path, no
separate return type — the modify API returns the same `ExecutionReport`
(D10) as any aggressor would. Real venues treat this the same way; most
don't even have a distinct "modify-crosses" message type.

**API shape:**
```python
def modify_order(
    self, order_id: int, new_price: int, new_quantity: int
) -> ExecutionReport: ...
```

**Consequences:**
- Implementation is a thin orchestrator: decide size-down-in-place vs
  cancel-and-repost; if the latter and the new order crosses, route
  through `execute_order`.
- IOC / FOK modification behaviour is explicitly **undefined** until
  those execution rules ship.
