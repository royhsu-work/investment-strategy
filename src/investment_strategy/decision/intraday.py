from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from investment_strategy.domain.result import StrategyResult


@dataclass(frozen=True, slots=True)
class IntradaySnapshot:
    session_date: date
    open: Decimal
    latest_price: Decimal
    snapshot_at: datetime


@dataclass(frozen=True, slots=True)
class LevelRelationship:
    plan: str
    level: float
    latest: str
    open: str

    def to_dict(self) -> dict[str, object]:
        return {
            "plan": self.plan,
            "level": self.level,
            "latest": self.latest,
            "open": self.open,
        }


@dataclass(frozen=True, slots=True)
class IntradayOverlay:
    session_date: date
    open: Decimal
    latest_price: Decimal
    snapshot_at: datetime
    relationships: tuple[LevelRelationship, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "session_date": self.session_date.isoformat(),
            "open": float(self.open),
            "latest_price": float(self.latest_price),
            "snapshot_at": self.snapshot_at.isoformat(),
            "relationships": [item.to_dict() for item in self.relationships],
        }


def parse_snapshot(
    raw: Mapping[str, object] | None, *, expected_session: date
) -> IntradaySnapshot | None:
    if raw is None:
        return None
    try:
        session_raw = raw["session_date"]
        session = (
            session_raw
            if isinstance(session_raw, date)
            else date.fromisoformat(str(session_raw))
        )
        open_ = Decimal(str(raw["open"]))
        latest = Decimal(str(raw["latest_price"]))
        snapshot_raw = raw["snapshot_at"]
        snapshot_at = (
            snapshot_raw
            if isinstance(snapshot_raw, datetime)
            else datetime.fromisoformat(str(snapshot_raw).replace("Z", "+00:00"))
        )
    except (KeyError, ValueError, TypeError, InvalidOperation):
        return None
    if session != expected_session or open_ <= 0 or latest <= 0 or snapshot_at.tzinfo is None:
        return None
    return IntradaySnapshot(session, open_, latest, snapshot_at)


def _relation(price: Decimal, level: float) -> str:
    target = Decimal(str(level))
    if price <= target:
        return "AT_OR_BELOW_LEVEL"
    return "ABOVE_LEVEL"


def build_intraday_overlay(snapshot: IntradaySnapshot, result: StrategyResult) -> IntradayOverlay:
    relationships: list[LevelRelationship] = []
    for level in result.entry_plan.levels:
        relationships.append(
            LevelRelationship(
                plan="ENTRY",
                level=level,
                latest=_relation(snapshot.latest_price, level),
                open=_relation(snapshot.open, level),
            )
        )
    for level in result.exit_plan.dynamic_levels:
        relationships.append(
            LevelRelationship(
                plan="EXIT",
                level=level,
                latest=_relation(snapshot.latest_price, level),
                open=_relation(snapshot.open, level),
            )
        )
    return IntradayOverlay(
        session_date=snapshot.session_date,
        open=snapshot.open,
        latest_price=snapshot.latest_price,
        snapshot_at=snapshot.snapshot_at,
        relationships=tuple(relationships),
    )
