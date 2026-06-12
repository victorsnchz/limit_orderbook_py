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
queue-and-level cleanup in a single place, and each returns a typed
payload describing the transition it performed (D13).

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

**Status:** current.

**Decision:** `OrderBook` owns a `dict[int, tuple[Side, int]]` mapping
`order_id` to `(side, price)`. Populated on `post_order`, consulted on
`get_order` / `cancel_order` / `modify_order` / `fill_top`.

**Rationale:** without it, cancel and modify are O(levels) — the book would
have to scan every price level on every side to find the order. With it,
they're O(1) lookup + O(1) removal from the queue.

**Invariant:** an order is in the book iff its id is in the index. The two
must move together:
- `post_order` → add to both.
- `cancel_order` → remove from both.
- `fill_top` → when a resting order clears, remove from both (current —
  `orderbook.py` does `del self._order_index[...]` as each resting order
  fills).

**Public membership API** OrderBook.__contains__(order_id: int). Index is consulted
often enough (in-book internal logic and in-tests) that exposing membership through
dunder justified. Mirrors OrdersQueue.__contains__ shape from D8,
Encapsulated index lookup so internal mapping changes don't ripple through caller.
Future setter for index entries __setitem__ could be considered for similar reasons if
surface grows.

**Distinction worth naming:**
- `OrderNotFoundError` (id absent from index) — expected, user-facing.
- Index-vs-book inconsistency (id in index, not in book) — invariant
  violation, must surface loudly, never swallowed.

---

## D10 — Execution output via `ExecutionResult`

**Status:** current.

**Decision:** `OrderExecution.execute()` returns an `ExecutionResult`
carrying a summary `ExecutionReport` (terminal aggressor state and
whether the residual posted) plus the full ordered list of `Event`s
emitted during the call.

**Rationale:** execution previously had no output channel. Callers that
needed to know what happened (agents, loggers, tests) either introspected
the book afterwards or read internal state the executor never returned.
Both are leaks. A return value is the minimal honest contract. Splitting
summary from stream keeps simple callers cheap (read `report.status`)
without forcing fills to be discarded for callers that need them.

**Shape:**
```python
@dataclass(frozen=True)
class ExecutionReport:
    aggressor: OrderSnapshot
    posted: bool          # residual rested in book
    status: FillStatus    # FILLED | PARTIALLY_FILLED | UNFILLED


@dataclass(frozen=True)
class ExecutionResult:
    report: ExecutionReport
    events: list[Event]   # ACCEPTED | REJECTED | FILLED* | POSTED
```

**On fills:** an earlier draft put `fills: list[FilledOrder]` on
`ExecutionReport`. The shipped shape moves fills into `ExecutionResult.events`
as `FILLED` events carrying `FilledPayload`. Single channel, no
duplication; the same stream is what D11 will append-log.

**Composed from payloads (D13):** every `Event` here wraps a
per-transition payload produced by the book — `FILLED`/`FilledPayload`,
`POSTED`/`PostedPayload`, `CANCELLED`/`CancelledPayload`,
`MODIFIED`/`ModifiedPayload`. The executor assembles the stream and the
summary; it never invents fill data.

**Consequences:** unblocks structured logging, agent feedback loops, and
the event log (D11).

---

## D11 — Event log as the source of truth

**Status:** pending (roadmap phase 2).

**Decision:** the source of truth is an append-only event log carrying
monotonically increasing sequence numbers. Every state transition
(accept, fill, cancel, modify, reject) becomes one event, wrapping that
transition's payload (D13). Persistence and query are projections derived
from the log; there is no separate snapshot writer. The earlier
snapshot-based `Saver` was decommissioned rather than migrated — replaying
the log subsumes it.

**Rationale:**
- Snapshots lose the causal chain. The log keeps it.
- Replayable: a test or a debugger can rebuild any past state from a
  prefix of the log.
- Matches how real exchanges publish market data (ITCH, FIX).

**Consequences:**
- No snapshot writer; any reader/projection (depth view, export, replay)
  is built fresh over the log.
- Integration tests become event-stream diffs, which are more precise
  than directory-of-CSV comparison.

---

## D12 — Modify Semantics

**Status:** current.

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

