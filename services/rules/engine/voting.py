"""
Sliding window temporal voting logic.
Spec: 04_AI_MODEL_SPEC.md §7.
"""

from collections import deque
from typing import Optional, Deque
from services.rules.engine.config import VotingConfig
from services.rules.engine.states import STATE_COMPLIANT, STATE_VIOLATING, STATE_UNKNOWN

DECISION_VIOLATING: str = "violating"
DECISION_COMPLIANT: str = "compliant"
DECISION_UNDECIDED: str = "undecided"

class TemporalVotingWindow:
    """Maintains a rolling history of valid frame states for a person and rule."""
    def __init__(self, config: Optional[VotingConfig] = None):
        self.config = config or VotingConfig()
        self.window: Deque[str] = deque(maxlen=self.config.window_frames)

    def add_frame_state(self, state: str) -> None:
        """
        Appends state to voting window.
        UNKNOWN is ignored and does not reset or count in voting.
        """
        if state in (STATE_COMPLIANT, STATE_VIOLATING):
            self.window.append(state)

    def get_decision(self) -> str:
        """
        Evaluates current sliding window:
        - If len < min_votes -> UNDECIDED
        - If violating ratio >= confirm_ratio -> VIOLATING
        - If violating ratio <= clear_ratio -> COMPLIANT
        - Else -> UNDECIDED
        """
        if len(self.window) < self.config.min_votes:
            return DECISION_UNDECIDED

        violating_count = sum(1 for s in self.window if s == STATE_VIOLATING)
        total = len(self.window)
        ratio = violating_count / total

        if ratio >= self.config.confirm_ratio:
            return DECISION_VIOLATING
        elif ratio <= self.config.clear_ratio:
            return DECISION_COMPLIANT
        else:
            return DECISION_UNDECIDED

    def get_violating_ratio(self) -> float:
        if not self.window:
            return 0.0
        return sum(1 for s in self.window if s == STATE_VIOLATING) / len(self.window)

    def reset(self) -> None:
        self.window.clear()
