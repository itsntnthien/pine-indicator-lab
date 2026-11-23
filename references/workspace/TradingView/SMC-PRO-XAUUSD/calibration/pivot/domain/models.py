from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from .enums import PivotProfileFamily, PivotDirection, CandidateStatus

@dataclass(frozen=True)
class OHLCBar:
    timestamp: datetime; open: float; high: float; low: float; close: float
    volume: Optional[float]=None; timeframe: str="M1"; provider: str="OANDA"; symbol: str="XAUUSD"; source_hash: str=""

@dataclass
class PivotCandidate:
    stable_id: str; profile_family: PivotProfileFamily; direction: PivotDirection; source_index: int; source_timestamp: datetime; source_price: float
    left_strength: int; right_strength: int; confirmation_delay: int; created_at_index: int; expected_confirmation_index: int
    status: CandidateStatus=CandidateStatus.ACTIVE; replacement_id: Optional[str]=None; invalidation_reason: Optional[str]=None; committed_at_index: Optional[int]=None

@dataclass(frozen=True)
class CommittedPivot:
    stable_id: str; profile_family: PivotProfileFamily; direction: PivotDirection; source_index: int; source_timestamp: datetime; source_price: float
    confirmed_index: int; confirmed_timestamp: datetime; left_strength: int; right_strength: int; dataset_hash: str; run_id: str
