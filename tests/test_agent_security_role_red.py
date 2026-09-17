from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_slice2_role_and_human_authority_regression_coverage_exists() -> None:
    target = ROOT / "tests/test_agent_security_role_boundaries.py"
    assert target.exists(), "missing target behavior: role and Human authority regression coverage"
