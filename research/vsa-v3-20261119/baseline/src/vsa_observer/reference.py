"""Causal VSA Observer v2. Prices/volume from one provider; no execution or P/L."""
from collections import deque
from dataclasses import dataclass, asdict
import math

VERSION = 'vsa-observer-2.0'
HTF = {'1': ('5', '15'), '3': ('15', '60'), '5': ('15', '60'),
       '15': ('60', '240'), '30': ('60', '240'), '60': ('240', 'D'), '240': ('D', 'W')}
PHASES = ['Chưa ghi nhận quét', 'Đã quét · chờ cấu trúc', 'Cấu trúc xác nhận',
          'Điều kiện hội tụ', 'Quét hai phía · chờ', 'Đã vô hiệu', 'Quét đã hết hạn']
REASONS = {1: 'Thiếu volume / ATR / warmup', 2: 'Chưa ghi nhận quét', 4: 'Quét quá 10 nến',
           8: 'Đóng vượt cực trị quét', 16: 'Quét hai phía còn hiệu lực',
           32: 'Chờ cấu trúc sau quét', 64: 'HTF chưa cùng hướng hoặc chưa đủ dữ liệu',
           128: 'VSA nến chốt chưa ủng hộ', 256: 'Giá xa EMA hơn 2,5 ATR'}


@dataclass(frozen=True)
class Candle:
    time: int
    end: int
    open: float
    high: float
    low: float
    close: float
    volume: float | None = None

    def validate(self):
        if self.time >= self.end or not all(math.isfinite(v) and v > 0 for v in (self.open, self.high, self.low, self.close)):
            raise ValueError('Invalid candle time/price')
        if self.low > min(self.open, self.close) or self.high < max(self.open, self.close) or self.low > self.high:
            raise ValueError('Invalid OHLC envelope')
        if self.volume is not None and (not math.isfinite(self.volume) or self.volume < 0):
            raise ValueError('Invalid volume')


@dataclass
class Sweep:
    bar: int | None = None
    stamp: int | None = None
    level: float | None = None
    extreme: float | None = None
    invalid: bool = False

    def update(self, side, level, extreme, index, stamp, close):
        if level is not None:
            self.bar, self.stamp, self.level, self.extreme, self.invalid = index, stamp, level, extreme, False
        elif self.bar is not None:
            self.invalid |= close < self.extreme if side == 1 else close > self.extreme

    def age(self, index):
        return -1 if self.bar is None else index - self.bar


@dataclass
class Zone:
    kind: str
    side: int
    id: int
    born: int
    anchor: int
    low: float
    high: float
    touched: bool = False
    terminal: bool = False


def phase(mask):
    return 5 if mask & 8 else 6 if mask & 4 else 0 if mask & 2 else 4 if mask & 16 else 1 if mask & 32 else 3 if mask == 0 else 2


def setup_mask(age, invalid, opposite, structure, htf, vsa, extended, ready):
    return ((0 if ready else 1) | (2 if age < 0 else 0) | (4 if age > 10 else 0) |
            (8 if invalid else 0) | (16 if opposite else 0) | (0 if structure else 32) |
            (0 if htf else 64) | (0 if vsa else 128) | (256 if extended else 0))


def classify(valid, rv, rr, location, delta, below_both):
    if not valid: return 99
    if rv >= 1.5 and rr >= 1.2 and delta > 0 and location >= .7: return 1
    if rv >= 1.5 and rr >= 1.2 and delta < 0 and location <= .3: return -1
    if rv >= 1.5 and rr <= .8 and location >= .65: return 2
    if rv >= 1.5 and rr <= .8 and location <= .35: return -2
    if rv <= .7 and rr <= .8 and below_both and delta < 0 and location >= .5: return 3
    if rv <= .7 and rr <= .8 and below_both and delta > 0 and location <= .5: return -3
    return 0


