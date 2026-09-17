from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class FailureCategory(StrEnum):
    CONFIGURATION_FAILED = "CONFIGURATION_FAILED"
    DATA_FAILED = "DATA_FAILED"
    STRATEGY_FAILED = "STRATEGY_FAILED"


@dataclass(frozen=True, slots=True)
class Failure:
    category: FailureCategory
    code: str
    reason: str

    def to_dict(self) -> dict[str, str]:
        return {
            "category": self.category.value,
            "code": self.code,
            "reason": self.reason,
        }


class ApplicationFailure(Exception):
    def __init__(self, failure: Failure) -> None:
        super().__init__(failure.reason)
        self.failure = failure


class RequestRejected(ValueError):
    """Raised by a request boundary before application evaluation starts."""


def configuration_failure(code: str, reason: str) -> ApplicationFailure:
    return ApplicationFailure(Failure(FailureCategory.CONFIGURATION_FAILED, code, reason))


def data_failure(code: str, reason: str) -> ApplicationFailure:
    return ApplicationFailure(Failure(FailureCategory.DATA_FAILED, code, reason))


def strategy_failure(code: str, reason: str) -> ApplicationFailure:
    return ApplicationFailure(Failure(FailureCategory.STRATEGY_FAILED, code, reason))
