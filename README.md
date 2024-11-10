# limit_orderbook_py
Python implementation of a limit orderbook data structure.

Why?
This project is not intended for any practical use case.
The aim is 
- to provide reader with a snapshot of my Python knowledge
- provide a snapshot of my knowledge in data-structures, algorithms, design patterns
- better understand the mechanics of an orderbook before implementing it in C/C++ (in which case a practical application could be considered for futher more interesting projects)


Project discussion

Data structures used
- min/max heaps for orderbook sides: fast access to top-of-book and any layer of the orderbook
- OrderedDict for order queues: dedicated method for FIFO queues + clear functionality intent (Python base dict now ordered, but using OrderedDict makes it obvious)
- custom data structures for orders, orderbook

Algorithms
- FIFO order queues
- main order types and execution rules (limit/market, fill-or-kill/good-till-cancelled, iceberg/hidden/public)

Design choices
- Most classes implemented as dataclasses with frozen=True even though their values can evolve. Yes this is a bit 'hacky', idea was to enforce permanence of the object structure and its most important features (an order once created will only see changes in quantity filled, an orderbook will always have 2 sides bid/ask...). Gives a good idea of which constraints will need to be applied with a strict type language for a more robust implementation.
- Ask forgiveness, not permission. Pythonic way of handling errors: try and handle any problem later rather than checking for hedge-cases prior to their occurence (in most cases). Code more readable, faster to develop, still robust.
- Bottom-up test-oriented development: dev from bottom module (order) up to the top (full orderbook), module by module, developing test-cases in parallel with each module. 