**Layering (D6 + D13):**
- The *transition* primitive on `OrderBook` is the in-place size-down that
  mutates `remaining_quantity` while keeping queue position, and returns
  `ModifiedPayload(original_order, modified_order)` (D13). It performs one
  mutation; it does not orchestrate. Currently shipped as
  `reduce_order_quantity`; `modify_order` is its canonical name (rename
  pending, noted in D14).
- The `ModifyOrderExecution` *policy* decides size-down-in-place vs
  cancel-and-repost and, like every execution, returns a single
  `ExecutionResult` (D10/D14) — never a bespoke per-operation result. The
  book primitive never returns an `ExecutionReport`.

**One envelope, one event stream (D14):** both branches return
`ExecutionResult`. Size-down wraps its `ModifiedPayload` as one `MODIFIED`
event with a report of `posted=True, status=UNFILLED` (the order is
resting, nothing traded). Cancel-and-repost composes `cancel_order` +
`post_order` / match into **one** events list led by a `CANCELLED` event,
then the replacement's `ACCEPTED` / `FILLED*` / `POSTED`.

**Cancel-last, narrate-cancel-first.** The original is cancelled only
*after* the replacement is accepted — so a rejected replacement never
loses the order (the stream then carries `REJECTED`, no `CANCELLED`, and
`is_rejected` is the whole signal). But the `CANCELLED` event is
*prepended* to the stream so the causal narrative reads old-order-leaves →
new-order-acts. Book-mutation order and event-stream order are allowed to
differ; the stream is assembled from already-frozen payloads. (D11
sequence numbers must therefore be stamped at stream-assembly order, not
at mutation time.)

**Crossing modifies:** a cancel-and-repost whose replacement crosses is
mechanically `cancel_order` followed by routing the replacement through
the matcher (`fill_top`), exactly as a fresh aggressor would be. No
dedicated code path and no separate return type — the crossing fills
surface as `FILLED` events (D13 payloads) inside the same
`ExecutionResult`. Real venues treat this the same way; most don't even
have a distinct "modify-crosses" message type.

**Rejected alternative (retired):** an earlier draft of the amend path
returned a bespoke `CancelAndExecuteResult(cancelled, execution_result)`
inside an `AmendmentResult = ModifiedPayload | CancelAndExecuteResult`
union. This mixed two altitudes (an atomic payload OR a composite),
forced callers to `isinstance`-branch and reach to different depths, and
hid the cancellation in a sibling field where the D11 log would miss it.
Retired in favour of the single-`ExecutionResult` shape above — the
cautionary example behind D14.

**API shape:**
```python
# transition (OrderBook): in-place size-down → one payload (D13)
def reduce_order_quantity(   # canonical: modify_order
    self, order_id: int, new_quantity: int
) -> ModifiedPayload: ...

# policy (ModifyOrderExecution): orchestrates, returns the summary (D10)
def amend(
    self, new_price: int | None, new_quantity: int | None
) -> ExecutionResult: ...
```

**Consequences:**
- The book primitive stays narrow; the size-down-vs-repost branch and
  crossing routing live in the executor (D6).
- `ModifiedPayload` / `EventKind.MODIFIED` are live (D13).
- A well-formed `amend` cannot produce a rejected replacement (inputs are
  validated before cloning); the rejection branch is a defensive guarantee
  exercised directly, not through the public call.
- IOC / FOK modification behaviour is explicitly **undefined** until
  those execution rules ship.

---

## D13 — Book primitives return typed payloads (symmetric returns)

**Status:** current.

**Decision:** every state-transition primitive on `OrderBook` returns a
frozen payload describing the transition it performed — never `None`,
never a policy-level summary. One payload type per primitive:

| primitive       | returns                                            |
|-----------------|----------------------------------------------------|
| `post_order`    | `PostedPayload`                                    |
| `cancel_order`  | `CancelledPayload`                                 |
| `modify_order`  | `ModifiedPayload`                                  |
| `fill_top`      | `list[FilledPayload]` (one per touched resting order) |

Each payload carries `OrderSnapshot`s of what changed plus the minimal
extra the transition produced (`FilledPayload.filled_qty`,
`ModifiedPayload.original_order` / `modified_order`).

**Rationale:**
- Before this, `execute()` had no honest output channel and callers
  re-introspected the book afterward (the leak named in D10). A payload
  per primitive makes each transition self-reporting at its source.
