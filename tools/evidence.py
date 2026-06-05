"""Evidence tools — literature (Europe PMC) and clinical trials (ClinicalTrials.gov v2)."""

from typing import Any, Dict


def _format_epmc(r: Dict[str, Any]) -> Dict[str, Any]:
    journal = None
    jinfo = r.get("journalInfo")
    if isinstance(jinfo, dict):
        journal = (jinfo.get("journal") or {}).get("title")
    abstract = r.get("abstractText") or ""
    return {
        "id": r.get("id"),
        "source": r.get("source"),
        "pmid": r.get("pmid"),
        "doi": r.get("doi"),
        "title": r.get("title"),
        "authors": r.get("authorString"),
        "journal": journal,
        "year": r.get("pubYear"),
        "is_open_access": r.get("isOpenAccess") == "Y",
        "has_fulltext_in_epmc": r.get("inEPMC") == "Y",
        "cited_by_count": r.get("citedByCount"),
        "abstract": (abstract[:500] + "…") if len(abstract) > 500 else (abstract or None),
    }


def _format_trial(study: Dict[str, Any]) -> Dict[str, Any]:
    ps = study.get("protocolSection", {}) or {}
    idm = ps.get("identificationModule", {}) or {}
    stm = ps.get("statusModule", {}) or {}
    dm = ps.get("designModule", {}) or {}
    cm = ps.get("conditionsModule", {}) or {}
    descm = ps.get("descriptionModule", {}) or {}
    nct = idm.get("nctId")
    summary = descm.get("briefSummary") or ""
    return {
        "nct_id": nct,
        "title": idm.get("briefTitle"),
        "status": stm.get("overallStatus"),
        "phases": dm.get("phases"),
        "study_type": dm.get("studyType"),
        "conditions": cm.get("conditions"),
        "summary": (summary[:400] + "…") if len(summary) > 400 else (summary or None),
        "url": f"https://clinicaltrials.gov/study/{nct}" if nct else None,
    }


def register(mcp, europepmc, trials) -> None:
    """Attach evidence tools (literature + clinical trials)."""

    @mcp.tool()
    def search_literature(query: str, max_results: int = 10, open_access_only: bool = False) -> dict:
        """Search the biomedical literature via Europe PMC (a PubMed superset).

        Complements `search_articles` (PubMed): Europe PMC returns abstracts inline plus
        open-access / full-text flags, preprints, and citation counts.

        Args:
            query: Search query (e.g. "FBN1 aortic aneurysm", "Marfan syndrome management").
            max_results: Number of results (1-100, default 10).
            open_access_only: If true, restrict to open-access articles.

        Returns:
            Dictionary with total_hits and results (each: id, pmid, doi, title, authors, journal,
            year, open-access/full-text flags, citation count, abstract).
        """
        try:
            if not query.strip():
                return {"error": "Query cannot be empty"}
            max_results = max(1, min(int(max_results), 100))
            q = f"({query}) AND OPEN_ACCESS:Y" if open_access_only else query
            data = europepmc.search(q, page_size=max_results)
            results = (data.get("resultList") or {}).get("result", [])
            return {
                "query": query,
                "total_hits": data.get("hitCount"),
                "returned": len(results),
                "results": [_format_epmc(r) for r in results],
                "source": "Europe PMC",
            }
        except Exception as e:
            return {"error": f"Literature search failed: {e}"}

    @mcp.tool()
    def search_clinical_trials(condition: str, status: str = "", max_results: int = 10) -> dict:
        """Search ClinicalTrials.gov (v2 API) for studies of a condition.

        Args:
            condition: Disease/condition to search (e.g. "Marfan syndrome").
            status: Optional overall-status filter — e.g. "RECRUITING", "COMPLETED",
                "ACTIVE_NOT_RECRUITING", "TERMINATED". Empty = any status.
            max_results: Number of trials (1-50, default 10).

        Returns:
            Dictionary with trials (each: nct_id, title, status, phases, study_type, conditions,
            summary, url).
        """
        try:
            if not condition.strip():
                return {"error": "Condition cannot be empty"}
            max_results = max(1, min(int(max_results), 50))
            data = trials.search(condition=condition, status=(status or None), page_size=max_results)
            studies = data.get("studies", []) or []
            return {
                "condition": condition,
                "status_filter": status or "any",
                "returned": len(studies),
                "trials": [_format_trial(s) for s in studies],
                "source": "ClinicalTrials.gov API v2",
            }
        except Exception as e:
            return {"error": f"Trial search failed: {e}"}
