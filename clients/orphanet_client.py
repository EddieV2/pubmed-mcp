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

    def get_clinical_entity(self, orphacode: str) -> Dict[str, Any]:
        """Fetch a rare-disease clinical entity by ORPHA code (digits only)."""
        code = "".join(ch for ch in str(orphacode) if ch.isdigit())
        return self.get_json(f"ClinicalEntity/orphacode/{code}")
