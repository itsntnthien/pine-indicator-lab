"""Sequential oracle for the interview contract. No orders, fills, or P/L."""
from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'references/workspace/TradingView/SMC-PRO-XAUUSD'))
from calibration.pivot.engine.features import true_ranges

FEEDS = {'OANDA:XAUUSD', 'FOREXCOM:NAS100', 'EXNESS:XAUUSD'}


@dataclass(frozen=True)
class Bar:
    time: int
    end: int
    open: float
    high: float
    low: float
    close: float

    def validate(self):
        if self.time >= self.end or not all(math.isfinite(x) and x > 0 for x in (self.open, self.high, self.low, self.close)):
            raise ValueError('Invalid timestamp or nonfinite/nonpositive OHLC')
        if self.high < max(self.open, self.close, self.low) or self.low > min(self.open, self.close, self.high):
            raise ValueError('Invalid OHLC envelope')


@dataclass
class Zone:
    id: str
    kind: str
    side: int
    lo: float
    hi: float
    anchor: int
    available: int
    born: int
    used: bool = False
    attempt: int | None = None
    extreme: float | None = None
    blocked: bool = False


@dataclass(frozen=True)
class Setup:
    id: str
    side: int
    confirmed_at: int
    confirm_index: int
    reference_close: float
    atr: float
    extreme: float
    stop: float
    target: float | None
    sources: tuple[str, ...]


@dataclass(frozen=True)
class OpenObservation:
    setup_id: str
    at: int
    price: float
    rr: float | None
    adverse: bool


def reward_risk(side, entry, stop, target):
    risk = side * (entry - stop)
    reward = side * (target - entry) if target is not None else None
    return reward / risk if risk > 0 and reward is not None and reward > 0 else None


class Series:
    def __init__(self):
        self.bars: list[Bar] = []
        self.ranges: list[float] = []
        self.atr: float | None = None

    def append(self, bar):
        bar.validate()
        if self.bars and bar.time < self.bars[-1].end:
            raise ValueError('Duplicate, overlapping, or unordered bars')
        self.bars.append(bar)
        tr = true_ranges(self.bars[-2:])[-1]
        self.ranges.append(tr)
        if len(self.ranges) == 14:
            self.atr = sum(self.ranges) / 14
        elif len(self.ranges) > 14:
            self.atr += (tr - self.atr) / 14
        return self.atr


class Context:
    """Call only with completed native HTF bars; availability is the bar close."""
    def __init__(self, feed, minutes, tick):
        if feed not in FEEDS or minutes not in (60, 240, 1440, 10080) or not math.isfinite(tick) or tick <= 0:
            raise ValueError('Unsupported feed/timeframe or tick')
        self.feed, self.minutes, self.tick = feed, minutes, tick
        self.series = Series()
        self.bias = 0
        self.high_pivot = self.low_pivot = None
        self.broken_high = self.broken_low = None
        self.zones: list[Zone] = []

    def add_zone(self, kind, side, lo, hi, anchor, available, born):
        if side not in (-1, 1) or not all(math.isfinite(x) for x in (lo, hi)) or lo > hi:
            raise ValueError('Invalid zone')
        ident = f'{self.feed}:{self.minutes}:{kind}:{side}:{anchor}:{available}'
        zone = Zone(ident, kind, side, lo, hi, anchor, available, born)
        self.zones.append(zone)
        if kind in ('BSL', 'SSL', 'SR'):
            matching = [z for z in self.zones if z.kind == kind and z.side == side]
            remove = {z.id for z in matching[:-3]}
            self.zones[:] = [z for z in self.zones if z.id not in remove]
        return zone

    def on_close(self, bar):
        previous_atr = self.series.atr
        atr = self.series.append(bar)
        bars = self.series.bars
        index = len(bars) - 1
        self.zones[:] = [z for z in self.zones if index - z.born < 100 and not (bar.close < z.lo if z.side == 1 else bar.close > z.hi)]
        up = self.high_pivot is not None and bar.close > self.high_pivot[1] and self.broken_high != self.high_pivot[0]
        down = self.low_pivot is not None and bar.close < self.low_pivot[1] and self.broken_low != self.low_pivot[0]
        break_side = 1 if up and not down else -1 if down and not up else 0
        if up and down:
            self.bias = 0
        elif break_side:
            self.bias = break_side
        if up:
            self.broken_high = self.high_pivot[0]
        if down:
            self.broken_low = self.low_pivot[0]
        if len(bars) >= 5:
            left2, left1, pivot, right1, right2 = bars[-5:]
            ph = pivot.high > max(left2.high, left1.high) and pivot.high >= max(right1.high, right2.high)
            pl = pivot.low < min(left2.low, left1.low) and pivot.low <= min(right1.low, right2.low)
            if ph:
                self.high_pivot = (pivot.time, pivot.high)
            if pl:
                self.low_pivot = (pivot.time, pivot.low)
            if atr is not None and atr > 0:
                for valid, level, side, kind in [(ph, pivot.high, -1, 'BSL'), (pl, pivot.low, 1, 'SSL')]:
                    if valid:
                        self.add_zone(kind, side, level, level, pivot.time, bar.end, index)
                        self.add_zone('SR', side, level - .2 * atr, level + .2 * atr, pivot.time, bar.end, index)
        if atr is None or atr <= 0:
            return
        if break_side:
            for origin in reversed(bars[max(0, index-10):index]):
                if (origin.close < origin.open if break_side == 1 else origin.close > origin.open):
                    self.add_zone('OB', break_side, origin.low, origin.high, bar.time, bar.end, index)
                    break
        if len(bars) >= 3:
            first = bars[-3]
            threshold = max(.1 * atr, self.tick)
            if bar.low - first.high >= threshold:
                self.add_zone('FVG', 1, first.high, bar.low, bar.time, bar.end, index)
            elif first.low - bar.high >= threshold:
                self.add_zone('FVG', -1, bar.high, first.low, bar.time, bar.end, index)
        if previous_atr is not None and previous_atr > 0 and abs(bar.close - bar.open) >= previous_atr:
            compact, lo, hi, selected = True, math.inf, -math.inf, None
            for k in range(1, min(3, index) + 1):
                source = bars[index-k]
                span = source.high - source.low
                compact = compact and span > 0 and abs(source.close - source.open) <= span * .5
                lo, hi = min(lo, source.low), max(hi, source.high)
                if compact and hi - lo <= previous_atr:
                    side = 1 if bar.close > hi and bar.close > bar.open else -1 if bar.close < lo and bar.close < bar.open else 0
                    if side:
                        selected = (side, lo, hi)
            if selected:
                self.add_zone('SD', *selected, bar.time, bar.end, index)


