"""
PubMed MCP Server
Provides article search and download functionality through Model Context Protocol.
"""

import os
from typing import List, Optional
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from pubmed_client import PubMedClient

# Load environment variables
load_dotenv()

# Initialize MCP server
mcp = FastMCP("PubMed")

# Initialize PubMed client
pubmed_client = PubMedClient(
    api_key=os.getenv('NCBI_API_KEY'),
    email=os.getenv('NCBI_EMAIL')
)


@mcp.tool()
def search_articles(
    query: str, 
    max_results: int = 20, 
    sort: str = "relevance"
) -> dict:
    """
    Search PubMed for articles matching the query.
    
    Args:
        query: Search query string (e.g., "COVID-19 vaccines", "machine learning AND healthcare")
        max_results: Maximum number of results to return (default: 20, max: 200)
        sort: Sort order - "relevance", "pub_date", or "first_author" (default: "relevance")
    
    Returns:
        Dictionary containing:
        - pmids: List of PubMed IDs
        - total_count: Total number of matching articles
        - query_used: The search query that was executed
    """
    try:
        # Validate inputs
        if not query.strip():
            return {"error": "Query cannot be empty"}
        
        if max_results < 1 or max_results > 200:
            max_results = min(max(max_results, 1), 200)
        
        if sort not in ["relevance", "pub_date", "first_author"]:
            sort = "relevance"
        
        # Perform search
        results = pubmed_client.search_articles(
            query=query,
            max_results=max_results,
            sort=sort
        )
        
        return {
            "pmids": results["pmids"],
            "total_count": results["total_count"],
            "query_used": query,
            "results_returned": len(results["pmids"]),
            "sort_order": sort
        }
        
    except Exception as e:
        return {"error": f"Search failed: {str(e)}"}


@mcp.tool()
def download_article(
    pmid: str, 
    format_type: str = "abstract", 
    return_mode: str = "xml"
) -> dict:
    """
    Download article details by PubMed ID.
    
    Args:
        pmid: PubMed ID (e.g., "33073741")
        format_type: Content format - "abstract", "medline", or "full" (default: "abstract")
        return_mode: Return format - "xml", "text", or "json" (default: "xml")
    
    Returns:
        Dictionary containing:
        - pmid: The PubMed ID
        - content: Article content in requested format
        - format_type: Format type used
        - return_mode: Return mode used
    """
    try:
        # Validate inputs
        if not pmid.strip():
            return {"error": "PMID cannot be empty"}
        
        # Clean PMID (remove any non-numeric characters)
        pmid_clean = ''.join(filter(str.isdigit, pmid))
        if not pmid_clean:
            return {"error": "PMID must contain numeric characters"}
        
        if format_type not in ["abstract", "medline", "full"]:
            format_type = "abstract"
        
        if return_mode not in ["xml", "text", "json"]:
            return_mode = "xml"
        
        # Fetch article
        content = pubmed_client.fetch_article(
            pmid=pmid_clean,
            rettype=format_type,
            retmode=return_mode
        )
        
        return {
            "pmid": pmid_clean,
            "content": content,
            "format_type": format_type,
            "return_mode": return_mode,
            "content_length": len(content)
        }
        
    except Exception as e:
        return {"error": f"Download failed: {str(e)}"}


@mcp.tool()
def download_articles_batch(
    pmids: List[str], 
    format_type: str = "abstract", 
    return_mode: str = "xml"
) -> dict:
    """
    Download multiple articles by PubMed IDs in a single request.
    
    Args:
        pmids: List of PubMed IDs (e.g., ["33073741", "33073726"])
        format_type: Content format - "abstract", "medline", or "full" (default: "abstract")
        return_mode: Return format - "xml", "text", or "json" (default: "xml")
    
    Returns:
        Dictionary containing:
        - pmids: List of requested PMIDs
        - content: Combined article content
        - format_type: Format type used
        - return_mode: Return mode used
        - article_count: Number of articles requested
    """
    try:
        # Validate inputs
        if not pmids or len(pmids) == 0:
            return {"error": "PMIDs list cannot be empty"}
        
        # Clean PMIDs
        pmids_clean = []
        for pmid in pmids:
            pmid_clean = ''.join(filter(str.isdigit, str(pmid)))
            if pmid_clean:
                pmids_clean.append(pmid_clean)
        
        if not pmids_clean:
            return {"error": "No valid PMIDs provided"}
        
        # Limit batch size to prevent timeout
        if len(pmids_clean) > 50:
            pmids_clean = pmids_clean[:50]
        
        if format_type not in ["abstract", "medline", "full"]:
            format_type = "abstract"
        
        if return_mode not in ["xml", "text", "json"]:
            return_mode = "xml"
        
        # Fetch articles
        content = pubmed_client.fetch_articles_batch(
            pmids=pmids_clean,
            rettype=format_type,
            retmode=return_mode
        )
        
        return {
            "pmids": pmids_clean,
            "content": content,
            "format_type": format_type,
            "return_mode": return_mode,
            "article_count": len(pmids_clean),
            "content_length": len(content)
        }
        
    except Exception as e:
        return {"error": f"Batch download failed: {str(e)}"}


@mcp.tool()
def get_article_summaries(pmids: List[str]) -> dict:
    """
    Get document summaries for articles (metadata without full content).
    
    Args:
        pmids: List of PubMed IDs (e.g., ["33073741", "33073726"])
    
    Returns:
        Dictionary containing:
        - pmids: List of requested PMIDs
        - summaries: XML summary data
        - article_count: Number of articles requested
    """
    try:
        # Validate inputs
        if not pmids or len(pmids) == 0:
            return {"error": "PMIDs list cannot be empty"}
        
        # Clean PMIDs
        pmids_clean = []
        for pmid in pmids:
            pmid_clean = ''.join(filter(str.isdigit, str(pmid)))
            if pmid_clean:
                pmids_clean.append(pmid_clean)
        
        if not pmids_clean:
            return {"error": "No valid PMIDs provided"}
        
        # Limit batch size
        if len(pmids_clean) > 50:
            pmids_clean = pmids_clean[:50]
        
        # Get summaries
        summaries = pubmed_client.get_article_summary(pmids_clean)
        
        return {
            "pmids": pmids_clean,
            "summaries": summaries,
            "article_count": len(pmids_clean),
            "content_length": len(summaries)
        }
        
    except Exception as e:
        return {"error": f"Summary retrieval failed: {str(e)}"}


if __name__ == "__main__":
    mcp.run()