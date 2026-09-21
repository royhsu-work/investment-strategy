"""Mechanical coverage for the executable consequence topology."""

from investment_strategy.scheduled_agent_action_model import TRANSITIONS
from investment_strategy.scheduled_agent_effect_contract import (
    consequence_spec_for,
    legal_transition_keys,
)


def test_every_legal_transition_has_exactly_one_consequence_spec() -> None:
    expected = {(action, result) for action, results in TRANSITIONS.items() for result in results}
    assert legal_transition_keys() == expected
    assert {
        (consequence_spec_for(action, result).action, consequence_spec_for(action, result).result)
        for action, result in expected
    } == expected
