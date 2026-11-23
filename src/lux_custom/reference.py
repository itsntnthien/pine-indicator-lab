"""Causal observation oracle. Reuses existing OHLC validation and Wilder ATR, no entries."""
from dataclasses import dataclass
import math
from src.intraday.reference import Bar, Series


def pivots(bars, length):
    if len(bars) < length * 2 + 1:
        return None, None
    window = bars[-(length * 2 + 1):]
    center = window[length]
    ph = center.high > max(b.high for b in window[:length]) and center.high >= max(b.high for b in window[length+1:])
    pl = center.low < min(b.low for b in window[:length]) and center.low <= min(b.low for b in window[length+1:])
    return (center.time, center.high) if ph else None, (center.time, center.low) if pl else None


@dataclass
class Structure:
    high: tuple | None = None
    low: tuple | None = None
    high_broken: bool = False
    low_broken: bool = False
    bias: int = 0

    def advance(self, bar, ph, pl):
        up = self.high is not None and not self.high_broken and bar.close > self.high[1]
        down = self.low is not None and not self.low_broken and bar.close < self.low[1]
        side, kind, level, anchor = 0, 0, None, None
        if up and down:
            self.bias = 0
        elif up or down:
            side = 1 if up else -1
            kind = 1 if self.bias == 0 else 2 if self.bias == side else 3
            anchor, level = self.high if up else self.low
            self.bias = side
        if up:
            self.high_broken = True
        if down:
            self.low_broken = True
        if ph:
            self.high, self.high_broken = ph, False
        if pl:
            self.low, self.low_broken = pl, False
        return side, kind, level, anchor


@dataclass
class Pool:
    level: float
    side: int
    anchor: int
    born: int
    equal: bool = False


@dataclass
class Region:
    kind: str
    side: int
    low: float
    high: float
    anchor: int
    born: int
    available: int
    stage: int = 0

    def advance(self, bar, index):
        if index - self.born >= 200:
            return False, False
        if index <= self.available:
            return True, False
        invalid = bar.close < self.low if self.side == 1 else bar.close > self.high
        if invalid:
            if self.kind in ('FVG', 'OB'):
                self.kind = 'IFVG' if self.kind == 'FVG' else 'BRK'
                self.side *= -1
                self.available, self.stage = index, 0
                return True, True
            return False, False
        touched = bar.high >= self.low and bar.low <= self.high
        filled = bar.low <= self.low if self.side == 1 else bar.high >= self.high
        if touched:
            self.stage = 2 if filled else max(self.stage, 1)
        return True, False


def assessment(active, other, internal, swing, recent_sweep=0, available=True):
    if not available:
        return 'Khung HTF thấp hơn chart: không diễn giải'
    if active == 0:
        return 'Hướng HTF chưa xác lập'
    if other != 0 and active != other:
        return 'H1 và H4 đang trái hướng'
    if recent_sweep == 3:
        return 'Quét hai phía gần đây; bối cảnh nhiễu'
    if internal == active and swing == active:
        return 'Cấu trúc chart cùng hướng HTF đang dùng'
    if internal == -active:
        return 'Nhịp chart ngược HTF; hồi hay đảo chưa rõ'
    return 'Cấu trúc chart chưa đồng thuận đầy đủ'


class Observer:
    def __init__(self, tick):
        if not math.isfinite(tick) or tick <= 0:
            raise ValueError('Positive finite tick required')
        self.tick = tick
        self.series = Series()
        self.internal, self.swing = Structure(), Structure()
        self.pools, self.regions, self.observations = [], [], []
        self.last_sweep, self.last_sweep_index = 0, None

    def on_close(self, bar, context=None, other=None):
        for ctx in (context, other):
            if ctx and ctx.series.bars and ctx.series.bars[-1].end > bar.time:
                raise ValueError('HTF close not available at chart bar open')
        atr = self.series.append(bar)
        bars, index = self.series.bars, len(self.series.bars)-1
        iph, ipl = pivots(bars, 2)
        sph, spl = pivots(bars, 5)
        internal = self.internal.advance(bar, iph, ipl)
        swing = self.swing.advance(bar, sph, spl)
        sweep, equal, inversions = 0, 0, 0
        for pool in self.pools[:]:
            expired = index - pool.born >= 200
            crossed = bar.close < pool.level if pool.side == 1 else bar.close > pool.level
            swept = (bar.low <= pool.level - self.tick and bar.close >= pool.level + self.tick) if pool.side == 1 else (bar.high >= pool.level + self.tick and bar.close <= pool.level - self.tick)
            if not expired and swept:
                sweep |= 1 if pool.side == 1 else 2
            if expired or crossed or swept:
                self.pools.remove(pool)
        for pivot, side in ((sph, -1), (spl, 1)):
            if pivot:
                anchor, value = pivot
                matching = [p for p in self.pools if p.side == side and abs(p.level-value) <= max(self.tick, (atr or 0)*.05)]
                for pool in matching:
                    pool.equal = True
                self.pools.append(Pool(value, side, anchor, index, bool(matching)))
                if matching:
                    equal += 1 if side == 1 else 2
        self.pools = self.pools[-40:]
        for region in self.regions[:]:
            keep, inverted = region.advance(bar, index)
            inversions += int(inverted)
            if not keep:
                self.regions.remove(region)
        if atr is not None and atr > 0:
            if len(bars) >= 3:
                first, middle = bars[-3:-1]
                threshold = max(self.tick, .1*atr)
                if bar.low-first.high >= threshold and middle.close > first.high:
                    self.regions.append(Region('FVG', 1, first.high, bar.low, middle.time, index, index))
                if first.low-bar.high >= threshold and middle.close < first.low:
                    self.regions.append(Region('FVG', -1, bar.high, first.low, middle.time, index, index))
            if swing[0]:
                for origin in reversed(bars[max(0, index-10):index]):
                    opposite = origin.close < origin.open if swing[0] == 1 else origin.close > origin.open
                    if opposite:
                        if origin.high > origin.low:
                            self.regions.append(Region('OB', swing[0], origin.low, origin.high, origin.time, index, index))
                        break
        self.regions = self.regions[-64:]
        if sweep:
            self.last_sweep, self.last_sweep_index = sweep, index
        recent = self.last_sweep if self.last_sweep_index is not None and index-self.last_sweep_index <= 5 else 0
        active = context.bias if context else 0
        secondary = other.bias if other else 0
        result = {'index': index, 'confirmed_at': bar.end, 'internal_break': internal[0], 'internal_type': internal[1],
                  'swing_break': swing[0], 'swing_type': swing[1], 'sweep_mask': sweep, 'equal_mask': equal,
                  'inversions': inversions, 'region_count': len(self.regions), 'pool_count': len(self.pools),
                  'atr': atr, 'assessment': assessment(active, secondary, self.internal.bias, self.swing.bias, recent)}
        self.observations.append(result)
        return result
