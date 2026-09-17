from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_slice3_s603_suppression_safety_regression_coverage_exists() -> None:
    target = ROOT / "tests/test_s603_suppression_safety.py"
    assert target.exists(), "missing target behavior: S603 suppression safety regression coverage"
