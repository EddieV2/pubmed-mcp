"""NCBI E-utilities client, generalized across Entrez databases via the ``db`` param.

All NCBI databases (pubmed, pmc, clinvar, gene, mesh, snp, nuccore, ...) are served by
the same E-utilities endpoints and share ONE rate limit per API key/IP. A single instance
of this client therefore coordinates every database behind one shared throttle — which is
why the whole NCBI family belongs in one client, not one-server-per-database.
"""

import json
import xml.etree.ElementTree as ET
from typing import Dict, Iterable, List, Optional, Union

from .base import BaseHTTPClient

IdsArg = Union[str, Iterable[str]]


def _join_ids(ids: IdsArg) -> str:
    if isinstance(ids, str):
        return ids
    return ",".join(str(i) for i in ids)


class NCBIClient(BaseHTTPClient):
    """Client for NCBI E-utilities (esearch / efetch / esummary)."""

    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    def __init__(
        self,
        api_key: Optional[str] = None,
        email: Optional[str] = None,
        tool: str = "biomed-mcp",
    ):
        default_params: Dict[str, str] = {"tool": tool}
        if api_key:
            default_params["api_key"] = api_key
        if email:
            default_params["email"] = email
        # 10 req/s with a key, 3 req/s without — shared across all databases.
        super().__init__(
            self.BASE_URL,
            min_interval=0.1 if api_key else 0.34,
            default_params=default_params,
        )

    def esearch(
        self,
        db: str,
        term: str,
        *,
        retmax: int = 20,
        sort: str = "relevance",
        retmode: str = "xml",
    ) -> str:
        """Raw esearch response text."""
        params = {
            "db": db,
            "term": term,
            "retmax": str(retmax),
            "retmode": retmode,
            "sort": sort,
        }
        return self.get_text("esearch.fcgi", params)

    def search(
        self, db: str, term: str, *, retmax: int = 20, sort: str = "relevance"
    ) -> Dict[str, object]:
        """Search a database and return ``{'ids': [...], 'total_count': int}``.

        Works for any Entrez database (pubmed, clinvar, gene, mesh, ...).
        """
        text = self.esearch(db, term, retmax=retmax, sort=sort, retmode="xml")
        root = ET.fromstring(text)

        ids: List[str] = []
        id_list = root.find("IdList")
        if id_list is not None:
            ids = [e.text for e in id_list.findall("Id") if e.text]

        count_elem = root.find("Count")
        total = int(count_elem.text) if count_elem is not None and count_elem.text else 0
        return {"ids": ids, "total_count": total}

    def efetch(
        self,
        db: str,
        ids: IdsArg,
        *,
        rettype: str = "abstract",
        retmode: str = "xml",
    ) -> str:
        """Fetch full records for one or more IDs (returns raw text in the requested format)."""
        params = {
            "db": db,
            "id": _join_ids(ids),
            "rettype": rettype,
            "retmode": retmode,
        }
        return self.get_text("efetch.fcgi", params)

    def esummary(self, db: str, ids: IdsArg, *, retmode: str = "xml") -> str:
        """Document summaries (metadata) for one or more IDs."""
        params = {"db": db, "id": _join_ids(ids), "retmode": retmode}
        return self.get_text("esummary.fcgi", params)

    def esummary_json(self, db: str, ids: IdsArg) -> Dict[str, object]:
        """Document summaries as parsed JSON (retmode=json) — used for ClinVar/Gene records."""
        return json.loads(self.esummary(db, ids, retmode="json"))
