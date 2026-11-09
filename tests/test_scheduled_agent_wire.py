"""Independent golden bytes and consumer integration for canonical request wires."""

from __future__ import annotations

import base64
import json

import pytest

from investment_strategy.scheduled_agent_application_bridge import (
    ApplicationRequest,
    parse_application_request,
    render_application_request,
)
from investment_strategy.scheduled_agent_runtime import WorkerRequest
from investment_strategy.scheduled_agent_wire import (
    APPLICATION_CONTINUATION_WIRE,
    DISPATCH_REQUEST_WIRE,
    EFFECT_REQUEST_WIRE,
    MACHINE_EFFECT_REQUEST_WIRE,
)


def test_dispatch_producer_consumer_matches_independent_golden_fixture() -> None:
    from investment_strategy.issue_comment_bridge import (
        DispatchRequest,
        parse_dispatch_request,
        render_dispatch_request,
    )

    request = DispatchRequest(requested_at="2026-11-09T18:45:00+08:00")
    golden = "DISPATCH_REQUEST\nRequested-At: 2026-11-09T18:45:00+08:00"
    assert render_dispatch_request(request) == golden
    assert parse_dispatch_request(golden + "\n") == request
    assert DISPATCH_REQUEST_WIRE.parse(golden) == {"Requested-At": request.requested_at}


def test_effect_request_golden_and_unicode_producer_to_consumer() -> None:
    source = WorkerRequest(138, "lead", "resolve-question")
    worker = {
        "issue_number": 138,
        "role": "lead",
        "action": "resolve-question",
        "change": "canonical-wire",
        "result_kind": "blocked",
        "evidence_ref": "issuecomment-138-wire",
        "result_content": '測試 Unicode \\n literal, "quotes" and emoji ✅',
        "requested_effects": [],
    }
    raw = json.dumps(worker, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    encoded = base64.b64encode(raw.encode("utf-8")).decode("ascii")
    request = ApplicationRequest("a" * 40, raw)
    expected = f"EFFECT_REQUEST\nAuthorization-Revision: {'a' * 40}\nWorker-Result-B64: {encoded}"
    assert (
        render_application_request(request, source=source, authorized_change="canonical-wire")
        == expected
    )
    assert parse_application_request(expected + "\n") == request
    assert EFFECT_REQUEST_WIRE.parse(expected) == {
        "Authorization-Revision": "a" * 40,
        "Worker-Result-B64": encoded,
    }


@pytest.mark.parametrize(
    "body",
    [
        "DISPATCH_REQUEST\nRequested-At: 2026-11-09T18:45:00+08:00\n\n",
        "DISPATCH_REQUEST\r\nRequested-At: 2026-11-09T18:45:00+08:00",
        "DISPATCH_REQUEST\n Requested-At: 2026-11-09T18:45:00+08:00",
        "DISPATCH_REQUEST\nRequested-At: 2026-11-09T18:45:00+08:00 ",
        "DISPATCH_REQUEST\nRequested-At: ",
        "DISPATCH_REQUEST\nRequested-At: ok\nExtra: no",
        "DISPATCH_REQUEST",
        "UNKNOWN\nRequested-At: ok",
    ],
)
def test_golden_wire_rejects_extra_missing_whitespace_or_bad_framing(body: str) -> None:
    assert DISPATCH_REQUEST_WIRE.parse(body) is None


def test_shared_codec_rejects_extra_fields_for_effect_and_continuation() -> None:
    assert (
        MACHINE_EFFECT_REQUEST_WIRE.parse(
            "EFFECT_REQUEST\nAuthorization-Revision: " + "a" * 40 + "\nWorker-Result-B64: YQ=="
        )
        is None
    )
    with pytest.raises(ValueError, match="fields differ"):
        EFFECT_REQUEST_WIRE.render(
            {"Authorization-Revision": "a" * 40, "Worker-Result-B64": "YQ==", "extra": "x"}
        )
    assert (
        APPLICATION_CONTINUATION_WIRE.parse("APPLICATION_CONTINUATION\nIssue: 138\nUnknown: 1")
        is None
    )


def test_unicode_and_escaping_use_one_exact_serializer_and_parser() -> None:
    values = {"Requested-At": '中文✅\\path"quoted"'}
    wire = DISPATCH_REQUEST_WIRE.render(values)
    assert wire.encode("utf-8") == ('DISPATCH_REQUEST\nRequested-At: 中文✅\\path"quoted"'.encode())
    assert DISPATCH_REQUEST_WIRE.parse(wire + "\n") == values
