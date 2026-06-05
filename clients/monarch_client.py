"""Monarch Initiative v3 API client.

The Monarch knowledge graph is our phenotype→disease engine. The key endpoint is
``POST /semsim/search``: given a set of HPO phenotype terms, it returns a ranked list of
candidate diseases (semantic similarity). No API key required.

Contract verified live (2026-06): semsim/search is POST; the response is a JSON *list* of
``{"subject": {entity}, "score": float, "similarity": {...}}`` ordered best-first.
"""

from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import quote

from .base import BaseHTTPClient


class MonarchClient(BaseHTTPClient):
    """Client for the Monarch Initiative v3 API."""

    BASE_URL = "https://api-v3.monarchinitiative.org/v3/api"

    SEMSIM_GROUPS = {
        "Human Diseases",
        "Human Genes",
        "Mouse Genes",
        "Rat Genes",
        "Zebrafish Genes",
        "C. Elegans Genes",
    }
    SEMSIM_METRICS = {
        "ancestor_information_content",
        "jaccard_similarity",
        "phenodigm_score",
    }

    # semsim/search is compute-heavy and its latency is highly variable: ≈2-3s typically,
    # but it can spike well past the default 25s timeout under load. Give it a longer budget
    # plus one retry so a transient spike doesn't sink the whole symptom→disease lookup.
    SEMSIM_TIMEOUT = 45
    SEMSIM_RETRIES = 1

    def __init__(self) -> None:
        super().__init__(self.BASE_URL, min_interval=0.2)

    def search(
        self,
        q: str,
        *,
        category: Optional[str] = None,
        limit: int = 10,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Free-text entity search. Pass ``category='biolink:Disease'`` to restrict to diseases."""
        params = {"q": q, "limit": limit, "offset": offset, "category": category}
        return self.get_json("search", params)

    def semsim_search(
        self,
        termset: Iterable[str],
        *,
        group: str = "Human Diseases",
        metric: str = "ancestor_information_content",
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Rank entities (default: diseases) by phenotype similarity to ``termset`` (HPO IDs)."""
        if group not in self.SEMSIM_GROUPS:
            group = "Human Diseases"
        if metric not in self.SEMSIM_METRICS:
            metric = "ancestor_information_content"
        body = {
            "termset": list(termset),
            "group": group,
            "metric": metric,
            "limit": max(1, min(int(limit), 50)),
        }
        return self.post_json(
            "semsim/search", body, timeout=self.SEMSIM_TIMEOUT, retries=self.SEMSIM_RETRIES
        )

    def get_entity(self, entity_id: str) -> Dict[str, Any]:
        """Full entity record by CURIE (e.g. ``MONDO:0007947``)."""
        return self.get_json(f"entity/{quote(entity_id, safe=':')}")
