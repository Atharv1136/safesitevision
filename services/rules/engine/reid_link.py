"""
Re-Identification (Re-ID) appearance linking and duplicate disambiguation.
Spec: 04_AI_MODEL_SPEC.md §6, 02_PRODUCT_FLOW.md §2.4, §2.5.
"""

from typing import List, Optional, Tuple, Dict, Any
import numpy as np
from services.rules.engine.config import ReidConfig

LINK_SAME_PERSON: str = "same_person"
LINK_POSSIBLE_DUPLICATE: str = "possible_duplicate"
LINK_DISTINCT_PERSON: str = "distinct_person"

class ReidLinker:
    """Evaluates appearance similarity and spatial/temporal continuity to re-identify workers."""
    def __init__(self, config: Optional[ReidConfig] = None):
        self.config = config or ReidConfig()

    @staticmethod
    def cosine_similarity(emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Computes cosine similarity between two 1D or normalized embedding vectors."""
        if emb1 is None or emb2 is None:
            return 0.0
        n1 = np.linalg.norm(emb1)
        n2 = np.linalg.norm(emb2)
        if n1 == 0 or n2 == 0:
            return 0.0
        return float(np.dot(emb1, emb2) / (n1 * n2))

    def evaluate_link(
        self,
        new_embedding: Optional[np.ndarray],
        new_pos: Tuple[float, float], # normalized (x, y)
        new_timestamp: float,
        candidate_embedding: Optional[np.ndarray],
        candidate_last_pos: Tuple[float, float],
        candidate_last_seen: float
    ) -> Tuple[str, float]:
        """
        Determines if a new track corresponds to an open/recent episode.
        Returns: (link_decision, similarity_score)
        """
        if new_embedding is None or candidate_embedding is None:
            return (LINK_DISTINCT_PERSON, 0.0)

        # Temporal check
        time_gap = new_timestamp - candidate_last_seen
        if time_gap > self.config.max_gap_s:
            return (LINK_DISTINCT_PERSON, 0.0)

        # Appearance similarity
        sim = self.cosine_similarity(new_embedding, candidate_embedding)

        # Spatial plausibility (workers cannot teleport across full frame instantly)
        # Normalized distance / time speed check
        dx = new_pos[0] - candidate_last_pos[0]
        dy = new_pos[1] - candidate_last_pos[1]
        dist = np.sqrt(dx * dx + dy * dy)
        
        # Simultaneous presence check:
        # If candidate was seen at the exact same timestamp at different locations,
        # they are distinct people co-present in the frame (e.g. identical overalls).
        if time_gap < 0.5 and dist > 0.03:
            return (LINK_DISTINCT_PERSON, sim)

        # If time gap is very small (e.g. < 2s), large jump is unlikely unless edge of frame
        if time_gap < 2.0 and dist > 0.8:
            return (LINK_DISTINCT_PERSON, sim)

        # Clear Match
        if sim >= self.config.link_similarity:
            return (LINK_SAME_PERSON, sim)
            
        # Grey Band: Never silently merge! Mark possible duplicate so human can review
        elif sim >= self.config.grey_band_low:
            return (LINK_POSSIBLE_DUPLICATE, sim)
            
        else:
            return (LINK_DISTINCT_PERSON, sim)
