# limit_orderbook_py

[![tests](https://github.com/victorsnchz/limit_orderbook_py/actions/workflows/test.yml/badge.svg)](https://github.com/victorsnchz/limit_orderbook_py/actions/workflows/test.yml)

A continuous-matching limit order book in Python. Single-process, in-memory,
price-time priority, integer-tick arithmetic, typed event output. Written as a
correctness-first reference implementation before a port to C++/Rust.

---

## What

A working matching engine: limit and market aggressors, modify (size-down
keeps queue priority, everything else is cancel-and-repost), FIFO queues at
each price level, multi-level walks across the book, and a typed
result/event stream from every execution. State transitions and execution
policy are split along a deliberate boundary (see D6 below). Every
non-obvious choice is documented in [DECISIONS.md](docs/DECISIONS.md).

**Testing.** Unit and integration suites both pass — 429 tests. The split
is bottom-up: each module (`Order`, `OrdersQueue`, `BookSide`, `OrderBook`,
`LimitOrderExecution` / `MarketOrderExecution`, `ModifyOrderExecution`) has
its own unit suite, and integration tests exercise the full
`OrderExecution → OrderBook → BookSide → OrdersQueue` stack.

## Why

1. **A C++/Rust port comes next.** Building it in Python first makes the
   invariants, the type boundaries, and the policy/transition split
   explicit before reworking into C++/Rust (TBD). Decisions made here (integer
   ticks, frozen value objects, a single-source order index) translate cleanly to a typed-language rewrite.
2. **A substrate for simulation.** Once the engine is correct and
   observable, agent-driven simulations and microstructure case studies
   become a thin layer on top (see *What's next*).
3. **A portfolio piece.** It's a public, end-to-end demonstration of how I
   reason about state, contracts, and trade-offs on a non-trivial system.

---

## Run / test

```bash
pip install -e ".[test]"                  # editable install + pytest

pytest                                    # full suite — 429 tests (what CI runs)
python -m unittest discover -s test       # same suite via the stdlib runner
```

Python ≥ 3.10; CI runs the suite on 3.10 / 3.11 / 3.12. The engine pulls in
`sortedcontainers` for the per-side level map; `matplotlib` is declared for
the depth-chart script (Phase 4) and is not yet used. `pytest` is the only
test-time dependency.

---

## Architecture

```
src/lob/
├── orders/
│   ├── order.py              # Order (mutable), OrderSpec, OrderID
│   ├── factory.py            # type-driven Order construction
│   └── order_id_generator.py # atomic, monotonic, injectable (D1)
├── orderbook/
│   ├── orders_queue.py       # FIFO queue at one price level (D8)
│   ├── book_side.py          # SortedDict[price → OrdersQueue], top-of-book
│   ├── orderbook.py          # bids + asks + order index (D9), state transitions (D6)
│   ├── order_execution.py    # LimitOrderExecution, MarketOrderExecution (D6, D10)
│   └── modify_order.py       # ModifyOrderExecution (D12, D14)
└── bookkeeping/
    ├── custom_types.py       # enums, Event/EventKind, payloads, snapshots, ExecutionResult
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
FILLED | POSTED | CANCELLED | MODIFIED`). One channel, no duplicate
fields, ready to feed an append-only event log (D11) without API churn.

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
priority. Anything else — a price change or a size-up — is
cancel-and-repost and loses priority. This is what Nasdaq, NYSE, LSE,
and CME implement; the fairness rule is *you cannot improve queue
position without paying for it with a fresh timestamp*. Crossing
modifies are mechanically `cancel_order` followed by routing the
replacement through the matcher, like any other aggressor — no separate
code path, no separate return type. `ModifyOrderExecution.modify` returns
a single `ExecutionResult` (D10/D14) like every other execution: a
size-down is one `MODIFIED` event; a cancel-and-repost is one event
stream led by a `CANCELLED` (the original, narrated first) followed by
the replacement's `ACCEPTED | FILLED* | POSTED`. The earlier bespoke
`CancelAndExecuteResult` was retired — see D14.

### Execution output is a typed contract (D10)

`execute()` returns `ExecutionResult(report, events)`:
`ExecutionReport` is a frozen summary (terminal aggressor state,
`FillStatus`, whether residual posted), `events` is the ordered stream
(`ACCEPTED | REJECTED | FILLED | POSTED | CANCELLED | MODIFIED`). One
channel for fills, not two, so the same stream is what the event log
(D11) will append. Cheap callers read `report.status`; replay-driven
callers consume `events`.

### Symmetric returns: one payload per transition (D13)

Every `OrderBook` mutation returns a typed payload — `post_order →
PostedPayload`, `cancel_order → CancelledPayload`, `modify_order →
ModifiedPayload`, `fill_top → list[FilledPayload]`. The book reports what
each transition did; the executor composes those payloads into the
`Event` stream and `ExecutionResult` (D10). No primitive returns `None`
and none builds a policy summary — each layer's return type matches its
job, and the event log (D11) appends a uniform stream.

### Frozen dataclasses for evolving objects

Every value object that crosses a module boundary is `frozen=True`:
`OrderSpec` and `OrderID` (inputs), `OrderSnapshot` and `LevelState`
(views), the per-transition payloads, `Event`, and the
`ExecutionReport` / `ExecutionResult` pair. The lone mutable exception
is the `Order` container itself — `remaining_quantity` drains as the
order fills, so it stays a plain class rather than a frozen dataclass.
The intent is to lock the structural contract while leaving the engine
free to evolve runtime state, and to make the C++ port's `const`
discipline a transcription rather than a redesign.

### Typed exception hierarchy, not stringly errors (D7)

Every domain error inherits from `OrderBookError`
(`DuplicateOrderError`, `InvalidOrderError`, `InvalidModificationError`,
`OrderNotFoundError`, `PriceLevelNotFoundError`, `EmptyBookSideError`,
`EmptyQueueError`).
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
`test/integration/test_order_execution.py`,
`test/integration/test_modify_order.py`). It's how the suite reached
429 passing, built bottom-up rather than against a frozen golden output.

---

## Repo conventions

- [docs/DECISIONS.md](docs/DECISIONS.md) — non-obvious or irreversible choices, with rejected
  alternatives and (where applicable) C++/Rust notes. Living document, and
  the only tracked doc; the phased roadmap and architecture brief are kept
  as local working notes.
- Commits are scoped (`feat`, `refactor`, `test`, `chore`); the history
  is meant to be readable.

---

## Contact

[github.com/victorsnchz](https://github.com/victorsnchz) · written as a public artifact.
Critique welcome.
