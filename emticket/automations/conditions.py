from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Tuple


@dataclass(frozen=True)
class EvalContext:
    obj: Any
    actor: Any
    trigger: str
    changes: Dict[str, Tuple[Any, Any]]
    extra: Dict[str, Any]


def _get_attr(obj: Any, path: str) -> Any:
    cur = obj
    for part in path.split("."):
        if cur is None:
            return None
        cur = getattr(cur, part, None)
    return cur


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if value == "":
        return True
    if isinstance(value, (list, tuple, dict, set)) and len(value) == 0:
        return True
    return False


def _cmp(op: str, left: Any, right: Any, ctx: EvalContext, field: str) -> bool:
    op = op.lower().strip()

    if op == "eq":
        return left == right
    if op == "ne":
        return left != right
    if op == "contains":
        if left is None:
            return False
        return str(right).lower() in str(left).lower()
    if op == "in":
        if right is None:
            return False
        return left in right
    if op == "gt":
        return left is not None and right is not None and left > right
    if op == "gte":
        return left is not None and right is not None and left >= right
    if op == "lt":
        return left is not None and right is not None and left < right
    if op == "lte":
        return left is not None and right is not None and left <= right
    if op == "is_empty":
        return _is_empty(left)
    if op == "not_empty":
        return not _is_empty(left)
    if op == "changed":
        return field in ctx.changes
    if op == "changed_to":
        if field not in ctx.changes:
            return False
        _, new = ctx.changes[field]
        return new == right
    if op == "changed_from":
        if field not in ctx.changes:
            return False
        old, _ = ctx.changes[field]
        return old == right

    return False


def eval_condition(condition: Dict[str, Any], ctx: EvalContext) -> bool:
    field = (condition.get("field") or "").strip()
    op = (condition.get("op") or "").strip()
    value = condition.get("value", None)

    if not field or not op:
        return False

    left = _get_attr(ctx.obj, field)
    return _cmp(op, left, value, ctx, field)


def eval_group(conditions: Dict[str, Any], ctx: EvalContext) -> bool:
    all_list = conditions.get("all", [])
    any_list = conditions.get("any", [])

    if not isinstance(all_list, list) or not isinstance(any_list, list):
        return False

    if all_list and not all(eval_condition(c, ctx) for c in all_list):
        return False

    if any_list and not any(eval_condition(c, ctx) for c in any_list):
        return False

    return True

