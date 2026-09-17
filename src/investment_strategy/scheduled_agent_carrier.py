"""Bounded immutable plans for identity-sensitive external GitHub carriers."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class CarrierPlan:
    """Exact application-authorized mutation plan for one replaceable carrier."""

    plan_id: str
    correlation: str
    repository: str
    issue_number: int
    change: str
    action: str
    authorization_revision: str
    operation: str
    target: Mapping[str, object]
    expected: Mapping[str, object]
    requested: Mapping[str, object]
    force: bool
    expected_postcondition: Mapping[str, object]


class CarrierRequired(RuntimeError):
    """The application authorized a mutation but an external carrier must execute it."""

    def __init__(self, plan: CarrierPlan) -> None:
        super().__init__(f"carrier required: {plan.plan_id}")
        self.plan = plan


def make_carrier_plan(
    *,
    repository: str,
    issue_number: int,
    change: str,
    action: str,
    authorization_revision: str,
    operation: str,
    target: Mapping[str, object],
    expected: Mapping[str, object],
    requested: Mapping[str, object],
    expected_postcondition: Mapping[str, object],
) -> CarrierPlan:
    """Construct a content-addressed plan with no carrier or successor authority."""

    if len(authorization_revision) != 40 or any(
        character not in "0123456789abcdef" for character in authorization_revision
    ):
        raise ValueError("carrier plan authorization revision is invalid")
    material = {
        "repository": repository,
        "issue_number": issue_number,
        "change": change,
        "action": action,
        "authorization_revision": authorization_revision,
        "operation": operation,
        "target": dict(target),
        "expected": dict(expected),
        "requested": dict(requested),
        "force": False,
        "expected_postcondition": dict(expected_postcondition),
    }
    encoded = json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    plan_id = f"carrier-plan-{hashlib.sha256(encoded).hexdigest()}"
    return CarrierPlan(
        plan_id=plan_id,
        correlation=f"{plan_id}:effect-request-{issue_number}",
        repository=repository,
        issue_number=issue_number,
        change=change,
        action=action,
        authorization_revision=authorization_revision,
        operation=operation,
        target=dict(target),
        expected=dict(expected),
        requested=dict(requested),
        force=False,
        expected_postcondition=dict(expected_postcondition),
    )


def carrier_plan_document(plan: CarrierPlan) -> dict[str, object]:
    """Return the serialized plan surface used by workflow artifacts and carriers."""

    return {
        "plan_id": plan.plan_id,
        "correlation": plan.correlation,
        "repository": plan.repository,
        "issue_number": plan.issue_number,
        "change": plan.change,
        "action": plan.action,
        "authorization_revision": plan.authorization_revision,
        "operation": plan.operation,
        "target": dict(plan.target),
        "expected": dict(plan.expected),
        "requested": dict(plan.requested),
        "force": plan.force,
        "expected_postcondition": dict(plan.expected_postcondition),
    }


def carrier_pr_identity(payload: Mapping[str, object]) -> dict[str, object]:
    """Capture only the immutable PR/ref identity relevant to a carrier plan."""

    head = payload.get("head")
    base = payload.get("base")
    head_mapping = head if isinstance(head, Mapping) else {}
    base_mapping = base if isinstance(base, Mapping) else {}
    head_repo = head_mapping.get("repo")
    base_repo = base_mapping.get("repo")
    head_repo_mapping = head_repo if isinstance(head_repo, Mapping) else {}
    base_repo_mapping = base_repo if isinstance(base_repo, Mapping) else {}
    return {
        "number": payload.get("number"),
        "state": payload.get("state"),
        "merged": payload.get("merged"),
        "draft": payload.get("draft"),
        "title": payload.get("title"),
        "body": payload.get("body"),
        "head": {
            "ref": head_mapping.get("ref"),
            "sha": head_mapping.get("sha"),
            "repo": head_repo_mapping.get("full_name"),
        },
        "base": {
            "ref": base_mapping.get("ref"),
            "sha": base_mapping.get("sha"),
            "repo": base_repo_mapping.get("full_name"),
        },
    }


__all__ = [
    "CarrierPlan",
    "CarrierRequired",
    "carrier_plan_document",
    "carrier_pr_identity",
    "make_carrier_plan",
]
