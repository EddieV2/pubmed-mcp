"""MedlinePlus Connect client — patient-friendly health information by diagnosis code.

Given a clinical code (here ICD-10-CM), returns consumer health topics from the U.S. National
Library of Medicine. No API key required.

Contract verified live (2026-06): ``GET /service?mainSearchCriteria.v.cs=<OID>&mainSearchCriteria.v.c=<code>
&knowledgeResponseType=application/json`` → ``{"feed": {"entry": [ {title, link, summary, ...} ]}}``.
"""

from typing import Any, Dict, List

from .base import BaseHTTPClient

# HL7 OIDs for the code systems MedlinePlus Connect accepts.
ICD10CM_OID = "2.16.840.1.113883.6.90"


class MedlinePlusClient(BaseHTTPClient):
    """Client for the MedlinePlus Connect web service."""

    BASE_URL = "https://connect.medlineplus.gov"

    def __init__(self) -> None:
        super().__init__(self.BASE_URL, min_interval=0.15)

    def connect_by_icd10cm(self, code: str) -> List[Dict[str, Any]]:
        """Return patient-facing topics for an ICD-10-CM code as ``[{title, url, summary}, ...]``."""
        params = {
            "mainSearchCriteria.v.cs": ICD10CM_OID,
            "mainSearchCriteria.v.c": code,
            "knowledgeResponseType": "application/json",
        }
        data = self.get_json("service", params)
        entries = (data.get("feed") or {}).get("entry") or []

        topics: List[Dict[str, Any]] = []
        for entry in entries:
            title = entry.get("title")
            if isinstance(title, dict):
                title = title.get("_value")
            summary = entry.get("summary")
            if isinstance(summary, dict):
                summary = summary.get("_value")
            links = entry.get("link") or []
            href = None
            if isinstance(links, list) and links:
                href = links[0].get("href")
            elif isinstance(links, dict):
                href = links.get("href")
            topics.append({
                "title": title,
                "url": href,
                "summary": (summary or "")[:300] or None,
            })
        return topics
