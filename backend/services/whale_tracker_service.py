"""
Whale Tracker Service — promoted from _quarantine/whale_tracker.py (v0.8.1).
Detects Smart Money volume patterns across the SGN Mesh.
Changes from quarantine: scan_for_whale_movement() dropped (random), register() + get_pulses() added,
singleton removed, no random import.
"""
import logging
from typing import List

from pydantic import BaseModel

logger = logging.getLogger("pbg.whale_tracker")

_SIM_PULSES = [
    {"match_id": "LIV_ARS",  "selection": "1X2_HOME",   "volume": 3_200_000, "confidence": 0.94, "nodes": 7},
    {"match_id": "RMA_BAR",  "selection": "O2.5_GOALS", "volume": 2_750_000, "confidence": 0.88, "nodes": 5},
    {"match_id": "MCI_MUN",  "selection": "BTTS_YES",   "volume": 1_850_000, "confidence": 0.76, "nodes": 4},
    {"match_id": "PSG_BVB",  "selection": "1X2_AWAY",   "volume": 4_100_000, "confidence": 0.91, "nodes": 9},
    {"match_id": "JUV_INT",  "selection": "1X2_DRAW",   "volume": 1_200_000, "confidence": 0.72, "nodes": 3},
]


class WhalePulse(BaseModel):
    match_id: str
    selection: str
    aggregated_volume: float
    confidence_score: float
    nodes_reporting: int


class WhaleTrackerService:
    def __init__(self):
        self._detected: List[WhalePulse] = []

    def register(self, pulse: WhalePulse) -> None:
        self._detected.insert(0, pulse)
        self._detected = self._detected[:20]
        logger.info(
            "WHALE_DETECTED: %.0f volume on %s | confidence=%.2f",
            pulse.aggregated_volume, pulse.match_id, pulse.confidence_score,
        )

    def get_pulses(self, limit: int = 10) -> List[WhalePulse]:
        if self._detected:
            return self._detected[:limit]
        return self._simulate(limit)

    def _simulate(self, limit: int) -> List[WhalePulse]:
        return [
            WhalePulse(
                match_id=s["match_id"],
                selection=s["selection"],
                aggregated_volume=s["volume"],
                confidence_score=s["confidence"],
                nodes_reporting=s["nodes"],
            )
            for s in _SIM_PULSES[:limit]
        ]