- The executor layer (policy, D6) composes these payloads — and only
  these — into `Event`s (`Event.payload` is the `Payload` union, one
  `EventKind` per payload) and into `ExecutionResult` / `ExecutionReport`
  (D10). The book never builds an `ExecutionReport`; the executor never
  mutates state. Each layer's return type matches its job.
- "Symmetric" is *shape*, not identical fields: every transition reports
  what it did in the same frozen-payload form, so the event log (D11)
  appends a uniform stream. Fields differ because the transitions differ.

**Rejected alternatives:**
- Return `None` and let callers read the book afterward — the original
  leak; non-replayable, couples every caller to book internals.
- Return `ExecutionReport` from book primitives — conflates a single
  transition with the executor's terminal summary and forces the book to
  know `FillStatus` / `posted`, which are policy concepts.

**Consequences:**
- A new transition = a new payload type in the `Payload` union and a new
  `EventKind`. `ModifiedPayload` / `EventKind.MODIFIED` are live (landed
  with the modify policy, D12).
- The kind paired with a payload is fixed once, in a `PAYLOAD_KIND`
  table, and events are built via `Event.of(payload)` — the discriminant
  is derived from the payload type, so it can never drift (D14).
- The event log (D11) and structured logging are pure consumers of the
  payload stream — no new plumbing per transition.

**C++ note:** payloads map to small `struct`s in a tagged union
(`std::variant<Posted, Cancelled, Filled, Modified>`); `Event` is the
variant plus an `EventKind` tag and a sequence number.

---

## D14 — Return-type altitude law

**Status:** current.

**Decision:** there are exactly three return-shape tiers, one rule each.
A new operation reuses them; it does not invent a fourth.

| tier        | what it is                                  | rule                                                        |
|-------------|---------------------------------------------|-------------------------------------------------------------|
| `*Payload`  | one atomic transition (frozen)              | member of the `Payload` union; one per `EventKind`; only ever surfaced wrapped in an `Event` |
| `*Report`   | a policy's terminal summary (frozen)        | in no union; one per policy family (`ExecutionReport`)      |
| `*Result`   | the policy envelope = `report + events`     | **exactly one exists: `ExecutionResult`** — every policy returns it; never add a `FooResult` |

**The test:** if you are tempted to add a `FooResult`, you actually want
one of — a new `EventKind` + payload inside `ExecutionResult.events`, or a
field on `ExecutionReport`. The retired `CancelAndExecuteResult` /
`AmendmentResult` (see D12) is the worked example of getting this wrong:
it added a second envelope, mixed altitudes in a union, and demoted a
transition (the cancel) to a sibling field where the event stream — and
thus the D11 log — could not see it.

**Two payload tiers.** The `Payload` union mixes two kinds of payload, and
the distinction matters:
- *Book-transition payloads* — `Posted`, `Cancelled`, `Filled`,
  `Modified`. Emitted by `OrderBook` primitives, one per transition (D13).
- *Policy-lifecycle payloads* — `Accepted`, `Rejected`. Emitted by
  `OrderExecution` to bracket an execution's admission/rejection; there is
  no book transition behind them.

Both ride the same `Event` stream (the log does not care who minted a
payload), but `Accepted`/`Rejected` must **not** be pushed down into the
book — they are policy facts, not state transitions.

**Kind never drifts from payload.** The `EventKind` that pairs with each
payload type is declared once in `PAYLOAD_KIND` and events are built with
`Event.of(payload)`. Hand-writing `Event(kind, payload)` is disallowed —
it lets the discriminant disagree with its payload.

**Notes:**
- Cancel-and-repost (D12) emits **two** distinct `order_id`s: the old id
  in the `CANCELLED` event, a fresh id in the `ACCEPTED` / `POSTED`
  events. Size-down keeps the id. A log consumer must not assume one
  amend = one id.
- D11 sequence numbers are stamped at **stream-assembly order**, not at
  mutation time — otherwise the prepended `CANCELLED` (D12) inverts
  against its replacement events.
- Known naming gap: the size-down primitive ships as
  `reduce_order_quantity`; its canonical D13 name is `modify_order`.
  Rename is a separate mechanical follow-up.
