"""Jig script parser.

Jig scripts use Python's surface syntax but are their own small language. We use
``ast.parse`` purely as a tokenizer/grammar (it never executes code) and then accept only a
whitelist of node types, which the runner in ``script.py`` interprets itself:

    script     := statement*
    statement  := call | target '=' (call | expr) | target op'=' expr | expr_call
                | 'if' expr ':' block ('elif' expr ':' block)* ['else' ':' block]
                | 'for' names 'in' expr ':' block
                | 'while' expr ':' block              (capped by config script.max_while_iterations)
                | 'break' | 'continue' | 'pass'
    call       := COMMAND '(' [expr] (',' NAME '=' expr)* ')'     an agent/procedure step
    expr       := literal | ref | expr '[' expr ']' | expr '[' expr? ':' expr? ']' | expr '.' NAME
                | expr binop expr | unop expr | expr cmp expr | expr and/or expr
                | expr 'if' expr 'else' expr | f-string | BUILTIN '(' args ')' | expr '.' METHOD '(' args ')'
    ref        := NAME ('.' NAME)*                    e.g.  spec   spec.id   spec.output.summary

Dotted names are *data lookups* resolved by the runner against the bound value, never Python
attribute access; method calls are dispatched through a fixed table (``datatypes.METHODS``).
Command calls must be a statement of their own (or the right side of an assignment), so every
agent step is visible in the script. Names starting with '_' are rejected. Imports, function
and class definitions, lambdas, comprehensions, ``**``, ``with``, ``try`` and the rest are
rejected with a positioned error.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Any

from .datatypes import BUILTINS, METHOD_NAMES


class ParseError(ValueError):
    def __init__(self, message: str, line: int | None = None, col: int | None = None):
        loc = f"line {line}" + (f", col {col}" if col is not None else "") if line else ""
        super().__init__(f"{message}" + (f" ({loc})" if loc else ""))
        self.line = line
        self.col = col


# ── expressions ─────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Ref:
    """Reference to a variable (``spec``) optionally followed by a data path (``spec.output.summary``)."""
    name: str
    path: tuple[str, ...] = ()

    def __str__(self) -> str:
        return ".".join((self.name, *self.path))


@dataclass(frozen=True)
class Attr:          # data lookup on a computed value: xs[0].id
    base: Any
    name: str


@dataclass(frozen=True)
class Index:         # xs[0], m["key"]
    base: Any
    key: Any


@dataclass(frozen=True)
class Slice:         # xs[1:3]
    base: Any
    lo: Any
    hi: Any


@dataclass(frozen=True)
class BinOp:
    op: str
    left: Any
    right: Any


@dataclass(frozen=True)
class Unary:
    op: str          # '-' or 'not'
    operand: Any


@dataclass(frozen=True)
class BoolOp:
    op: str          # 'and' or 'or'
    values: tuple


@dataclass(frozen=True)
class Compare:
    left: Any
    ops: tuple
    rights: tuple


@dataclass(frozen=True)
class Cond:          # a if test else b
    test: Any
    a: Any
    b: Any


@dataclass(frozen=True)
class FStr:
    parts: tuple     # str or expr


@dataclass(frozen=True)
class Call:          # builtin function
    func: str
    args: tuple
    kwargs: tuple    # ((name, expr), ...)


@dataclass(frozen=True)
class Method:        # value.method(args)
    base: Any
    name: str
    args: tuple


# Literal containers stay plain Python lists/dicts (possibly holding expressions), so a fully
# constant argument parses to exactly the value written.


# ── statements ──────────────────────────────────────────────────────────
@dataclass
class Statement:
    """A command call (one agent or procedure step), optionally assigned."""
    command: str
    target: Any = None
    kwargs: dict[str, Any] = field(default_factory=dict)
    bind: str | None = None          # simple `name = command(...)`
    line: int = 0
    source: str = ""
    bind_target: Any = None          # set instead of bind for `m["k"] = command(...)`


@dataclass
class Assign:
    target: Any                      # str | tuple[str, ...] | Index
    value: Any
    line: int = 0
    source: str = ""


@dataclass
class AugAssign:
    target: Any                      # str | Index
    op: str
    value: Any
    line: int = 0
    source: str = ""


@dataclass
class ExprStmt:
    expr: Any
    line: int = 0
    source: str = ""


@dataclass
class If:
    test: Any
    body: list
    orelse: list
    line: int = 0
    source: str = ""


@dataclass
class For:
    target: Any                      # str | tuple[str, ...]
    iter: Any
    body: list
    line: int = 0
    source: str = ""


@dataclass
class While:
    test: Any
    body: list
    line: int = 0
    source: str = ""


@dataclass
class Break:
    line: int = 0
    source: str = ""


@dataclass
class Continue:
    line: int = 0
    source: str = ""


@dataclass
class Pass:
    line: int = 0
    source: str = ""


BINOPS = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/", ast.FloorDiv: "//", ast.Mod: "%"}
CMPOPS = {ast.Eq: "==", ast.NotEq: "!=", ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">=",
          ast.In: "in", ast.NotIn: "not in", ast.Is: "is", ast.IsNot: "is not"}
RESERVED = {"true", "false", "null"}


def _check_name(name: str, node: ast.AST) -> None:
    if name.startswith("_"):
        raise ParseError(f"names starting with '_' are not allowed ('{name}')", getattr(node, "lineno", None),
                         getattr(node, "col_offset", None))


class _Parser:
    def __init__(self, source: str, known_commands: set[str] | None, predefined: set[str] | None):
        self.lines = source.splitlines()
        self.commands = known_commands
        self.bound: set[str] = set(predefined or ())
        self.loop_depth = 0

    # ── helpers ─────────────────────────────────────────────────────────
    def _src(self, node: ast.AST) -> str:
        end = getattr(node, "end_lineno", node.lineno) or node.lineno
        if isinstance(node, (ast.If, ast.For, ast.While)):
            end = node.lineno           # header line only for compound statements
        return "\n".join(self.lines[node.lineno - 1:end]).strip()

    def _is_command(self, name: str) -> bool:
        if name in BUILTINS:
            return False
        return self.commands is None or name in self.commands

    def _use(self, expr: Any, line: int) -> None:
        """References must point at a name bound earlier in the script (or supplied from outside)."""
        for r in _refs(expr):
            if r.name not in self.bound:
                raise ParseError(f"reference to undefined variable '{r.name}'", line)

    def _bind(self, target: Any, node: ast.AST) -> None:
        names = target if isinstance(target, tuple) else (target,) if isinstance(target, str) else ()
        for n in names:
            if n in RESERVED or n in BUILTINS:
                raise ParseError(f"'{n}' is reserved and cannot be assigned", node.lineno)
            self.bound.add(n)

    # ── expressions ─────────────────────────────────────────────────────
    def expr(self, node: ast.AST) -> Any:
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (str, int, float, bool)) or node.value is None:
                return node.value
            raise ParseError(f"unsupported constant {node.value!r}", node.lineno, node.col_offset)
        if isinstance(node, (ast.List, ast.Tuple)):
            return [self.expr(e) for e in node.elts]
        if isinstance(node, ast.Dict):
            out = {}
            for k, v in zip(node.keys, node.values):
                if k is None or not (isinstance(k, ast.Constant) and isinstance(k.value, str)):
                    raise ParseError("dict keys must be string literals", node.lineno, node.col_offset)
                out[k.value] = self.expr(v)
            return out
        if isinstance(node, ast.Name):
            if node.id in RESERVED:
                return {"true": True, "false": False, "null": None}[node.id]
            _check_name(node.id, node)
            return Ref(node.id)
        if isinstance(node, ast.Attribute):
            _check_name(node.attr, node)
            if self._is_command_call(node.value):
                raise ParseError("dotted references must start with a variable name; assign the command's "
                                 "result first (x = command(...)) and use x.<field>", node.lineno, node.col_offset)
            base = self.expr(node.value)
            if isinstance(base, Ref):
                return Ref(base.name, (*base.path, node.attr))
            return Attr(base, node.attr)
        if isinstance(node, ast.Subscript):
            base = self.expr(node.value)
            if isinstance(node.slice, ast.Slice):
                if node.slice.step is not None:
                    raise ParseError("slice steps are not supported", node.lineno, node.col_offset)
                lo = self.expr(node.slice.lower) if node.slice.lower else None
                hi = self.expr(node.slice.upper) if node.slice.upper else None
                return Slice(base, lo, hi)
            return Index(base, self.expr(node.slice))
        if isinstance(node, ast.BinOp):
            op = BINOPS.get(type(node.op))
            if not op:
                raise ParseError(f"operator '{type(node.op).__name__}' is not supported", node.lineno,
                                 node.col_offset)
            return BinOp(op, self.expr(node.left), self.expr(node.right))
        if isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.USub):
                inner = self.expr(node.operand)
                if isinstance(inner, (int, float)) and not isinstance(inner, bool):
                    return -inner
                return Unary("-", inner)
            if isinstance(node.op, ast.Not):
                return Unary("not", self.expr(node.operand))
            raise ParseError(f"operator '{type(node.op).__name__}' is not supported", node.lineno, node.col_offset)
        if isinstance(node, ast.BoolOp):
            return BoolOp("and" if isinstance(node.op, ast.And) else "or", tuple(self.expr(v) for v in node.values))
        if isinstance(node, ast.Compare):
            ops = []
            for o in node.ops:
                if type(o) not in CMPOPS:
                    raise ParseError("unsupported comparison", node.lineno, node.col_offset)
                ops.append(CMPOPS[type(o)])
            return Compare(self.expr(node.left), tuple(ops), tuple(self.expr(c) for c in node.comparators))
        if isinstance(node, ast.IfExp):
            return Cond(self.expr(node.test), self.expr(node.body), self.expr(node.orelse))
        if isinstance(node, ast.JoinedStr):
            parts = []
            for v in node.values:
                if isinstance(v, ast.Constant):
                    parts.append(v.value)
                elif isinstance(v, ast.FormattedValue):
                    if v.format_spec is not None or v.conversion not in (-1, None):
                        raise ParseError("f-string format specs and conversions are not supported", node.lineno)
                    parts.append(self.expr(v.value))
            return FStr(tuple(parts))
        if isinstance(node, ast.Call):
            return self.call_expr(node)
        raise ParseError(f"unsupported expression '{type(node).__name__}'; allowed are literals, variables, "
                         f"operators, comparisons, builtins and data-type methods", getattr(node, "lineno", None),
                         getattr(node, "col_offset", None))

    def _args(self, node: ast.Call) -> tuple[list, dict]:
        for a in node.args:
            if isinstance(a, ast.Starred):
                raise ParseError("star-arguments are not allowed", node.lineno)
        kwargs: dict[str, Any] = {}
        for kw in node.keywords:
            if kw.arg is None:
                raise ParseError("**kwargs are not allowed", node.lineno)
            if kw.arg in kwargs:
                raise ParseError(f"duplicate parameter '{kw.arg}'", node.lineno)
            _check_name(kw.arg, node)
            kwargs[kw.arg] = self.expr(kw.value)
        return [self.expr(a) for a in node.args], kwargs

    def call_expr(self, node: ast.Call) -> Any:
        """A call inside an expression: a builtin or a data-type method, never a command."""
        f = node.func
        if isinstance(f, ast.Name):
            if f.id in BUILTINS:
                args, kwargs = self._args(node)
                return Call(f.id, tuple(args), tuple(kwargs.items()))
            if self._is_command(f.id):
                raise ParseError(f"command '{f.id}' must be a statement of its own or the right side of an "
                                 f"assignment, not part of an expression", node.lineno, node.col_offset)
            raise ParseError(f"unknown command '{f.id}'", node.lineno, node.col_offset)
        if isinstance(f, ast.Attribute):
            _check_name(f.attr, f)
            if f.attr not in METHOD_NAMES:
                raise ParseError(f"unknown method '{f.attr}'; methods are only available on lists, maps, "
                                 f"queues, sets and strings (see docs/language.md)", node.lineno, node.col_offset)
            args, kwargs = self._args(node)
            if kwargs:
                raise ParseError("methods take positional arguments only", node.lineno)
            return Method(self.expr(f.value), f.attr, tuple(args))
        raise ParseError("command name must be a bare identifier", node.lineno, node.col_offset)

    def command(self, node: ast.Call) -> tuple[str, Any, dict]:
        name = node.func.id
        if len(node.args) > 1:
            raise ParseError(f"'{name}' accepts at most one positional argument (the target)", node.lineno)
        args, kwargs = self._args(node)
        return name, (args[0] if args else None), kwargs

    def _is_command_call(self, node: ast.AST) -> bool:
        return isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and self._is_command(node.func.id)

    # ── assignment targets ──────────────────────────────────────────────
    def target(self, node: ast.AST, allow_tuple: bool = True) -> Any:
        if isinstance(node, ast.Name):
            _check_name(node.id, node)
            return node.id
        if allow_tuple and isinstance(node, (ast.Tuple, ast.List)) and all(isinstance(e, ast.Name) for e in node.elts):
            for e in node.elts:
                _check_name(e.id, e)
            return tuple(e.id for e in node.elts)
        if isinstance(node, ast.Subscript) and not isinstance(node.slice, ast.Slice):
            t = Index(self.expr(node.value), self.expr(node.slice))
            self._use(t, node.lineno)
            return t
        raise ParseError("assignment target must be a single name, a name[index], or names to unpack",
                         node.lineno)

    # ── statements ──────────────────────────────────────────────────────
    def block(self, nodes: list[ast.AST]) -> list:
        return [self.stmt(n) for n in nodes]

    def stmt(self, node: ast.AST) -> Any:
        line, src = node.lineno, self._src(node)
        if isinstance(node, ast.Expr):
            if self._is_command_call(node.value):
                name, target, kwargs = self.command(node.value)
                for v in [target, *kwargs.values()]:
                    self._use(v, line)
                return Statement(name, target, kwargs, None, line, src)
            if isinstance(node.value, ast.Call):
                e = self.call_expr(node.value)
                self._use(e, line)
                return ExprStmt(e, line, src)
            raise ParseError("each statement must be a command call, an assignment or control flow", line)
        if isinstance(node, ast.Assign):
            if len(node.targets) != 1:
                raise ParseError("assignment target must be a single name", line)
            tnode = node.targets[0]
            if self._is_command_call(node.value):
                name, target, kwargs = self.command(node.value)
                for v in [target, *kwargs.values()]:
                    self._use(v, line)
                t = self.target(tnode, allow_tuple=False)
                self._bind(t, node)
                return Statement(name, target, kwargs, t if isinstance(t, str) else None, line, src,
                                 None if isinstance(t, str) else t)
            value = self.expr(node.value)
            self._use(value, line)
            t = self.target(tnode)
            self._bind(t, node)
            return Assign(t, value, line, src)
        if isinstance(node, ast.AugAssign):
            op = BINOPS.get(type(node.op))
            if not op:
                raise ParseError(f"operator '{type(node.op).__name__}' is not supported", line)
            if self._is_command_call(node.value):
                raise ParseError("a command call cannot be combined with an operator; assign it first", line)
            t = self.target(node.target, allow_tuple=False)
            if isinstance(t, str) and t not in self.bound:
                raise ParseError(f"reference to undefined variable '{t}'", line)
            value = self.expr(node.value)
            self._use(value, line)
            return AugAssign(t, op, value, line, src)
        if isinstance(node, ast.If):
            test = self.expr(node.test)
            self._use(test, line)
            return If(test, self.block(node.body), self.block(node.orelse), line, src)
        if isinstance(node, ast.For):
            if node.orelse:
                raise ParseError("for ... else is not supported", line)
            it = self.expr(node.iter)
            self._use(it, line)
            t = self.target(node.target)
            if isinstance(t, Index):
                raise ParseError("loop variable must be a name or names to unpack", line)
            self._bind(t, node)
            self.loop_depth += 1
            body = self.block(node.body)
            self.loop_depth -= 1
            return For(t, it, body, line, src)
        if isinstance(node, ast.While):
            if node.orelse:
                raise ParseError("while ... else is not supported", line)
            test = self.expr(node.test)
            self._use(test, line)
            self.loop_depth += 1
            body = self.block(node.body)
            self.loop_depth -= 1
            return While(test, body, line, src)
        if isinstance(node, (ast.Break, ast.Continue)):
            if not self.loop_depth:
                raise ParseError(f"'{src}' outside a loop", line)
            return (Break if isinstance(node, ast.Break) else Continue)(line, src)
        if isinstance(node, ast.Pass):
            return Pass(line, src)
        raise ParseError(f"statement type '{type(node).__name__}' is not allowed", line)


def parse(source: str, known_commands: set[str] | None = None,
          predefined: set[str] | None = None) -> list:
    """`predefined` names are variables supplied from outside (e.g. one row of a batch file)."""
    try:
        tree = ast.parse(source, mode="exec")
    except SyntaxError as e:
        raise ParseError(f"syntax error: {e.msg}", e.lineno, e.offset) from None
    p = _Parser(source, known_commands, predefined)
    return p.block(tree.body)


def walk(stmts: list):
    """Every statement, depth first, including those nested in if/for/while blocks."""
    for s in stmts:
        yield s
        if isinstance(s, If):
            yield from walk(s.body)
            yield from walk(s.orelse)
        elif isinstance(s, (For, While)):
            yield from walk(s.body)


def _refs(v: Any):
    if isinstance(v, Ref):
        yield v
    elif isinstance(v, list):
        for x in v:
            yield from _refs(x)
    elif isinstance(v, dict):
        for x in v.values():
            yield from _refs(x)
    elif isinstance(v, (Attr, Index, Slice, BinOp, Unary, BoolOp, Compare, Cond, FStr, Call, Method)):
        for f in v.__dataclass_fields__:
            yield from _refs(getattr(v, f))
    elif isinstance(v, tuple):
        for x in v:
            yield from _refs(x)
