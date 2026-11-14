"""Lattice script parser.

Lattice scripts *look* like Python function calls but are a declarative command
language. We use ``ast.parse`` purely as a tokenizer/grammar (it never executes
code) and then accept only a tiny whitelist of node types:

    script     := statement*
    statement  := call | NAME '=' call
    call       := COMMAND '(' [literal] (',' NAME '=' literal)* ')'
    literal    := str | int | float | bool | None | list | tuple | dict | NAME(ref)

Anything else (attribute access, arithmetic, comprehensions, lambdas, imports,
subscripts, f-strings, nested calls...) is rejected with a positioned error.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Any


class ParseError(ValueError):
    def __init__(self, message: str, line: int | None = None, col: int | None = None):
        loc = f"line {line}" + (f", col {col}" if col is not None else "") if line else ""
        super().__init__(f"{message}" + (f" ({loc})" if loc else ""))
        self.line = line
        self.col = col


@dataclass(frozen=True)
class Ref:
    """Reference to a variable bound by an earlier statement (``x = requirement(...)``)."""
    name: str


@dataclass
class Statement:
    command: str
    target: Any = None
    kwargs: dict[str, Any] = field(default_factory=dict)
    bind: str | None = None
    line: int = 0
    source: str = ""


def _literal(node: ast.AST) -> Any:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (str, int, float, bool)) or node.value is None:
            return node.value
        raise ParseError(f"unsupported constant {node.value!r}", node.lineno, node.col_offset)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub) and isinstance(node.operand, ast.Constant) \
            and isinstance(node.operand.value, (int, float)) and not isinstance(node.operand.value, bool):
        return -node.operand.value
    if isinstance(node, (ast.List, ast.Tuple)):
        return [_literal(e) for e in node.elts]
    if isinstance(node, ast.Dict):
        out = {}
        for k, v in zip(node.keys, node.values):
            if k is None or not (isinstance(k, ast.Constant) and isinstance(k.value, str)):
                raise ParseError("dict keys must be string literals", node.lineno, node.col_offset)
            out[k.value] = _literal(v)
        return out
    if isinstance(node, ast.Name):
        if node.id in ("true", "false", "null"):
            return {"true": True, "false": False, "null": None}[node.id]
        return Ref(node.id)
    raise ParseError(f"unsupported expression '{type(node).__name__}'; only literals and variable "
                     f"references are allowed as arguments", getattr(node, "lineno", None),
                     getattr(node, "col_offset", None))


def _call(node: ast.AST, known_commands: set[str] | None) -> tuple[str, Any, dict[str, Any]]:
    if not isinstance(node, ast.Call):
        raise ParseError("each statement must be a command call", getattr(node, "lineno", None))
    if not isinstance(node.func, ast.Name):
        raise ParseError("command name must be a bare identifier", node.lineno, node.col_offset)
    name = node.func.id
    if known_commands is not None and name not in known_commands:
        raise ParseError(f"unknown command '{name}'", node.lineno, node.col_offset)
    if len(node.args) > 1:
        raise ParseError(f"'{name}' accepts at most one positional argument (the target)", node.lineno)
    for a in node.args:
        if isinstance(a, ast.Starred):
            raise ParseError("star-arguments are not allowed", node.lineno)
    target = _literal(node.args[0]) if node.args else None
    kwargs: dict[str, Any] = {}
    for kw in node.keywords:
        if kw.arg is None:
            raise ParseError("**kwargs are not allowed", node.lineno)
        if kw.arg in kwargs:
            raise ParseError(f"duplicate parameter '{kw.arg}'", node.lineno)
        kwargs[kw.arg] = _literal(kw.value)
    return name, target, kwargs


def parse(source: str, known_commands: set[str] | None = None,
          predefined: set[str] | None = None) -> list[Statement]:
    """`predefined` names are variables supplied from outside (e.g. one row of a batch file)."""
    try:
        tree = ast.parse(source, mode="exec")
    except SyntaxError as e:
        raise ParseError(f"syntax error: {e.msg}", e.lineno, e.offset) from None
    lines = source.splitlines()
    statements: list[Statement] = []
    bound: set[str] = set(predefined or ())
    for node in tree.body:
        bind = None
        if isinstance(node, ast.Expr):
            call = node.value
        elif isinstance(node, ast.Assign):
            if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
                raise ParseError("assignment target must be a single name", node.lineno)
            bind = node.targets[0].id
            call = node.value
        else:
            raise ParseError(f"statement type '{type(node).__name__}' is not allowed", node.lineno)
        name, target, kwargs = _call(call, known_commands)
        # References must point at an earlier binding.
        for v in [target, *kwargs.values()]:
            for r in _refs(v):
                if r.name not in bound:
                    raise ParseError(f"reference to undefined variable '{r.name}'", node.lineno)
        end = getattr(node, "end_lineno", node.lineno) or node.lineno
        statements.append(Statement(name, target, kwargs, bind, node.lineno,
                                    "\n".join(lines[node.lineno - 1:end]).strip()))
        if bind:
            bound.add(bind)
    return statements


def _refs(v: Any):
    if isinstance(v, Ref):
        yield v
    elif isinstance(v, list):
        for x in v:
            yield from _refs(x)
    elif isinstance(v, dict):
        for x in v.values():
            yield from _refs(x)
