from datetime import timedelta

from ..domain.models import OHLCBar


def resample(bars, minutes, expected_components, component_minutes=1, audit=None):
    """Aggregate only complete, UTC-anchored component windows."""
    out = []
    group = []
    start = None
    previous = None
    for bar in bars:
        if bar.timestamp.tzinfo is None or bar.timestamp.utcoffset() != timedelta(0):
            raise ValueError("resampling requires UTC-aware timestamps")
        if previous is not None and bar.timestamp <= previous:
            raise ValueError("resampling requires strictly increasing timestamps")
        previous = bar.timestamp
        anchor = bar.timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
        bucket = anchor + timedelta(minutes=((bar.timestamp - anchor).total_seconds() // 60 // minutes) * minutes)
        if start is None:
            start = bucket
        if bucket != start:
            _append_complete_window(out, group, start, minutes, expected_components, component_minutes, audit)
            group = []
            start = bucket
        group.append(bar)
    if start is not None:
        _append_complete_window(out, group, start, minutes, expected_components, component_minutes, audit)
    return out


def _append_complete_window(out, group, start, minutes, expected_components, component_minutes, audit):
    expected = [start + timedelta(minutes=component_minutes * index) for index in range(expected_components)]
    if [bar.timestamp for bar in group] == expected:
        out.append(_agg(group, start, f"M{minutes}"))
    elif audit is not None:
        audit.append({"window_open": start.isoformat(), "reason": "missing_or_incomplete_component"})


def _require_timeframe(bars, expected_timeframe):
    if any(bar.timeframe != expected_timeframe for bar in bars):
        raise ValueError(f"{expected_timeframe} source bars are required")


def _agg(group, timestamp, timeframe):
    first = group[0]
    return OHLCBar(
        timestamp,
        first.open,
        max(bar.high for bar in group),
        min(bar.low for bar in group),
        group[-1].close,
        sum(bar.volume or 0 for bar in group) if any(bar.volume is not None for bar in group) else None,
        timeframe,
        first.provider,
        first.symbol,
        first.source_hash,
    )


def resample_m3(bars, audit=None):
    return resample(bars, 3, 3, component_minutes=1, audit=audit)


def resample_m45(bars, audit=None):
    """Construct production M45 exclusively from validated M15 bars."""
    _require_timeframe(bars, "M15")
    return resample(bars, 45, 3, component_minutes=15, audit=audit)


def resample_m45_from_m1_parity(bars, audit=None):
    """Optional M1-derived M45 parity series; never the production M45 path."""
    _require_timeframe(bars, "M1")
    return resample(bars, 45, 45, component_minutes=1, audit=audit)
