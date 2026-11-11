"""One-time, read-only qualification of the historical T1 native artifacts."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

from investment_strategy.scheduled_agent_dispatch_result import (
    DispatchArtifactReadError,
    fetch_dispatch_artifact,
)

_REPOSITORY = "royhsu-work/investment-strategy"
_REVISION = "8bf5007c4dc6fb8368473af3aba86dbe5136a627"


@dataclass(frozen=True, slots=True)
class Source:
    request_comment_id: int
    run_id: int
    run_attempt: int
    artifact_id: int
    size_in_bytes: int
    sha256: str


_SOURCES = (
    Source(
        request_comment_id=6757650907,
        run_id=42746001986,
        run_attempt=1,
        artifact_id=13731193002,
        size_in_bytes=199,
        sha256="6cf122171ef4a82d09ed3f34e50fe65bb39a04c179beef6afce8dcc1cd6a14cd",
    ),
    Source(
        request_comment_id=6758397830,
        run_id=42751607415,
        run_attempt=1,
        artifact_id=13733163299,
        size_in_bytes=199,
        sha256="7a9da20934c78dd4f03d62432a37901ea853e53d4e88f7f3ba0f3b84e6015625",
    ),
)


def _emit(document: dict[str, object]) -> None:
    print(json.dumps(document, sort_keys=True, separators=(",", ":")))


def main() -> int:
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    token = os.environ.get("GITHUB_TOKEN", "")
    if repository != _REPOSITORY or not token:
        _emit(
            {
                "stage": "diagnostic-precondition",
                "classification": "PERMANENT_INVALID",
                "repository_match": repository == _REPOSITORY,
                "token_present": bool(token),
                "mutation_attempted": False,
            }
        )
        return 0

    for source in _SOURCES:
        try:
            verified = fetch_dispatch_artifact(
                repository,
                token,
                request_comment_id=source.request_comment_id,
                run_id=source.run_id,
                current_revision=_REVISION,
                expected_run_attempt=source.run_attempt,
                expected_artifact_id=source.artifact_id,
                expected_artifact_sha256=source.sha256,
            )
        except DispatchArtifactReadError as error:
            _emit(error.diagnostic())
            continue

        diagnostic = verified.diagnostic(run_id=source.run_id)
        if (
            verified.run_attempt != source.run_attempt
            or verified.artifact_id != source.artifact_id
            or verified.artifact_size_in_bytes != source.size_in_bytes
            or verified.content_length != source.size_in_bytes
            or verified.artifact_sha256 != source.sha256
            or verified.content_sha256 != source.sha256
        ):
            diagnostic["stage"] = "diagnostic-expectation"
            diagnostic["classification"] = "IDENTITY_STALE"
            diagnostic["mutation_attempted"] = False
        _emit(diagnostic)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
