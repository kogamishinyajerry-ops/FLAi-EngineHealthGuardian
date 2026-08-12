"""Feature engineering — phase-aware, physics/peer normalization."""

from ehm.data_brain.features.egt import baseline, residual
from ehm.data_brain.features.peer import PeerGroup

__all__ = ["PeerGroup", "baseline", "residual"]
