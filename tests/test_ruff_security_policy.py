from __future__ import annotations

import tomllib
from pathlib import Path


def test_ruff_security_policy_is_enabled_and_test_asserts_are_scoped() -> None:
    config = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    lint = config["tool"]["ruff"]["lint"]

    assert "S" in lint["select"]
    assert lint["per-file-ignores"] == {"tests/**": ["S101"]}