def direction(bar):
    return 0 if bar is None else (bar.close > bar.open) - (bar.close < bar.open)


def closed_context(bars, at):
    """The caller supplies native close timestamps, never guessed next-bar openings."""
    return max((b for b in bars if b.end <= at), key=lambda b: b.end, default=None)


class Observer:
    def __init__(self, tick, timeframe='5', ema_length=200):
        if not math.isfinite(tick) or tick <= 0 or not 50 <= ema_length <= 500:
            raise ValueError('Invalid tick/EMA period')
        self.tick, self.timeframe, self.ema_length = tick, timeframe, ema_length
        self.history = deque(maxlen=21)
        self.tr_seed = []
        self.ema_seed = []
        self.ema = self.atr = self.internal_atr = None
        self.fast = self.slow = None
        self.index = self.sequence = self.trend = 0
        self.high_swing = self.low_swing = None
        self.high_consumed = self.low_consumed = False
        self.structure = None
        self.pools, self.fvgs, self.obs = [], [], []
        self.low_sweep, self.high_sweep = Sweep(), Sweep()
        self.snapshot = None
        self.events = deque(maxlen=120)

    def ticks(self, value):
        return math.floor(value / self.tick + .5)

    def price(self, value):
        return self.ticks(value) * self.tick

    def add_zone(self, kind, side, bar, lo, hi):
        self.sequence += 1
        z = Zone(kind, side, self.sequence, self.index, bar.time, self.price(lo), self.price(hi))
        {'POOL': self.pools, 'FVG': self.fvgs, 'OB': self.obs}[kind].append(z)
        return z

    def zone_context(self, side, price):
        zones = [z for z in self.fvgs + self.obs if z.side == side and not z.terminal]
        distance = lambda z: max(z.low - price, price - z.high, 0)
        z = min(zones, key=lambda z: (distance(z), -z.id), default=None)
        if z is None or self.atr is None or self.atr <= 0:
            return {'code': 0, 'text': 'Chưa có vùng', 'zone': asdict(z) if z else None, 'distanceAtr': None}
        d = distance(z)
        code = 1 if d == 0 else 2 if d <= .5 * self.atr else 3
        text = {1: 'Trong ', 2: 'Gần ', 3: 'Xa '}[code] + z.kind + (' · đã chạm' if z.touched else ' · chưa chạm')
        return {'code': code, 'text': text, 'zone': asdict(z), 'distanceAtr': d / self.atr}

    def on_close(self, bar, contexts=(None, None)):
        bar.validate()
        if self.history and bar.time < self.history[-1].end:
            raise ValueError('Duplicate/unordered candle; rebuild on source revision')
        for ctx in contexts:
            if ctx is not None:
                ctx.validate()
                if ctx.end > bar.end: raise ValueError('Future HTF supplied')
        prev = self.history[-1] if self.history else None
        self.index += 1
        alpha = 2 / (self.ema_length + 1)
        # Native Pine ta.ema seeds with SMA(length), verified with the synthetic chart harness.
        if self.ema is None:
            self.ema_seed.append(bar.close)
            if len(self.ema_seed) == self.ema_length: self.ema = sum(self.ema_seed)/self.ema_length
        else:
            self.ema = alpha * bar.close + (1-alpha) * self.ema
        self.fast = bar.close if self.fast is None else self.fast + 2/9 * (bar.close-self.fast)
        self.slow = bar.close if self.slow is None else self.slow + 2/22 * (bar.close-self.slow)
        tr = bar.high-bar.low if prev is None else max(bar.high-bar.low, abs(bar.high-prev.close), abs(bar.low-prev.close))
        self.internal_atr = tr if self.internal_atr is None else self.internal_atr + (tr-self.internal_atr)/14
        if self.atr is None:
            self.tr_seed.append(tr)
            if len(self.tr_seed) == 14: self.atr = sum(self.tr_seed)/14
        else:
            self.atr = (13*self.atr + tr)/14
        prior = list(self.history)[-20:]
        valid = len(prior) == 20 and all(b.volume is not None and b.volume > 0 for b in prior+[bar]) and bar.high > bar.low
        mean_range = sum(b.high-b.low for b in prior)/20 if len(prior) == 20 else 0
        valid &= mean_range > 0
        rv = bar.volume/(sum(b.volume for b in prior)/20) if valid else None
        rr = (bar.high-bar.low)/mean_range if valid else None
        loc = (bar.close-bar.low)/(bar.high-bar.low) if valid else None
        below = valid and bar.volume < prior[-1].volume and bar.volume < prior[-2].volume
        vsa = classify(valid, rv, rr, loc, bar.close-prev.close if prev else 0, below)
        old_high, old_low = self.high_swing, self.low_swing
        new_high = new_low = False
        window = list(self.history)+[bar]
        if len(window) >= 11:
            w = window[-11:]; p = w[5]
            ph, pl = self.ticks(p.high), self.ticks(p.low)
            new_high = all(ph >= self.ticks(b.high) for b in w[:5]) and all(ph > self.ticks(b.high) for b in w[6:])
            new_low = all(pl <= self.ticks(b.low) for b in w[:5]) and all(pl < self.ticks(b.low) for b in w[6:])
            if new_high: self.high_swing = (ph, p.time, bar.time)
            if new_low: self.low_swing = (pl, p.time, bar.time)
        for zones, ttl in ((self.pools,500),(self.fvgs,250),(self.obs,250)):
            zones[:] = [z for z in zones if not z.terminal and self.index-z.born <= ttl]
        hi, lo, cl = self.ticks(bar.high), self.ticks(bar.low), self.ticks(bar.close)
        swept_low = swept_high = None
        for z in self.pools:
            level = self.ticks(z.low)
            if (z.side == -1 and cl > level) or (z.side == 1 and cl < level):
                z.terminal = True
            elif not z.touched and ((z.side == -1 and hi > level and cl <= level) or (z.side == 1 and lo < level and cl >= level)):
                z.touched = True
                if z.side == -1: swept_high = z.high if swept_high is None else max(swept_high,z.high)
                else: swept_low = z.low if swept_low is None else min(swept_low,z.low)
        for z in self.fvgs + self.obs:
            zl, zh = self.ticks(z.low), self.ticks(z.high)
            invalid = (z.side == 1 and cl < zl) or (z.side == -1 and cl > zh)
            filled = z.kind == 'FVG' and ((z.side == 1 and lo <= zl) or (z.side == -1 and hi >= zh))
            z.terminal |= invalid or filled
            if not z.terminal and hi >= zl and lo <= zh: z.touched = True
        new_fvg_side = 0
        if len(self.history) >= 2:
            b2 = self.history[-2]
            if lo > self.ticks(b2.high) and self.ticks(prev.high) > self.ticks(b2.high):
                self.add_zone('FVG',1,bar,b2.high,bar.low); new_fvg_side = 1
            elif hi < self.ticks(b2.low) and self.ticks(prev.low) < self.ticks(b2.low):
                self.add_zone('FVG',-1,bar,bar.high,b2.low); new_fvg_side = -1
        for side, exists, swing in ((1,new_low,self.low_swing),(-1,new_high,self.high_swing)):
            if not exists: continue
            level = swing[0]
            match = next((z for z in self.pools if not z.terminal and not z.touched and z.side == side and abs(self.ticks(z.low)-level) <= 1), None)
            if match:
                match.low = match.high = (min(self.ticks(match.low),level) if side == 1 else max(self.ticks(match.low),level))*self.tick
            else: self.add_zone('POOL',side,bar,level*self.tick,level*self.tick)
        bull = old_high is not None and not self.high_consumed and cl > old_high[0]
        bear = old_low is not None and not self.low_consumed and cl < old_low[0]
        event = 0
        if bull and bear: self.trend = 0
        elif bull:
            event = 2 if self.trend == -1 else 1
            self.trend = 1; self.high_consumed = True
        elif bear:
            event = -2 if self.trend == 1 else -1
            self.trend = -1; self.low_consumed = True
        if new_high: self.high_consumed = False
        if new_low: self.low_consumed = False
        if event:
            self.structure = {'type':event,'time':bar.time,'price':(old_high[0] if event > 0 else old_low[0])*self.tick}
            self.events.append({'time':bar.time//1000,'side':self.trend,'kind':'vsa_structure','text':('CHoCH' if abs(event)==2 else 'BOS')})
        if event and (event > 0)-(event < 0) == new_fvg_side:
            for b in reversed(prior):
                if (event > 0 and self.ticks(b.close) < self.ticks(b.open)) or (event < 0 and self.ticks(b.close) > self.ticks(b.open)):
                    self.add_zone('OB',self.trend,bar,b.low,b.high); break
        for zones, cap in ((self.pools,8),(self.fvgs,5),(self.obs,5)):
            zones[:] = [z for z in zones if not z.terminal][-cap:]
        self.low_sweep.update(1,swept_low,bar.low,self.index,bar.time,bar.close)
        self.high_sweep.update(-1,swept_high,bar.high,self.index,bar.time,bar.close)
        sweep_code = 2 if swept_low is not None and swept_high is not None else 1 if swept_low is not None else -1 if swept_high is not None else 0
        if sweep_code:
            self.events.append({'time':bar.time//1000,'side':1 if sweep_code==1 else -1,'kind':'vsa_sweep','text':{1:'Quét đáy',-1:'Quét đỉnh',2:'Quét hai phía'}[sweep_code]})
        distance = (bar.close-self.ema)/self.atr if self.ema is not None and self.atr and self.atr > 0 else None
        ready = valid and distance is not None and self.index >= max(21,3*self.ema_length)
        context_ready = self.timeframe in HTF and len(contexts)==2 and all(c is not None for c in contexts)
        recent = lambda sw: 0 <= sw.age(self.index) <= 10 and not sw.invalid
        sides = []
        for side, sw, other in ((1,self.low_sweep,self.high_sweep),(-1,self.high_sweep,self.low_sweep)):
            structure = sw.stamp is not None and self.structure is not None and self.structure['time'] >= sw.stamp and self.trend == side and (self.structure['type']>0)-(self.structure['type']<0) == side
            aligned = context_ready and all(direction(c)==side for c in contexts)
            mask = setup_mask(sw.age(self.index),sw.invalid,recent(sw) and recent(other),structure,aligned,vsa != 99 and vsa*side>0,distance is not None and abs(distance)>2.5,ready)
            reasons = [text for flag,text in REASONS.items() if mask & flag]
            if not context_ready: reasons = ['Thiếu nến HTF đã đóng' if r == REASONS[64] else r for r in reasons]
            sides.append({'side':side,'phase':phase(mask),'text':PHASES[phase(mask)],'mask':mask,'reasons':reasons,
                          'sweep':{**asdict(sw),'age':sw.age(self.index)},'structureConfirmed':structure,
                          'zone':self.zone_context(side,bar.close)})
        self.history.append(bar)
        self.snapshot = {'version':VERSION,'closedAt':bar.end,'barTime':bar.time,'barCount':self.index,
                         'warmupRequired':max(21,3*self.ema_length),'dataReady':bool(ready),'vsa':vsa,'rv':rv,'rr':rr,
                         'ema':self.ema,'atr':self.atr,'distanceAtr':distance,'sweepCode':sweep_code,
                         'structure':dict(self.structure) if self.structure else None,'trend':self.trend,
                         'contexts':[None if c is None else {'time':c.time,'end':c.end,'direction':direction(c)} for c in contexts],
                         'long':sides[0],'short':sides[1]}
        return self.snapshot
