from investment_strategy.native_closing_preflight import has_native_closing_reference


def test_reproduces_140_155_commit_message_bypass() -> None:
    assert has_native_closing_reference(
        "Resolve #159 OpenSpec review findings in proposal",
        repository_full_name="royhsu-work/investment-strategy",
        coordination_issue=159,
    )


def test_accepts_non_closing_reference() -> None:
    assert not has_native_closing_reference(
        "Refs #159",
        repository_full_name="royhsu-work/investment-strategy",
        coordination_issue=159,
    )


def test_matches_keyword_case_and_punctuation() -> None:
    assert has_native_closing_reference(
        "FIXES: #159",
        repository_full_name="royhsu-work/investment-strategy",
        coordination_issue=159,
    )


def test_ignores_unrelated_issue() -> None:
    assert not has_native_closing_reference(
        "Resolves #158",
        repository_full_name="royhsu-work/investment-strategy",
        coordination_issue=159,
    )


def test_ignores_fenced_code_example() -> None:
    assert not has_native_closing_reference(
        "Example only:\n```text\nResolve #159\n```",
        repository_full_name="royhsu-work/investment-strategy",
        coordination_issue=159,
    )