class EntryEngine:
    def __init__(self, context, minutes):
        if (context.minutes, minutes) not in ((60, 5), (240, 15)):
            raise ValueError('Observation-only timeframe; no entry engine')
        self.context, self.minutes = context, minutes
        self.series = Series()
        self.setups: list[Setup] = []
        self.observations: list[OpenObservation] = []

    def on_close(self, bar):
        ctx = self.context
        if ctx.series.bars and ctx.series.bars[-1].end > bar.time:
            raise ValueError('Future HTF data passed to LTF engine')
        atr = self.series.append(bar)
        i = len(self.series.bars) - 1
        if self.setups and self.setups[-1].confirm_index == i - 1:
            setup = self.setups[-1]
            adverse = setup.side * (bar.open - setup.stop) <= 0 or (setup.target is not None and setup.side * (setup.target - bar.open) <= 0)
            self.observations.append(OpenObservation(setup.id, bar.time, bar.open, reward_risk(setup.side, bar.open, setup.stop, setup.target), adverse))
        accepted = []
        for z in ctx.zones:
            if z.used or z.available > bar.time:
                continue
            contact = bar.high >= z.lo and bar.low <= z.hi
            if z.side != ctx.bias or atr is None or atr <= 0:
                z.attempt, z.extreme, z.blocked = None, None, contact
                continue
            if z.blocked and not contact:
                z.blocked = False
            if z.attempt is not None and i - z.attempt > 3:
                z.attempt, z.extreme, z.blocked = None, None, contact
            liquidity = z.kind in ('BSL', 'SSL')
            qualified = contact and (not liquidity or (bar.low <= z.lo - ctx.tick if z.side == 1 else bar.high >= z.hi + ctx.tick))
            if z.attempt is None and not z.blocked and qualified:
                z.attempt, z.extreme = i, bar.low if z.side == 1 else bar.high
            if z.attempt is not None:
                z.extreme = min(z.extreme, bar.low) if z.side == 1 else max(z.extreme, bar.high)
                reclaimed = (bar.close >= z.hi + ctx.tick if liquidity else bar.close > z.hi) if z.side == 1 else (bar.close <= z.lo - ctx.tick if liquidity else bar.close < z.lo)
                if reclaimed:
                    accepted.append(z)
        if not accepted:
            return None
        side = ctx.bias
        extreme = min(z.extreme for z in accepted) if side == 1 else max(z.extreme for z in accepted)
        unrounded = extreme - side * max(.1 * atr, ctx.tick)
        stop = (math.floor(unrounded / ctx.tick + 1e-9) if side == 1 else math.ceil(unrounded / ctx.tick - 1e-9)) * ctx.tick
        if side * (bar.close - stop) <= 0:
            return None
        targets = [z.lo if side == 1 else z.hi for z in ctx.zones if z.side == -side and z.available <= bar.time]
        targets = [p for p in targets if side * (p - bar.close) >= ctx.tick]
        target = (min(targets) if side == 1 else max(targets)) if targets else None
        setup = Setup(f'{ctx.feed}:{ctx.minutes}>{self.minutes}:{bar.end}:{side}', side, bar.end, i, bar.close, atr, extreme, stop, target, tuple(z.id for z in accepted))
        self.setups.append(setup)
        for z in accepted:
            z.used, z.attempt = True, None
        return setup


def replay(context, minutes, htf_bars, ltf_bars):
    """Consume native HTF closes only when available at the LTF bar open."""
    engine = EntryEngine(context, minutes)
    htf = iter(htf_bars)
    pending = next(htf, None)
    for bar in ltf_bars:
        while pending is not None and pending.end <= bar.time:
            context.on_close(pending)
            pending = next(htf, None)
        engine.on_close(bar)
    return engine


def visual_groups(zones):
    """Geometry only; never mutate any trading zone or its identity."""
    result = []
    for side in (-1, 1):
        for z in sorted((z for z in zones if z.side == side), key=lambda z: z.lo):
            if result and result[-1]['side'] == side and z.lo <= result[-1]['hi']:
                result[-1]['hi'] = max(result[-1]['hi'], z.hi)
                result[-1]['sources'].append(z.id)
            else:
                result.append({'side': side, 'lo': z.lo, 'hi': z.hi, 'sources': [z.id]})
    return result
