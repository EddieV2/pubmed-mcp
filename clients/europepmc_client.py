"""Europe PMC client — biomedical literature search (a PubMed superset).

Adds full-text availability, open-access flags, abstracts, and text-mined annotations.
No API key required.

Contract verified live (2026-06): ``GET /search?query=&format=json&resultType=core`` →
``{"hitCount": int, "resultList": {"result": [ {id, source, pmid, doi, title, ...} ]}}``.
"""

from typing import Any, Dict

from .base import BaseHTTPClient


class EuropePMCClient(BaseHTTPClient):
    """Client for the Europe PMC REST API."""

    BASE_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest"

    def __init__(self) -> None:
        super().__init__(self.BASE_URL, min_interval=0.15)

    def search(self, query: str, *, page_size: int = 10, result_type: str = "core") -> Dict[str, Any]:
        """Search the literature. ``result_type='core'`` includes abstracts and rich metadata."""
        params = {
            "query": query,
            "format": "json",
            "pageSize": max(1, min(int(page_size), 100)),
            "resultType": result_type,
        }
        return self.get_json("search", params)
