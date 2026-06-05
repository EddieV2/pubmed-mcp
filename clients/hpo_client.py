"""Human Phenotype Ontology (HPO) term lookup via NIH Clinical Tables.

Turns free-text symptom descriptions into standardized ``HP:`` codes, which Monarch's
semsim engine consumes. No API key required.

Contract verified live (2026-06): ``GET .../search?terms=&maxList=`` returns
``[total_count, ["HP:...", ...], null, [["HP:...", "Label"], ...]]``.
"""

from typing import Dict, List

from .base import BaseHTTPClient


class HPOClient(BaseHTTPClient):
    """Client for the NIH Clinical Tables HPO autocomplete API."""

    BASE_URL = "https://clinicaltables.nlm.nih.gov/api/hpo/v3"

    def __init__(self) -> None:
        super().__init__(self.BASE_URL, min_interval=0.1)

    def search(self, text: str, *, max_list: int = 7) -> List[Dict[str, str]]:
        """Return best-matching HPO terms as ``[{'id': 'HP:...', 'name': '...'}, ...]``."""
        params = {"terms": text, "maxList": max_list}
        data = self.get_json("search", params)
        pairs = data[3] if isinstance(data, list) and len(data) > 3 and data[3] else []
        return [{"id": code, "name": label} for code, label in pairs]
