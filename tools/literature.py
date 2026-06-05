"""Literature tools — PubMed search and retrieval via NCBI E-utilities.

These preserve the original PubMed server's tool surface, now backed by the generalized
``NCBIClient`` (db='pubmed').
"""

from typing import List

_VALID_FORMATS = ("abstract", "medline", "full")
_VALID_MODES = ("xml", "text", "json")
_VALID_SORTS = ("relevance", "pub_date", "first_author")


def _clean_pmids(pmids: List[str]) -> List[str]:
    cleaned = []
    for pmid in pmids:
        digits = "".join(filter(str.isdigit, str(pmid)))
        if digits:
            cleaned.append(digits)
    return cleaned


def register(mcp, ncbi) -> None:
    """Attach literature tools to the MCP server."""

    @mcp.tool()
    def search_articles(query: str, max_results: int = 20, sort: str = "relevance") -> dict:
        """Search PubMed for articles matching the query.

        Args:
            query: Search query string (e.g., "COVID-19 vaccines", "BRCA1 AND breast cancer").
            max_results: Maximum number of results to return (default: 20, max: 200).
            sort: Sort order - "relevance", "pub_date", or "first_author" (default: "relevance").

        Returns:
            Dictionary with pmids, total_count, query_used, results_returned, and sort_order.
        """
        try:
            if not query.strip():
                return {"error": "Query cannot be empty"}
            max_results = min(max(max_results, 1), 200)
            if sort not in _VALID_SORTS:
                sort = "relevance"
            results = ncbi.search("pubmed", query, retmax=max_results, sort=sort)
            return {
                "pmids": results["ids"],
                "total_count": results["total_count"],
                "query_used": query,
                "results_returned": len(results["ids"]),
                "sort_order": sort,
            }
        except Exception as e:
            return {"error": f"Search failed: {e}"}

    @mcp.tool()
    def download_article(
        pmid: str, format_type: str = "abstract", return_mode: str = "xml"
    ) -> dict:
        """Download article details by PubMed ID.

        Args:
            pmid: PubMed ID (e.g., "33073741").
            format_type: "abstract", "medline", or "full" (default: "abstract").
            return_mode: "xml", "text", or "json" (default: "xml").

        Returns:
            Dictionary with pmid, content, format_type, return_mode, and content_length.
        """
        try:
            if not pmid.strip():
                return {"error": "PMID cannot be empty"}
            pmid_clean = "".join(filter(str.isdigit, pmid))
            if not pmid_clean:
                return {"error": "PMID must contain numeric characters"}
            if format_type not in _VALID_FORMATS:
                format_type = "abstract"
            if return_mode not in _VALID_MODES:
                return_mode = "xml"
            content = ncbi.efetch(
                "pubmed", pmid_clean, rettype=format_type, retmode=return_mode
            )
            return {
                "pmid": pmid_clean,
                "content": content,
                "format_type": format_type,
                "return_mode": return_mode,
                "content_length": len(content),
            }
        except Exception as e:
            return {"error": f"Download failed: {e}"}

    @mcp.tool()
    def download_articles_batch(
        pmids: List[str], format_type: str = "abstract", return_mode: str = "xml"
    ) -> dict:
        """Download multiple articles by PubMed IDs in a single request (max 50).

        Args:
            pmids: List of PubMed IDs (e.g., ["33073741", "33073726"]).
            format_type: "abstract", "medline", or "full" (default: "abstract").
            return_mode: "xml", "text", or "json" (default: "xml").

        Returns:
            Dictionary with pmids, content, format_type, return_mode, article_count, content_length.
        """
        try:
            if not pmids:
                return {"error": "PMIDs list cannot be empty"}
            pmids_clean = _clean_pmids(pmids)
            if not pmids_clean:
                return {"error": "No valid PMIDs provided"}
            if len(pmids_clean) > 50:
                pmids_clean = pmids_clean[:50]
            if format_type not in _VALID_FORMATS:
                format_type = "abstract"
            if return_mode not in _VALID_MODES:
                return_mode = "xml"
            content = ncbi.efetch(
                "pubmed", pmids_clean, rettype=format_type, retmode=return_mode
            )
            return {
                "pmids": pmids_clean,
                "content": content,
                "format_type": format_type,
                "return_mode": return_mode,
                "article_count": len(pmids_clean),
                "content_length": len(content),
            }
        except Exception as e:
            return {"error": f"Batch download failed: {e}"}

    @mcp.tool()
    def get_article_summaries(pmids: List[str]) -> dict:
        """Get document summaries for articles (metadata without full content; max 50).

        Args:
            pmids: List of PubMed IDs (e.g., ["33073741", "33073726"]).

        Returns:
            Dictionary with pmids, summaries (XML), article_count, and content_length.
        """
        try:
            if not pmids:
                return {"error": "PMIDs list cannot be empty"}
            pmids_clean = _clean_pmids(pmids)
            if not pmids_clean:
                return {"error": "No valid PMIDs provided"}
            if len(pmids_clean) > 50:
                pmids_clean = pmids_clean[:50]
            summaries = ncbi.esummary("pubmed", pmids_clean, retmode="xml")
            return {
                "pmids": pmids_clean,
                "summaries": summaries,
                "article_count": len(pmids_clean),
                "content_length": len(summaries),
            }
        except Exception as e:
            return {"error": f"Summary retrieval failed: {e}"}
