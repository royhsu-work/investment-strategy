from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from investment_strategy.decision import DecisionRequest, DecisionService

from .helpers import (
    FixedClock,
    SnapshotGateway,
    SpyGateway,
    TestStrategy,
    WeekdayCalendar,
    bars,
    make_resolver,
)


def current_service(
    snapshot: Mapping[str, object] | None,
) -> tuple[DecisionService, TestStrategy, SnapshotGateway]:
    strategy = TestStrategy(minimum_history=1)
    market = SpyGateway(bars(date(2026, 8, 7), 2))
    snapshots = SnapshotGateway(snapshot)
    service = DecisionService(
        resolver=make_resolver(strategy),
        market_data=market,
        calendar=WeekdayCalendar(session_complete=False),
        clock=FixedClock(datetime(2026, 8, 11, 10, tzinfo=UTC)),
        intraday=snapshots,
    )
    return service, strategy, snapshots


def valid_snapshot() -> dict[str, object]:
    return {
        "session_date": "2026-08-11",
        "open": 9.5,
        "latest_price": 11.0,
        "snapshot_at": "2026-08-11T02:00:00+00:00",
    }


def test_current_formal_decision_can_include_separate_overlay() -> None:
    service, strategy, _ = current_service(valid_snapshot())
    artifact = service.run(DecisionRequest("00733"))
    assert artifact["status"] == "SUCCESS"
    assert artifact["resolved_as_of"] == "2026-08-10"
    overlay = artifact["intraday_overlay"]
    assert overlay["session_date"] == "2026-08-11"
    assert overlay["open"] == 9.5
    assert overlay["latest_price"] == 11.0
    assert strategy.last_context is not None
    assert strategy.last_context.as_of == date(2026, 8, 10)
    assert strategy.last_context.market_data[-1].trading_timestamp == date(2026, 8, 10)


def test_historical_decision_never_attaches_current_overlay() -> None:
    service, _, snapshots = current_service(valid_snapshot())
    artifact = service.run(DecisionRequest("00733", date(2026, 8, 7)))
    assert artifact["status"] == "SUCCESS"
    assert "intraday_overlay" not in artifact
    assert snapshots.calls == 0


def test_snapshot_cannot_change_formal_strategy_result() -> None:
    service_with, _, _ = current_service(valid_snapshot())
    service_without, _, _ = current_service(None)
    with_overlay = service_with.run(DecisionRequest("00733"))
    without_overlay = service_without.run(DecisionRequest("00733"))
    assert with_overlay["strategy_result"] == without_overlay["strategy_result"]


def test_overlay_uses_only_deterministic_relationships_and_never_near_or_touch_history() -> None:
    service, _, _ = current_service(valid_snapshot())
    artifact = service.run(DecisionRequest("00733"))
    overlay_text = str(artifact["intraday_overlay"])
    assert "AT_OR_BELOW_LEVEL" in overlay_text
    assert "ABOVE_LEVEL" in overlay_text
    assert "NEAR" not in overlay_text
    assert "TOUCHED" not in overlay_text
    assert "FILL" not in overlay_text


def test_intraday_snapshot_session_eligibility_uses_market_timezone() -> None:
    strategy = TestStrategy(minimum_history=1)
    snapshots = SnapshotGateway(valid_snapshot())
    service = DecisionService(
        resolver=make_resolver(strategy),
        market_data=SpyGateway(bars(date(2026, 8, 10), 1)),
        calendar=WeekdayCalendar(
            session_complete=False,
            market_timezone=ZoneInfo("Asia/Taipei"),
        ),
        clock=FixedClock(datetime(2026, 8, 10, 16, 30, tzinfo=UTC)),
        intraday=snapshots,
    )
    artifact = service.run(DecisionRequest("00733"))
    assert artifact["status"] == "SUCCESS"
    assert artifact["resolved_as_of"] == "2026-08-10"
    assert artifact["intraday_overlay"]["session_date"] == "2026-08-11"
    assert snapshots.calls == 1


def test_invalid_or_unavailable_snapshot_is_non_fatal() -> None:
    invalid = valid_snapshot()
    invalid["latest_price"] = 0
    for snapshot in (None, invalid):
        service, _, _ = current_service(snapshot)
        artifact = service.run(DecisionRequest("00733"))
        assert artifact["status"] == "SUCCESS"
        assert "intraday_overlay" not in artifact
