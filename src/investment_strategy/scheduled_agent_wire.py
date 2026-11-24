"""Single byte-level contract for line-framed Scheduled Agent requests.

The GitHub issue_comment trigger only selects a marker. This codec owns
producer and consumer field order, delimiters, newline framing, and escaping;
repository authorization remains a separate application responsibility.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import re
from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LineWireContract:
    marker: str
    fields: tuple[str, ...]

    def render(self, values: Mapping[str, str]) -> str:
        if set(values) != set(self.fields):
            raise ValueError(f"{self.marker} fields differ from canonical contract")
        lines = [self.marker]
        for field in self.fields:
            value = values[field]
            if (
                not isinstance(value, str)
                or not value
                or value != value.strip()
                or "\n" in value
                or "\r" in value
                or "\x00" in value
            ):
                raise ValueError(f"{self.marker} field {field} is not canonical")
            lines.append(f"{field}: {value}")
        return "\n".join(lines)

    def parse(self, body: str) -> dict[str, str] | None:
        if not isinstance(body, str):
            return None
        # Exactly one terminal LF is allowed as transport framing. It is not
        # a field. Extra blank lines, CRLF, or embedded CR fail closed.
        canonical_body = body[:-1] if body.endswith("\n") else body
        if "\r" in canonical_body:
            return None
        lines = canonical_body.split("\n")
        if len(lines) != len(self.fields) + 1 or lines[0] != self.marker:
            return None
        values: dict[str, str] = {}
        for field, line in zip(self.fields, lines[1:], strict=True):
            prefix = f"{field}: "
            if not line.startswith(prefix):
                return None
            values[field] = line[len(prefix) :]
        try:
            if self.render(values) != canonical_body:
                return None
        except ValueError:
            return None
        return values


EFFECT_REQUEST_WIRE = LineWireContract(
    "EFFECT_REQUEST", ("Authorization-Revision", "Worker-Result-B64")
)
MACHINE_EFFECT_REQUEST_WIRE = LineWireContract(
    "EFFECT_REQUEST",
    ("Authorization-Revision", "Dispatch-Correlation", "Worker-Result-B64"),
)
APPLICATION_CONTINUATION_WIRE = LineWireContract(
    "APPLICATION_CONTINUATION",
    (
        "Issue",
        "Original-Request-Comment",
        "Accepted-Decision-SHA256",
        "Predecessor-Run-ID",
        "Predecessor-Run-Attempt",
        "Predecessor-Job-ID",
        "Predecessor-Artifact-ID",
        "Predecessor-Artifact-Digest",
        "Failure-Evidence-SHA256",
        "Recovery-Episode-SHA256",
        "Continuation-Correlation",
    ),
)
DISPATCH_REQUEST_WIRE = LineWireContract("DISPATCH_REQUEST", ("Requested-At",))
# A direct-Human request for a NON-WRITING maintenance intake. This is
# neither an EFFECT_REQUEST nor a repository-dispatched Action/Result.
RUNTIME_REPAIR_REQUEST_WIRE = LineWireContract(
    "RUNTIME_REPAIR_REQUEST",
    (
        "Issue",
        "Change",
        "Action",
        "Accepted-Request-Comment",
        "Accepted-Decision-SHA256",
        "Repair-PR",
        "Repair-HEAD",
    ),
)


APPLICATION_DECISION_MARKER = "APPLICATION_DECISION"
APPLICATION_DECISION_DISPOSITIONS = frozenset({"ACCEPTED", "REJECTED"})
APPLICATION_DECISION_WIRE = LineWireContract(
    APPLICATION_DECISION_MARKER,
    (
        "Request-Comment",
        "Request-Body-SHA256",
        "Authorization-Revision",
        "Issue",
        "Role",
        "Action",
        "Change",
        "Result-Kind",
        "Disposition",
        "Worker-Result-SHA256",
        "Application-Intent-B64",
        "Reason",
    ),
)
_APPLICATION_DECISION_FIELDS = APPLICATION_DECISION_WIRE.fields


@dataclass(frozen=True)
class ApplicationDecisionRecord:
    """Immutable application acceptance/rejection evidence for one exact request."""

    request_comment_id: int
    request_body_sha256: str
    authorization_revision: str
    issue_number: int
    role: str
    action: str
    change: str
    result_kind: str
    disposition: str
    worker_result_sha256: str
    raw_worker_result: str
    reason: str


def parse_application_decision(body: object) -> ApplicationDecisionRecord | None:
    """Parse and verify one application decision comment."""

    if not isinstance(body, str):
        return None
    # Historical decision comments were parsed with splitlines(); retain that
    # compatibility while sourcing field order from the same producer schema.
    lines = body.splitlines()
    if (
        len(lines) != len(_APPLICATION_DECISION_FIELDS) + 1
        or lines[0] != APPLICATION_DECISION_MARKER
    ):
        return None
    values: dict[str, str] = {}
    for line in lines[1:]:
        key, separator, value = line.partition(": ")
        if not separator or key in values or key not in _APPLICATION_DECISION_FIELDS:
            return None
        if not value or value != value.strip():
            return None
        values[key] = value
    if tuple(values) != _APPLICATION_DECISION_FIELDS:
        return None
    try:
        request_comment_id = int(values["Request-Comment"])
        issue_number = int(values["Issue"])
    except ValueError:
        return None
    encoded = values["Application-Intent-B64"]
    try:
        raw_worker_result = base64.b64decode(encoded.encode("ascii"), validate=True).decode("utf-8")
    except (UnicodeDecodeError, ValueError, binascii.Error):
        return None
    if (
        request_comment_id <= 0
        or issue_number <= 0
        or not re.fullmatch(r"[0-9a-f]{64}", values["Request-Body-SHA256"])
        or not re.fullmatch(r"[0-9a-f]{40}", values["Authorization-Revision"])
        or values["Disposition"] not in APPLICATION_DECISION_DISPOSITIONS
        or not values["Role"]
        or not values["Action"]
        or not values["Change"]
        or not values["Result-Kind"]
        or not re.fullmatch(r"[0-9a-f]{64}", values["Worker-Result-SHA256"])
        or hashlib.sha256(raw_worker_result.encode("utf-8")).hexdigest()
        != values["Worker-Result-SHA256"]
    ):
        return None
    return ApplicationDecisionRecord(
        request_comment_id=request_comment_id,
        request_body_sha256=values["Request-Body-SHA256"],
        authorization_revision=values["Authorization-Revision"],
        issue_number=issue_number,
        role=values["Role"],
        action=values["Action"],
        change=values["Change"],
        result_kind=values["Result-Kind"],
        disposition=values["Disposition"],
        worker_result_sha256=values["Worker-Result-SHA256"],
        raw_worker_result=raw_worker_result,
        reason=values["Reason"],
    )
