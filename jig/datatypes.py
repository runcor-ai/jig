"""Built-in functions and data types for Jig scripts: list, map, queue, set (and strings).

Everything here runs locally and costs nothing; only commands call agents. Methods are
dispatched through the fixed ``METHODS`` table, never ``getattr``, so a script can reach only
the operations listed here. Every value a script builds is size-checked (``Limits.max_items``)
*before* it is allocated where that is possible, so a script cannot exhaust memory.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any, Callable

from .errors import JigError


@dataclass
class Limits:
    max_items: int = 100_000          # longest list/map/queue/set/string a script may build
    max_int: int = 2 ** 63


def fail(msg: str) -> JigError:
    return JigError("E_SCRIPT", msg)


class Queue:
    """First in, first out. push() adds at the back, pop() takes from the front."""
    __slots__ = ("items",)

    def __init__(self, items=()):
        self.items = deque(items)

    def __len__(self):
        return len(self.items)

    def __iter__(self):
        return iter(self.items)

    def __contains__(self, x):
        return x in self.items

    def __eq__(self, other):
        return isinstance(other, Queue) and list(self.items) == list(other.items)

    def __repr__(self):
        return f"queue({list(self.items)!r})"


def type_name(v: Any) -> str:
    if v is None:
        return "null"
    return {bool: "bool", int: "int", float: "number", str: "string", list: "list", dict: "map",
            set: "set", Queue: "queue"}.get(type(v), type(v).__name__)


def size(v: Any) -> int:
    return len(v) if isinstance(v, (str, list, dict, set, Queue)) else 0


def guard(v: Any, lim: Limits) -> Any:
    if isinstance(v, bool):
        return v
    if isinstance(v, int) and abs(v) > lim.max_int:
        raise fail(f"integer {str(v)[:20]}... is too large")
    if size(v) > lim.max_items:
        raise fail(f"{type_name(v)} would have {size(v)} items; the limit is {lim.max_items} "
                   f"(config script.max_items)")
    return v


def precheck(n: int, lim: Limits, what: str = "result") -> None:
    if n > lim.max_items:
        raise fail(f"{what} would have {n} items; the limit is {lim.max_items} (config script.max_items)")


def _iterable(v: Any, fn: str) -> list:
    if isinstance(v, (list, str, set, Queue)):
        return list(sorted(v, key=_sort_key) if isinstance(v, set) else v)
    if isinstance(v, dict):
        return list(v)
    raise fail(f"{fn}() needs a list, map, queue, set or string, got {type_name(v)}")


def _sort_key(x: Any):
    return (type_name(x), x) if isinstance(x, (int, float, str, bool)) or x is None else (type_name(x), str(x))


def _hashable(x: Any, what: str) -> Any:
    if isinstance(x, (str, int, float, bool)) or x is None:
        return x
    raise fail(f"{what} must be a string, number, bool or null, got {type_name(x)}")


# ── builtin functions ───────────────────────────────────────────────────
def b_len(lim, v):
    if isinstance(v, (str, list, dict, set, Queue)):
        return len(v)
    raise fail(f"len() needs a list, map, queue, set or string, got {type_name(v)}")


def b_range(lim, *a):
    if not 1 <= len(a) <= 3 or not all(isinstance(x, int) and not isinstance(x, bool) for x in a):
        raise fail("range() takes 1 to 3 integers")
    r = range(*a)
    precheck(len(r), lim, "range()")
    return list(r)


def b_list(lim, v=None):
    return [] if v is None else _iterable(v, "list")


def b_map(lim, v=None):
    if v is None:
        return {}
    if isinstance(v, dict):
        return dict(v)
    if isinstance(v, list) and all(isinstance(p, list) and len(p) == 2 for p in v):
        return {_hashable(k, "map key"): x for k, x in v}
    raise fail("map() takes nothing, a map, or a list of [key, value] pairs")


def b_queue(lim, v=None):
    return Queue() if v is None else Queue(_iterable(v, "queue"))


def b_set(lim, v=None):
    return set() if v is None else {_hashable(x, "set item") for x in _iterable(v, "set")}


def b_str(lim, v=""):
    from .script import to_data  # late import: shared JSON conversion
    import json
    if isinstance(v, str):
        return v
    if isinstance(v, bool) or v is None:
        return {True: "true", False: "false", None: "null"}[v]
    if isinstance(v, (int, float)):
        return str(v)
    s = json.dumps(to_data(v), default=str)
    precheck(len(s), lim, "str()")
    return s


def b_int(lim, v):
    try:
        if isinstance(v, str) and len(v) > 30:
            raise ValueError
        return int(v)
    except (TypeError, ValueError):
        raise fail(f"int() cannot convert {type_name(v)} {str(v)[:40]!r}") from None


def b_float(lim, v):
    try:
        return float(v)
    except (TypeError, ValueError):
        raise fail(f"number() cannot convert {type_name(v)} {str(v)[:40]!r}") from None


def b_bool(lim, v):
    return truthy(v)


def b_sorted(lim, v, reverse=False):
    items = _iterable(v, "sorted")
    try:
        return sorted(items, reverse=bool(reverse))
    except TypeError:
        raise fail("sorted() items must all be numbers or all be strings") from None


def _agg(name, fn):
    def f(lim, *a):
        items = a[0] if len(a) == 1 else list(a)
        items = _iterable(items, name)
        if not items:
            raise fail(f"{name}() of an empty sequence")
        try:
            return fn(items)
        except TypeError:
            raise fail(f"{name}() items must all be numbers or all be strings") from None
    return f


def b_sum(lim, v):
    items = _iterable(v, "sum")
    if not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in items):
        raise fail("sum() needs numbers")
    return sum(items)


def b_abs(lim, v):
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return abs(v)
    raise fail(f"abs() needs a number, got {type_name(v)}")


def b_round(lim, v, n=0):
    if isinstance(v, (int, float)) and isinstance(n, int):
        return round(v, n) if n else round(v)
    raise fail("round() needs a number")


def b_enumerate(lim, v, start=0):
    return [[i, x] for i, x in enumerate(_iterable(v, "enumerate"), start)]


def b_type(lim, v):
    return type_name(v)


def b_print(lim, *a):  # replaced by the runner with one that records output; kept for signature
    return None


BUILTINS: dict[str, Callable] = {
    "len": b_len, "range": b_range, "list": b_list, "map": b_map, "dict": b_map, "queue": b_queue,
    "set": b_set, "str": b_str, "int": b_int, "number": b_float, "float": b_float, "bool": b_bool,
    "sorted": b_sorted, "min": _agg("min", min), "max": _agg("max", max), "sum": b_sum, "abs": b_abs,
    "round": b_round, "enumerate": b_enumerate, "type": b_type, "print": b_print,
    "fail": b_print,   # handled by the runner: stops the script and marks the run failed
}


# ── methods ─────────────────────────────────────────────────────────────
def _need(args, lo, hi, name):
    if not lo <= len(args) <= hi:
        want = lo if lo == hi else f"{lo} to {hi}"
        raise fail(f"{name}() takes {want} argument(s), got {len(args)}")


def _idx(xs, i, name):
    if not isinstance(i, int) or isinstance(i, bool):
        raise fail(f"{name}() index must be an integer")
    if not -len(xs) <= i < len(xs):
        raise fail(f"{name}() index {i} is out of range for a list of {len(xs)}")
    return i


def m_list_append(lim, xs, *a):
    _need(a, 1, 1, "append")
    precheck(len(xs) + 1, lim, "list")
    xs.append(a[0])


def m_list_extend(lim, xs, *a):
    _need(a, 1, 1, "extend")
    other = _iterable(a[0], "extend")
    precheck(len(xs) + len(other), lim, "list")
    xs.extend(other)


def m_list_insert(lim, xs, *a):
    _need(a, 2, 2, "insert")
    precheck(len(xs) + 1, lim, "list")
    if not isinstance(a[0], int):
        raise fail("insert() index must be an integer")
    xs.insert(a[0], a[1])


def m_list_pop(lim, xs, *a):
    _need(a, 0, 1, "pop")
    if not xs:
        raise fail("pop() from an empty list")
    return xs.pop(_idx(xs, a[0], "pop") if a else -1)


def m_list_remove(lim, xs, *a):
    _need(a, 1, 1, "remove")
    if a[0] not in xs:
        raise fail(f"remove(): {str(a[0])[:40]!r} is not in the list")
    xs.remove(a[0])


def m_list_index(lim, xs, *a):
    _need(a, 1, 1, "index")
    if a[0] not in xs:
        raise fail(f"index(): {str(a[0])[:40]!r} is not in the list")
    return xs.index(a[0])


def m_list_sort(lim, xs, *a):
    _need(a, 0, 1, "sort")
    try:
        xs.sort(reverse=bool(a[0]) if a else False)
    except TypeError:
        raise fail("sort() items must all be numbers or all be strings") from None


def m_list_reverse(lim, xs, *a):
    _need(a, 0, 0, "reverse")
    xs.reverse()


def m_copy(lim, v, *a):
    _need(a, 0, 0, "copy")
    import copy
    return copy.deepcopy(v)


def m_map_get(lim, m, *a):
    _need(a, 1, 2, "get")
    return m.get(_hashable(a[0], "map key"), a[1] if len(a) > 1 else None)


def m_map_put(lim, m, *a):
    _need(a, 2, 2, "put")
    k = _hashable(a[0], "map key")
    if k not in m:
        precheck(len(m) + 1, lim, "map")
    m[k] = a[1]


def m_map_remove(lim, m, *a):
    _need(a, 1, 1, "remove")
    k = _hashable(a[0], "map key")
    if k not in m:
        raise fail(f"remove(): map has no key {str(k)[:40]!r}")
    return m.pop(k)


def m_map_has(lim, m, *a):
    _need(a, 1, 1, "has")
    return _hashable(a[0], "map key") in m


def m_map_keys(lim, m, *a):
    _need(a, 0, 0, "keys")
    return list(m.keys())


def m_map_values(lim, m, *a):
    _need(a, 0, 0, "values")
    return list(m.values())


def m_map_items(lim, m, *a):
    _need(a, 0, 0, "items")
    return [[k, v] for k, v in m.items()]


def m_queue_push(lim, q, *a):
    _need(a, 1, 1, "push")
    precheck(len(q) + 1, lim, "queue")
    q.items.append(a[0])


def m_queue_pop(lim, q, *a):
    _need(a, 0, 0, "pop")
    if not q.items:
        raise fail("pop() from an empty queue")
    return q.items.popleft()


def m_queue_peek(lim, q, *a):
    _need(a, 0, 0, "peek")
    if not q.items:
        raise fail("peek() at an empty queue")
    return q.items[0]


def m_set_add(lim, s, *a):
    _need(a, 1, 1, "add")
    x = _hashable(a[0], "set item")
    if x not in s:
        precheck(len(s) + 1, lim, "set")
    s.add(x)


def m_set_remove(lim, s, *a):
    _need(a, 1, 1, "remove")
    x = _hashable(a[0], "set item")
    if x not in s:
        raise fail(f"remove(): {str(x)[:40]!r} is not in the set")
    s.remove(x)


def m_set_has(lim, s, *a):
    _need(a, 1, 1, "has")
    return _hashable(a[0], "set item") in s


def _set_op(name, fn):
    def f(lim, s, *a):
        _need(a, 1, 1, name)
        other = {_hashable(x, "set item") for x in _iterable(a[0], name)}
        out = fn(s, other)
        return guard(out, lim)
    return f


def _str1(name, fn):
    def f(lim, s, *a):
        _need(a, 0, 0, name)
        return fn(s)
    return f


def m_str_split(lim, s, *a):
    _need(a, 0, 1, "split")
    if a and (not isinstance(a[0], str) or not a[0]):
        raise fail("split() separator must be a non-empty string")
    out = s.split(a[0]) if a else s.split()
    return guard(out, lim)


def m_str_replace(lim, s, *a):
    _need(a, 2, 2, "replace")
    old, new = a
    if not isinstance(old, str) or not isinstance(new, str):
        raise fail("replace() takes two strings")
    n = s.count(old) if old else len(s) + 1
    precheck(len(s) + n * (len(new) - len(old)), lim, "replace()")
    return s.replace(old, new)


def m_str_join(lim, sep, *a):
    _need(a, 1, 1, "join")
    items = _iterable(a[0], "join")
    if not all(isinstance(x, str) for x in items):
        raise fail("join() items must all be strings (use str() on each)")
    precheck(sum(map(len, items)) + len(sep) * max(len(items) - 1, 0), lim, "join()")
    return sep.join(items)


def m_str_test(name, fn):
    def f(lim, s, *a):
        _need(a, 1, 1, name)
        if not isinstance(a[0], str):
            raise fail(f"{name}() takes a string")
        return fn(s, a[0])
    return f


METHODS: dict[type, dict[str, Callable]] = {
    list: {"append": m_list_append, "push": m_list_append, "extend": m_list_extend, "insert": m_list_insert,
           "pop": m_list_pop, "remove": m_list_remove, "index": m_list_index, "sort": m_list_sort,
           "reverse": m_list_reverse, "copy": m_copy},
    dict: {"get": m_map_get, "put": m_map_put, "remove": m_map_remove, "has": m_map_has, "keys": m_map_keys,
           "values": m_map_values, "items": m_map_items, "copy": m_copy},
    Queue: {"push": m_queue_push, "pop": m_queue_pop, "peek": m_queue_peek, "copy": m_copy},
    set: {"add": m_set_add, "remove": m_set_remove, "has": m_set_has, "copy": m_copy,
          "union": _set_op("union", lambda a, b: a | b), "intersection": _set_op("intersection", lambda a, b: a & b),
          "difference": _set_op("difference", lambda a, b: a - b)},
    str: {"lower": _str1("lower", str.lower), "upper": _str1("upper", str.upper), "strip": _str1("strip", str.strip),
          "split": m_str_split, "replace": m_str_replace, "join": m_str_join,
          "startswith": m_str_test("startswith", str.startswith), "endswith": m_str_test("endswith", str.endswith),
          "contains": m_str_test("contains", lambda s, x: x in s)},
}

METHOD_NAMES = {n for table in METHODS.values() for n in table}


def call_method(lim: Limits, base: Any, name: str, args: list) -> Any:
    table = METHODS.get(type(base))
    fn = table.get(name) if table else None
    if fn is None:
        have = ", ".join(sorted(table)) if table else "none"
        raise fail(f"{type_name(base)} has no method '{name}' (available: {have})")
    out = fn(lim, base, *args)
    return guard(out, lim)


def truthy(v: Any) -> bool:
    if isinstance(v, Queue):
        return len(v) > 0
    return bool(v)
