from __future__ import annotations

import ast
import operator
from typing import Any, Dict, Iterable, List


ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

ALLOWED_UNARY = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

SAFE_FUNCTIONS = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
}


def evaluate_calculations(
    rows: List[Dict[str, Any]],
    calculations: Iterable[Dict[str, Any]] | None,
) -> List[Dict[str, Any]]:
    """
    Evaluate calculated fields for each row in the result set.

    Calculations use safe arithmetic expressions referencing existing field
    keys (e.g., "revenue - cost").
    """
    if not calculations:
        return rows

    compiled = []
    for calc in calculations:
        expression = calc.get("expression")
        target = calc.get("id") or calc.get("field") or calc.get("key")
        if not expression or not target:
            continue
        compiled.append((target, _compile_expression(expression)))

    if not compiled:
        return rows

    for row in rows:
        context = dict(row)
        for target, expr in compiled:
            try:
                row[target] = expr(context)
            except ZeroDivisionError:
                row[target] = None
            except Exception:
                row[target] = None
    return rows


def _compile_expression(expression: str):
    tree = ast.parse(expression, mode="eval")
    _validate_ast(tree)

    def evaluator(context: Dict[str, Any]):
        return _eval_node(tree.body, context)

    return evaluator


def _validate_ast(node: ast.AST) -> None:
    allowed_nodes = (
        ast.Expression,
        ast.BinOp,
        ast.UnaryOp,
        ast.Constant,
        ast.Name,
        ast.Call,
        ast.Load,
        ast.Compare,
        ast.BoolOp,
        ast.And,
        ast.Or,
        ast.Gt,
        ast.GtE,
        ast.Lt,
        ast.LtE,
        ast.Eq,
        ast.NotEq,
        ast.IfExp,
    )
    if not isinstance(node, allowed_nodes):
        raise ValueError(f"Unsupported expression node: {type(node).__name__}")

    for child in ast.iter_child_nodes(node):
        _validate_ast(child)


def _eval_node(node: ast.AST, context: Dict[str, Any]):
    if isinstance(node, ast.Constant):
        return node.value

    if isinstance(node, ast.Name):
        return context.get(node.id)

    if isinstance(node, ast.BinOp):
        left = _eval_node(node.left, context)
        right = _eval_node(node.right, context)
        op = ALLOWED_OPERATORS.get(type(node.op))
        if op is None:
            raise ValueError(f"Unsupported binary operator: {type(node.op).__name__}")
        return op(left, right)

    if isinstance(node, ast.UnaryOp):
        operand = _eval_node(node.operand, context)
        op = ALLOWED_UNARY.get(type(node.op))
        if op is None:
            raise ValueError(f"Unsupported unary operator: {type(node.op).__name__}")
        return op(operand)

    if isinstance(node, ast.Call):
        func_name = getattr(node.func, "id", None)
        if func_name not in SAFE_FUNCTIONS:
            raise ValueError(f"Function '{func_name}' is not allowed in calculations.")
        func = SAFE_FUNCTIONS[func_name]
        args = [_eval_node(arg, context) for arg in node.args]
        kwargs = {kw.arg: _eval_node(kw.value, context) for kw in node.keywords}
        return func(*args, **kwargs)

    if isinstance(node, ast.Compare):
        left = _eval_node(node.left, context)
        result = True
        for op, comparator in zip(node.ops, node.comparators):
            right = _eval_node(comparator, context)
            result = result and _compare(left, right, op)
            left = right
        return result

    if isinstance(node, ast.BoolOp):
        values = [_eval_node(value, context) for value in node.values]
        if isinstance(node.op, ast.And):
            return all(values)
        if isinstance(node.op, ast.Or):
            return any(values)
        raise ValueError(f"Unsupported boolean operator: {type(node.op).__name__}")

    if isinstance(node, ast.IfExp):
        test = _eval_node(node.test, context)
        return _eval_node(node.body if test else node.orelse, context)

    raise ValueError(f"Unsupported expression element: {type(node).__name__}")


def _compare(left: Any, right: Any, op: ast.AST) -> bool:
    if isinstance(op, ast.Gt):
        return left > right
    if isinstance(op, ast.GtE):
        return left >= right
    if isinstance(op, ast.Lt):
        return left < right
    if isinstance(op, ast.LtE):
        return left <= right
    if isinstance(op, ast.Eq):
        return left == right
    if isinstance(op, ast.NotEq):
        return left != right
    raise ValueError(f"Unsupported comparison operator: {type(op).__name__}")
