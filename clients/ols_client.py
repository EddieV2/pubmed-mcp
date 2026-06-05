"""EBI OLS4 client — Ontology Lookup Service.

Used as a robust fallback for Orphanet rare-disease definitions: OLS hosts ORDO (the Orphanet
Rare Disease Ontology), so when ``api.orphacode.org`` is unreachable (it has intermittently
flaky DNS), OLS still serves the same Orphanet definition + preferred label, keyed by ORPHA
code. OLS runs on the same EBI infrastructure as Europe PMC (reliable). No API key. ORDO is
CC BY 4.0.
"""

from typing import Any, Dict, Optional
from urllib.parse import quote

from .base import BaseHTTPClient


class OLSClient(BaseHTTPClient):
    """Client for the EBI Ontology Lookup Service (OLS4)."""

    BASE_URL = "https://www.ebi.ac.uk/ols4/api"
    _ORDO_IRI = "http://www.orpha.net/ORDO/Orphanet_{code}"

    def __init__(self) -> None:
        super().__init__(self.BASE_URL, min_interval=0.1)

    def get_ordo_term(self, orphacode: str) -> Optional[Dict[str, Any]]:
        """Look up an ORDO term by ORPHA code.

        Returns ``{orphacode, preferred_term, definition, url, source}`` or ``None`` if the term
        carries neither a label nor a definition. Raises (UpstreamError/HTTPError) on transport
        failure, so callers can distinguish "unavailable" from "no data".
        """
        code = "".join(ch for ch in str(orphacode) if ch.isdigit())
        if not code:
            return None
        iri = self._ORDO_IRI.format(code=code)
        # OLS expects the term IRI double-URL-encoded inside the path.
        enc = quote(quote(iri, safe=""), safe="")
        data = self.get_json(f"ontologies/ordo/terms/{enc}")

        label = data.get("label")
        descr = data.get("description")
        if isinstance(descr, (list, tuple)):
            definition = next((d for d in descr if d), None)
        else:
            definition = descr or None
        if not label and not definition:
            return None
        return {
            "orphacode": int(code),
            "preferred_term": label,
            "definition": definition,
            "url": data.get("iri") or iri,
            "source": "EBI OLS (ORDO)",
        }
