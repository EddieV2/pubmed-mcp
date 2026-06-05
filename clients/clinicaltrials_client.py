"""ClinicalTrials.gov client — the v2 API (the legacy v1 API was retired in June 2024).

No API key required.

Contract verified live (2026-06): ``GET /studies?query.cond=&pageSize=&format=json`` →
``{"studies": [ {"protocolSection": {identificationModule, statusModule, ...}} ], "nextPageToken": str}``.
"""

from typing import Any, Dict, Optional

from .base import BaseHTTPClient


class ClinicalTrialsClient(BaseHTTPClient):
    """Client for the ClinicalTrials.gov v2 API."""

    BASE_URL = "https://clinicaltrials.gov/api/v2"

    def __init__(self) -> None:
        super().__init__(self.BASE_URL, min_interval=0.2)

    def search(
        self,
        *,
        condition: Optional[str] = None,
        term: Optional[str] = None,
        status: Optional[str] = None,
        page_size: int = 10,
    ) -> Dict[str, Any]:
        """Search studies. ``status`` is an overallStatus filter (e.g. RECRUITING, COMPLETED)."""
        params: Dict[str, Any] = {
            "format": "json",
            "pageSize": max(1, min(int(page_size), 50)),
        }
        if condition:
            params["query.cond"] = condition
        if term:
            params["query.term"] = term
        if status:
            params["filter.overallStatus"] = status
        return self.get_json("studies", params)
