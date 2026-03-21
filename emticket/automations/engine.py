from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from django.db import transaction

from .conditions import EvalContext, eval_group
from .actions import ACTION_REGISTRY, ActionResult, _ensure_ticket
from .models import AutomationRule, AutomationRun


@dataclass
class RuleRunResult:
    rule_id: int
    matched: bool
    actions_executed: List[Dict[str, Any]]
    error: str = ""


class AutomationEngine:
    """
    Runs rules for a given organization + trigger on an object.
    """

    def __init__(self, *, organization_id: int, trigger: str):
        self.organization_id = organization_id
        self.trigger = trigger

    def _load_rules(self) -> List[AutomationRule]:
        return list(
            AutomationRule.objects.filter(
                organization_id=self.organization_id,
                enabled=True,
                trigger=self.trigger,
            ).order_by("priority", "id")
        )

    def run(self, ctx: EvalContext) -> List[RuleRunResult]:
        obj = _ensure_ticket(ctx.obj)

        # Loop prevention in-memory (within request/transaction)
        executed_key = f"_auto_executed_{self.trigger}"
        executed: set = getattr(obj, executed_key, set())
        results: List[RuleRunResult] = []

        for rule in self._load_rules():
            # Prevent duplicate execution for same ticket+trigger in this request
            if rule.id in executed:
                continue

            # DB-level dedupe: avoid rerunning same rule repeatedly
            # We keep it simple: if a run exists in last few seconds, skip.
            # Replace with AuditEvent or Redis key if you want stronger dedupe.
            if AutomationRun.objects.filter(
                organization_id=self.organization_id,
                rule_id=rule.id,
                object_type="Ticket",
                object_id=str(obj.id),
            ).order_by("-ran_at").exists():
                # NOTE: if you want "run every time", remove this block.
                pass

            matched = False
            actions_executed: List[Dict[str, Any]] = []
            error = ""

            try:
                matched = eval_group(rule.conditions or {}, ctx)

                if matched:
                    actions_executed = self._execute_actions(obj, rule.actions or [])
            except Exception as e:
                error = str(e)

            # Write run record
            AutomationRun.objects.create(
                organization_id=self.organization_id,
                rule_id=rule.id,
                object_type="Ticket",
                object_id=str(obj.id),
                matched=matched,
                actions_executed=actions_executed,
                error=error,
            )

            executed.add(rule.id)
            setattr(obj, executed_key, executed)

            results.append(RuleRunResult(
                rule_id=rule.id,
                matched=matched,
                actions_executed=actions_executed,
                error=error,
            ))

        return results

    def _execute_actions(self, ticket, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []

        for action in actions:
            a_type = (action.get("type") or "").strip()
            value = action.get("value", None)

            fn = ACTION_REGISTRY.get(a_type)
            if not fn:
                out.append({"type": a_type, "ok": False, "detail": "Unknown action type"})
                continue

            try:
                # Normalize action call signatures
                if a_type in ("set_status", "set_visibility"):
                    res: ActionResult = fn(ticket, str(value))
                elif a_type in ("set_priority", "assign_team", "assign_user", "add_watcher"):
                    res = fn(ticket, int(value))
                elif a_type in ("add_tags", "remove_tags"):
                    res = fn(ticket, list(value or []))
                elif a_type in ("notify", "create_subtask"):
                    res = fn(ticket, dict(value or {}))
                elif a_type == "unassign":
                    res = fn(ticket)
                else:
                    # fallback
                    res = fn(ticket, value)

                out.append({"type": a_type, "ok": res.ok, "detail": res.detail, "changed": res.changed})
            except Exception as e:
                out.append({"type": a_type, "ok": False, "detail": f"Exception: {e}"})

        return out
