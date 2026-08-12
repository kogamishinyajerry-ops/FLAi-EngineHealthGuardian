"""Feature engineering — generic, phase-aware normalization primitives.

Scenario-specific feature engineering (e.g. EGT / vibration residuals) lives in
each ``scenarios/<name>/features.py``; the library only provides the reusable
``PeerGroup`` (see ADR-0007).
"""

from ehm.data_brain.features.peer import PeerGroup

__all__ = ["PeerGroup"]
