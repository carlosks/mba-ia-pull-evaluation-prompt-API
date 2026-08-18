from datetime import datetime, timedelta, timezone

from app.routes.projects import _isoformat_utc
from app.services.project_builder_service import utc_now_iso


def test_isoformat_utc_returns_empty_string_for_none():
    assert _isoformat_utc(None) == ""


def test_isoformat_utc_treats_naive_datetime_as_utc():
    value = datetime(2026, 8, 18, 19, 0, 0)

    assert _isoformat_utc(value) == "2026-08-18T19:00:00Z"


def test_isoformat_utc_converts_timezone_aware_datetime_to_utc():
    brasilia_time = datetime(
        2026,
        8,
        18,
        16,
        0,
        0,
        tzinfo=timezone(timedelta(hours=-3)),
    )

    assert _isoformat_utc(brasilia_time) == "2026-08-18T19:00:00Z"


def test_utc_now_iso_returns_explicit_utc_timestamp():
    value = utc_now_iso()

    assert value.endswith("Z")

    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))

    assert parsed.tzinfo is not None
    assert parsed.utcoffset() == timedelta(0)
