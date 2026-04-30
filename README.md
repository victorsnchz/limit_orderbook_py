# limit_orderbook_py

[![tests](https://github.com/victorsnchz/limit_orderbook_py/actions/workflows/test.yml/badge.svg)](https://github.com/victorsnchz/limit_orderbook_py/actions/workflows/test.yml)

A continuous-matching limit order book in Python. Single-process, in-memory,
price-time priority, integer-tick arithmetic, typed event output. Written as a
correctness-first reference implementation before a port to C++.

---

## What

Working matching enginer which supports limit and market aggressors,
FIFO queues at each price level, multi-level walks across the book,
typed result/event stream from every execution. State transitions and
execution policy are split along a deliberate boundary (see D6 below). Every
non-obvious choice is documented in [DECISIONS.md](docs/DECISIONS.md); the next
work and its rationale live in [ROADMAP.md](docs/ROADMAP.md).

Testing
unit + integration tests pass
Test split is bottom-up: each module (`Order`, `OrdersQueue`, `BookSide`, `OrderBook`, `OrderExecution`) has its own unit suite, and integration tests exercise the full
`OrderExecution → OrderBook → BookSide → OrdersQueue` stack.

## Why

1. **A C++/Rust port comes next.** Building it in Python first makes the
   invariants, the type boundaries, and the policy/transition split
   explicit before reworking into C++/Rust (TBD). Decisions made here (integer
   ticks, frozen value objects, a single-source order index) translate cleanly to a typed-language rewrite.
2. **A substrate for simulation.** Once the engine is correct and
   observable, agent-driven simulations and microstructure case studies
   become a thin layer on (see *What's next*).
3. **A portfolio piece.** It's a public, end-to-end demonstration of how I
   reason about state, contracts, and trade-offs on a non-trivial system.

---

## Run / test

```bash
pip install -e .                          # editable install (sortedcontainers, matplotlib)

python -m unittest discover -s test       # full suite
./test_by_module.bash                     # per-module, in dependency order,
                                          # returns  only failed tests
```

Python ≥ 3.10. No third-party dependency in the engine path; `matplotlib`
is for the depth-chart script (Phase 4) and `sortedcontainers` backs the
per-side level map.

---

## Architecture

```
src/lob/
├── orders/
│   ├── order.py              # Order, OrderSpec, OrderSnapshot, FilledOrder
│   ├── factory.py            # type-driven Order construction
│   └── order_id_generator.py # atomic, monotonic, injectable (D1)
├── orderbook/
│   ├── orders_queue.py       # FIFO queue at one price level (D8)
│   ├── book_side.py          # SortedDict[price → OrdersQueue], top-of-book
│   ├── orderbook.py          # bids + asks + order index (D9), state transitions (D6)
│   └── order_execution.py    # LimitOrderExecution, MarketOrderExecution (D6, D10)
└── bookkeeping/
    ├── custom_types.py       # Side, OrderType, ExecutionRule, FillStatus, Event, payloads
    ├── exceptions.py         # OrderBookError hierarchy (D7)
    └── settings.py           # tick size, configuration
```

**Hot paths:**
- `O(log n_levels)` to find a price level (`SortedDict`), `O(1)` for
  top-of-book.
- `O(1)` cancel / modify by id, via `OrderBook._order_index` (D9).
- `O(1)` enqueue / dequeue per order at a level (`OrderedDict`).

**The execution path:**
`OrderExecution.execute()` returns an `ExecutionResult` (D10) with a
summary `ExecutionReport` (terminal aggressor state, fill status, whether
residual posted) and an ordered `list[Event]` (`ACCEPTED | REJECTED |
FILLED | POSTED`). One channel, no duplicate fields, ready to feed an
append-only event log (D11) without API churn.

---

## What's next

In phase order. The full version, with rationale, is in
[ROADMAP.md](docs/ROADMAP.md). Highlights:

**Phase 1 — engine completeness.** `cancel_order` (1.8) and
`modify_order` (1.9, semantics in D12 — size-down keeps queue priority,
everything else is cancel-and-repost; crossing modifies route through the
matcher and return the same `ExecutionReport` an aggressor would).
`assert_book_consistent()` as an integration-only invariant probe (1.7).
CI on every push (1.4).

**Phase 2 — observability.** Append-only event log with monotone sequence
numbers (D11, 2.3): every state transition is one event, the historical
`Saver` becomes a derived reader (1.13/2.4 already moved to "decommission
and rebuild" rather than refactor). This is the same model real exchanges
publish (ITCH/FIX) and the substrate for replayable backtests.
Structured logging at engine boundaries (2.5).

**Phase 3 — hygiene.** Migrate the remaining float tick to integer
`TICK_SIZE` / `TICK_SCALE` constants (D4 — type-level enforcement is
already done; only `settings.py` is left). `mypy --strict` and `ruff` on
CI (3.3, 3.4).

**Phase 4 — simulation.** A `RandomAgent` (4.1), a deterministic
`Simulation.run(n_agents, n_ticks, seed)` (4.2), depth-chart rendering
(4.3). With the event log in place, all three are thin.

**Phase 5 — port.** Once the contract is stable and the suite is green,
the C++/Rust rewrite begins. The [DECISIONS.md](docs/DECISIONS.md) C++/Rust notes are the spec.

---

## Engineering decisions worth surfacing

These are the calls that have actual leverage on the design. Each links
to its full entry in [DECISIONS.md](docs/DECISIONS.md).

### State transitions vs. policy (D6)

The book owns mutation; execution owns when to mutate. `OrderBook`
exposes `post_order`, `cancel_order`, `modify_order`, and `fill_top` —
each one atomically maintains the queue, the level, and the order index.
`OrderExecution` strategies (limit, market, future IOC/FOK/pegged)
decide whether to call them and how often, and never touch state
directly. Rejected the alternative (book as pure data, executor runs the
match loop) because it forces every new strategy to re-implement the
cleanup and eventually one won't.

### Single source of truth for order lookup (D9)

`OrderBook` maintains a `dict[int, tuple[Side, int]]` index from
`order_id` to `(side, price)`. Cancel / modify / fill-driven cleanup all
go through it; without it those operations are `O(levels)`. The
invariant is *an order is in the book iff its id is in the index*, and
the distinction between "id absent" (user-facing `OrderNotFoundError`,
D7) and "in index but not in book" (loud invariant violation) is named
explicitly so the second is never silently swallowed.

### Integer ticks, end to end (D4)

Matching, comparison, and storage operate exclusively on integer ticks.
Decimal prices live only at the I/O boundary. Eliminates the
`100.1 + 0.2 != 100.3` class of bugs in price comparison, mirrors real
exchange internals, and makes the C++ port trivially fast and exact.

### Modify semantics from real venues (D12)

A modify at the same price with strictly lower quantity keeps queue
priority. Anything else — price change, size up, side flip — is
cancel-and-repost and loses priority. This is what Nasdaq, NYSE, LSE,
and CME implement; the fairness rule is *you cannot improve queue
position without paying for it with a fresh timestamp*. Crossing
modifies are mechanically `cancel_order` followed by `execute_order` on
the new aggressor and return the same `ExecutionReport` as any other
aggressor — no separate code path, no separate return type, matching
how real venues handle it.

### Execution output is a typed contract (D10)

`execute()` returns `ExecutionResult(report, events)`:
`ExecutionReport` is a frozen summary (terminal aggressor state,
`FillStatus`, whether residual posted), `events` is the ordered stream
(`ACCEPTED | REJECTED | FILLED | POSTED`). One channel for fills, not
two, so the same stream is what the event log (D11) will append. Cheap
callers read `report.status`; replay-driven callers consume `events`.

### Frozen dataclasses for evolving objects

`Order`, `OrderSpec`, `OrderSnapshot`, `FilledOrder`, `LevelState`,
`ExecutionReport`, `ExecutionResult` are all `frozen=True`. Quantity
filled and similar evolving fields live on the *mutable* `Order`
container; everything that crosses a boundary (snapshots, events,
reports) is immutable. The intent is to lock the structural contract
while leaving the engine free to evolve runtime state, and to make the
C++ port's `const` discipline a transcription rather than a redesign.

### Typed exception hierarchy, not stringly errors (D7)

Every domain error inherits from `OrderBookError`
(`DuplicateOrderError`, `InvalidOrderError`, `OrderNotFoundError`,
`PriceLevelNotFoundError`, `EmptyBookSideError`, `EmptyQueueError`).
Tests assert on the type; callers can write a single
`except OrderBookError:` at a boundary without catching unrelated
`KeyError` / `ValueError`. `assert` is reserved strictly for invariant
violations (never triggered in correct code); user-facing failure modes
always raise typed exceptions.

### Bottom-up, test-driven module by module

Each module shipped with its unit suite before the next one was built;
integration tests landed once the stack was assembled. The split is
visible in the test layout (`test/unit/*` per module,
`test/integration/test_orderbook.py`,
`test/integration/test_order_execution.py`). It's how the suite reached
353 passing without snapshot tests or mocks of the engine itself.

---

## Repo conventions

- [docs/DECISIONS.md](docs/DECISIONS.md) — non-obvious or irreversible choices, with rejected
  alternatives and (where applicable) C++ notes. Living document.
- [docs/ROADMAP.md](docs/ROADMAP.md) — phased work, gated by an explicit *engine green* bar.
  Tasks reference decision IDs.
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — diagram-oriented summary of the engine's structure.
- Commits are scoped (`feat`, `refactor`, `test`, `chore`); the history
  is meant to be readable.

---

## Contact

[github.com/thespielmaster](https://github.com) · written as a public artifact.
Critique welcome.
