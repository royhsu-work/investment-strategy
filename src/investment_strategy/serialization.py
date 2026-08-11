from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any


class ArtifactSerializationError(ValueError):
    """Raised when a public artifact cannot be represented as strict JSON."""


def serialize_public_artifact(artifact: Mapping[str, Any]) -> str:
    try:
        return json.dumps(
            artifact,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ArtifactSerializationError(
            "public artifact contains a non-JSON-compatible value"
        ) from exc
