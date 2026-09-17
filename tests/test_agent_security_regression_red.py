from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_slice1_authority_regression_coverage_exists() -> None:
    target = ROOT / "tests/test_agent_security_authority.py"
    assert target.exists(), "missing target behavior: deterministic authority regression coverage"
