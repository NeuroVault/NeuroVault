from dataclasses import dataclass, field
from typing import Optional

from . import vocabulary as v

ACTIVE = "active"
INACTIVE = "inactive"
COMPLETED = "completed"


@dataclass
class Metaanalysis:
    id: Optional[int]
    owner_id: Optional[int]
    name: str
    description: Optional[str] = None
    status: Optional[str] = ACTIVE
    map_ids: frozenset = field(default_factory=frozenset)
    output_collection_id: Optional[int] = None

    @property
    def is_completed(self):
        return self.status == COMPLETED


def accepts_map(item):
    """Group-level T or Z statistic maps can join a meta-analysis."""
    stats = item.stats
    return (
        item.is_statmap
        and not item.payload.from_nidm
        and stats.analysis_level == v.GROUP
        and stats.map_type in (v.T, v.Z)
    )


def description_for(n_maps, weighted):
    if weighted:
        return (
            "Two sided Stouffer's fixed-effects image-based "
            f"meta-analysis on {n_maps} maps weighted by "
            "their corresponding sample sizes. FWE corrected "
            "with theoretical null distribution."
        )
    return (
        "Two sided Stouffer's fixed-effects image-based "
        f"meta-analysis on {n_maps} maps. FWE "
        "corrected with theoretical null distribution."
    )
