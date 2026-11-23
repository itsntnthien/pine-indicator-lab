from __future__ import annotations

import math
from statistics import pstdev

from .types import Bar, FeatureValue, TradeDirection


def true_ranges(bars: list[Bar]) -> list[float]:
    values: list[float] = []
    for index, bar in enumerate(bars):
        previous_close = bars[index - 1].close if index else bar.close
        values.append(max(bar.high - bar.low, abs(bar.high - previous_close), abs(bar.low - previous_close)))
    return values


def causal_atr(bars: list[Bar], period: int) -> list[FeatureValue | None]:
    if period < 1:
        raise ValueError("ATR period must be positive")
    ranges = true_ranges(bars)
    output: list[FeatureValue | None] = [None] * len(bars)
    for index in range(period - 1, len(bars)):
        start = index - period + 1
        output[index] = FeatureValue(sum(ranges[start : index + 1]) / period, bars[index].timestamp, start, index)
    return output


def causal_volatility(bars: list[Bar], window: int) -> list[FeatureValue | None]:
    if window < 2:
        raise ValueError("volatility window must be at least two")
    returns = [0.0]
    for index in range(1, len(bars)):
        prior = bars[index - 1].close
        returns.append((bars[index].close - prior) / prior if prior else 0.0)
    output: list[FeatureValue | None] = [None] * len(bars)
    for index in range(window - 1, len(bars)):
        start = index - window + 1
        output[index] = FeatureValue(pstdev(returns[start : index + 1]), bars[index].timestamp, start, index)
    return output


def causal_displacement(bars: list[Bar], atr: list[FeatureValue | None], window: int) -> list[FeatureValue | None]:
    if window < 1:
        raise ValueError("displacement window must be positive")
    output: list[FeatureValue | None] = [None] * len(bars)
    for index in range(window - 1, len(bars)):
        if atr[index] is None or atr[index].value <= 0:
            continue
        start = index - window + 1
        body = abs(bars[index].close - bars[start].open)
        output[index] = FeatureValue(body / atr[index].value, bars[index].timestamp, start, index)
    return output


def confirmation_completion_index(start_index: int, required_bars: int) -> int:
    if required_bars < 1:
        raise ValueError("confirmation bars must be positive")
    return start_index + required_bars - 1


def retest_index(bars: list[Bar], start_index: int, window: int, direction: TradeDirection, reference_price: float) -> int | None:
    end = min(len(bars), start_index + window)
    for index in range(start_index, end):
        touched = bars[index].low <= reference_price if direction == TradeDirection.LONG else bars[index].high >= reference_price
        if touched:
            return index
    return None


def warmup_eligible(index: int, *windows: int) -> bool:
    return index >= max(windows) - 1


def validate_feature_causality(values: list[FeatureValue | None], bars: list[Bar]) -> None:
    for index, value in enumerate(values):
        if value is None:
            continue
        if value.source_end_index != index or value.source_start_index < 0:
            raise ValueError("non-causal feature source interval")
        if value.as_of_timestamp != bars[index].timestamp:
            raise ValueError("feature as-of timestamp mismatch")
        if not math.isfinite(value.value):
            raise ValueError("non-finite feature value")
