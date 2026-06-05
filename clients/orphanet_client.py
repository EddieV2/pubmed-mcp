"""Orphanet client — rare-disease reference data via the Orphanet API (api.orphacode.org).

Provides the preferred term, definition, and canonical URL for an ORPHA code. The API expects
an ``apiKey`` header to be present but (as of 2026-06) accepts any non-empty value for the free
English endpoints. Orphanet content is CC BY 4.0.
"""

from typing import Any, Dict

from .base import BaseHTTPClient


class OrphanetClient(BaseHTTPClient):
    """Client for the Orphanet (Orphadata) code API."""

    BASE_URL = "https://api.orphacode.org/EN"

    def __init__(self) -> None:
        super().__init__(self.BASE_URL, min_interval=0.2, headers={"apiKey": "biomed-mcp"})
        # Memoize successful lookups for the process lifetime. Orphanet clinical entities are
        # stable reference data, and api.orphacode.org has intermittently unreliable DNS — so a
        # disease that resolved once keeps enriching cards through later outages. Only successful
        # fetches are stored (failures raise before reaching the cache), so it can't be poisoned.
        self._cache: Dict[str, Dict[str, Any]] = {}

    def get_clinical_entity(self, orphacode: str) -> Dict[str, Any]:
        """Fetch a rare-disease clinical entity by ORPHA code (digits only), memoized on success."""
        code = "".join(ch for ch in str(orphacode) if ch.isdigit())
        cached = self._cache.get(code)
        if cached is not None:
            return cached
        entity = self.get_json(f"ClinicalEntity/orphacode/{code}")
        self._cache[code] = entity
        return entity
