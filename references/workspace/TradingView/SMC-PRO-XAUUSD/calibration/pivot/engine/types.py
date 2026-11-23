from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class PivotType(str, Enum):
    HIGH = "HIGH"
    LOW = "LOW"


class TradeDirection(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class EventState(str, Enum):
    CANDIDATE = "CANDIDATE"
    CONFIRMED = "CONFIRMED"
    WAITING_FOR_ENTRY = "WAITING_FOR_ENTRY"
    ACTIVE = "ACTIVE"
    TARGET_HIT = "TARGET_HIT"
    STOP_HIT = "STOP_HIT"
    TARGET_GAP = "TARGET_GAP"
    STOP_GAP = "STOP_GAP"
    AMBIGUOUS = "AMBIGUOUS"
    EXPIRED = "EXPIRED"
    INVALIDATED = "INVALIDATED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class TerminalLabel(str, Enum):
    TARGET_HIT = "TARGET_HIT"
    STOP_HIT = "STOP_HIT"
    TARGET_GAP = "TARGET_GAP"
    STOP_GAP = "STOP_GAP"
    AMBIGUOUS_BOTH_TOUCHED = "AMBIGUOUS_BOTH_TOUCHED"
    EXPIRED_NO_ENTRY = "EXPIRED_NO_ENTRY"
    EXPIRED_AFTER_ENTRY = "EXPIRED_AFTER_ENTRY"
    INVALIDATED_BEFORE_ENTRY = "INVALIDATED_BEFORE_ENTRY"
    CANCELLED_BY_NEW_STRUCTURE = "CANCELLED_BY_NEW_STRUCTURE"
    NO_VALID_STOP = "NO_VALID_STOP"
    NO_VALID_TARGET = "NO_VALID_TARGET"
    INSUFFICIENT_FORWARD_HORIZON = "INSUFFICIENT_FORWARD_HORIZON"
    PARTITION_BOUNDARY_REJECTED = "PARTITION_BOUNDARY_REJECTED"
    DATA_QUALITY_REJECTED = "DATA_QUALITY_REJECTED"


@dataclass(frozen=True)
class Bar:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    timeframe: str
    profile: str

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo is None:
            raise ValueError("bar timestamp must be timezone-aware")
        if self.high < max(self.open, self.close, self.low) or self.low > min(self.open, self.close, self.high):
            raise ValueError("invalid OHLC ordering")


@dataclass(frozen=True)
class ConfirmedPivot:
    pivot_index: int
    confirmation_index: int
    pivot_timestamp: datetime
    confirmation_timestamp: datetime
    pivot_price: float
    pivot_type: PivotType
    left_strength: int
    right_strength: int
    profile: str
    timeframe: str


@dataclass(frozen=True)
class FeatureValue:
    value: float
    as_of_timestamp: datetime
    source_start_index: int
    source_end_index: int


@dataclass(frozen=True)
class Transition:
    event_id: str
    previous_state: EventState | None
    new_state: EventState
    transition_timestamp: datetime
    transition_reason: str
    profile: str
    timeframe: str
    configuration_id: str


@dataclass
class PivotEvent:
    event_id: str
    configuration_id: str
    profile: str
    timeframe: str
    pivot: ConfirmedPivot
    direction: TradeDirection
    state: EventState = EventState.CANDIDATE
    transitions: list[Transition] = field(default_factory=list)
    entry_index: int | None = None
    entry_timestamp: datetime | None = None
    entry_price: float | None = None
    stop_price: float | None = None
    target_price: float | None = None
    terminal_label: TerminalLabel | None = None
    terminal_timestamp: datetime | None = None
    exit_price: float | None = None
    terminal_level: float | None = None
    gap_slippage: float | None = None
    terminal_reason: str | None = None
    ambiguity: bool = False


@dataclass(frozen=True)
class Outcome:
    label: TerminalLabel
    timestamp: datetime
    reason: str
    exit_price: float | None
    terminal_level: float | None
    gap_slippage: float | None = None
    ambiguity: bool = False


@dataclass(frozen=True)
class HarnessConfig:
    stage: str
    profile: str
    timeframe: str
    pivot_strength: int
    atr_period: int
    volatility_window: int
    displacement_window: int
    structure_confirmation: int
    entry_confirmation: int
    retest_window: int
    setup_expiry: int
    max_event_lifecycle: int
    atr_stop_multiplier: float
    stop_buffer_atr_fraction: float
    reward_risk_multiple: float
    symbol_tick_size: float = 0.01
    contract_version: int = 1

    def payload(self) -> dict[str, Any]:
        return dict(self.__dict__)
