"""Single byte-level contract for line-framed Scheduled Agent requests.

The GitHub issue_comment trigger only selects a marker. This codec owns
producer and consumer field order, delimiters, newline framing, and escaping;
repository authorization remains a separate application responsibility.
"""

from __future__ import annotations

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
