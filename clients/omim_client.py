"""OMIM client — gold-standard catalog of Mendelian disorders (OPTIONAL).

Requires a free *academic* OMIM API key (set ``OMIM_API_KEY``). The server only instantiates
this client when a key is present, so everything else works without it.

Licensing note: OMIM is free for academic/non-profit use with a key, but is NOT redistributable
for commercial use without a paid license from JHU. Keep this server academic-only while OMIM is wired in.
"""

from typing import Any, Dict

from .base import BaseHTTPClient


class OMIMClient(BaseHTTPClient):
    """Client for the OMIM API (api.omim.org)."""

    BASE_URL = "https://api.omim.org/api"

    def __init__(self, api_key: str):
        super().__init__(
            self.BASE_URL,
            min_interval=0.2,
            default_params={"apiKey": api_key, "format": "json"},
        )

    def get_entry(self, mim_number: str, *, include: str = "clinicalSynopsis") -> Dict[str, Any]:
        """Fetch an OMIM entry; returns a compact summary (title + clinical-synopsis sections)."""
        num = "".join(ch for ch in str(mim_number) if ch.isdigit())
        data = self.get_json("entry", {"mimNumber": num, "include": include})
        entries = (((data or {}).get("omim") or {}).get("entryList")) or []
        if not entries:
            return {"mim_number": num, "found": False}
        entry = entries[0].get("entry", {}) or {}
        synopsis = entry.get("clinicalSynopsis", {})
        return {
            "mim_number": num,
            "preferred_title": (entry.get("titles") or {}).get("preferredTitle"),
            "clinical_synopsis_sections": (
                [k for k in synopsis.keys() if not k.startswith("old")][:20]
                if isinstance(synopsis, dict) else None
            ),
            "found": True,
        }
