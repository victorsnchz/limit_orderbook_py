# limit_orderbook_py
Python implementation of a limit orderbook data structure, with continuous execution.

Why?
This project is not intended for any practical use case.
The aim is 
- to provide reader with a snapshot of my Python knowledge.
- provide a snapshot of my knowledge in data-structures, algorithms, design patterns.
- better understand the mechanics of an orderbook before implementing it in C/C++ (in which case a practical application could be considered for futher more interesting projects).


Project discussion

Coding paradigms and possible debates
- functions: I do not adhere to the 'minimize-function-length-clean-code-paradigm' ( AKA functions should be AT MOST 2-4 lines).
  functions should adhere to SRP but splitting anything beyond 4 lines into 2 functions makes it harder (to me) to read code and keep
  context in mind while jumping around files trying understand which function does what. I prefer longer (SRP) functions where as
  many instructions as possible are located at the same place on my screen.

Design patterns (to be implemented)
- Factory for orders: create objects of unique type, subtype decided by user, instantiation taken care of via decicated factory-function.
- Factory for OrderExecution: given an order (eg market vs limit) instantiate the right execution algorithm.

Data structures used
- SortedDict for orderbook price levels -> O(1) access to any price level, especially O(1) access to top of book
- OrderedDict for order queues at given level: dedicated method for FIFO queues + clear functionality intent (Python base dict now ordered, but using OrderedDict makes it obvious)
- custom data structures for orders, orderbook

Algorithms
- FIFO order queues
- main order types and execution rules (limit/market, fill-or-kill/good-till-cancelled)

Design choices
- Most classes implemented as dataclasses with frozen=True even though their values can evolve. Yes this is a bit 'hacky', idea was to enforce permanence of the object structure and its most important features (an order once created will only see changes in quantity filled, an orderbook will always have 2 sides bid/ask...). Gives a good idea of which constraints will need to be applied with a strict type language for a more robust implementation.
- Ask forgiveness, not permission. Pythonic way of handling errors: try and handle any problem later rather than checking for hedge-cases prior to their occurence (in most cases). Code more readable, faster to develop, still robust.
- Bottom-up test-oriented development: dev from bottom module (order) up to the top (full orderbook), module by module, developing test-cases in parallel with each module. 
