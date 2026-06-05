# Biomed MCP Server

A Model Context Protocol (MCP) server for biomedical research and **rare & genetic disease** lookup. It began as a PubMed client and is growing into a multi-source health server: search the biomedical literature, and — the headline capability — **search a set of symptoms to find candidate illnesses** (phenotype-driven disease ranking via the Monarch Initiative + Human Phenotype Ontology).

> ⚕️ **Decision-support only.** This server retrieves and ranks information from curated knowledge bases. It is not a diagnostic device and does not replace evaluation by a qualified clinician.

## Features

- **Symptom → Illness**: Map free-text symptoms to standardized HPO terms and rank candidate diseases via Monarch semantic similarity — strongest for rare & genetic disease
- **Disease Cards**: Structured, multi-source disease summaries — description, inheritance, causal genes, phenotypes, cross-references — enriched with Orphanet (rare-disease definitions), MedlinePlus (patient-friendly info), and OMIM (optional, academic key)
- **Genetic Variants**: Clinically-relevant variants for a gene from NCBI ClinVar — the disease → gene → variant chain
- **Clinical Trials**: Search ClinicalTrials.gov (v2 API) by condition and status
- **Literature**: PubMed (search + download) and Europe PMC (full-text-aware, open-access flags, citation counts)
- **Shared Rate Limiting**: One throttle across all NCBI E-utilities databases (PubMed, ClinVar, Gene, MeSH, ...), respecting NCBI's per-key limit
- **Error Handling**: Robust handling of API failures

## Installation

### Quick Setup (Recommended)

1. **Clone or download** this repository
2. **Run the setup script**:
   ```bash
   ./setup.sh
   ```
   This will create a virtual environment, install dependencies, and provide next steps.

### Manual Setup

1. **Clone or download** this repository
2. **Create and activate virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
4. **Configure environment** (optional but recommended):
   ```bash
   cp .env.example .env
   # Edit .env file with your NCBI API key and email
   ```

## Configuration

### Environment Variables

Create a `.env` file with the following optional configuration:

- `NCBI_API_KEY`: Your NCBI API key (increases rate limit from 3 to 10 requests/second)
- `NCBI_EMAIL`: Your email address (recommended by NCBI for API usage tracking)

Get your free NCBI API key at: https://www.ncbi.nlm.nih.gov/account/settings/

## Usage

### Running the Server

1. **Activate the virtual environment** (if not already active):
   ```bash
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Run the server**:
   ```bash
   python server.py
   ```

The server will start and listen for MCP connections via stdio.

3. **To deactivate** the virtual environment when done:
   ```bash
   deactivate
   ```

### Available Tools

#### 1. `search_articles`

Search PubMed for articles matching a query.

**Parameters:**
- `query` (string, required): Search query (e.g., "COVID-19 vaccines", "machine learning AND healthcare")
- `max_results` (int, optional): Maximum results to return (default: 20, max: 200)
- `sort` (string, optional): Sort order - "relevance", "pub_date", or "first_author" (default: "relevance")

**Returns:**
- `pmids`: List of PubMed IDs
- `total_count`: Total number of matching articles
- `query_used`: The search query executed
- `results_returned`: Number of results returned
- `sort_order`: Sort order used

**Example:**
```json
{
  "query": "CRISPR gene editing",
  "max_results": 10,
  "sort": "pub_date"
}
```

#### 2. `download_article`

Download article details by PubMed ID.

**Parameters:**
- `pmid` (string, required): PubMed ID (e.g., "33073741")
- `format_type` (string, optional): Content format - "abstract", "medline", or "full" (default: "abstract")
- `return_mode` (string, optional): Return format - "xml", "text", or "json" (default: "xml")

**Returns:**
- `pmid`: The PubMed ID
- `content`: Article content in requested format
- `format_type`: Format type used
- `return_mode`: Return mode used
- `content_length`: Length of content

#### 3. `download_articles_batch`

Download multiple articles in a single request.

**Parameters:**
- `pmids` (list, required): List of PubMed IDs
- `format_type` (string, optional): Content format (default: "abstract")
- `return_mode` (string, optional): Return format (default: "xml")

**Returns:**
- `pmids`: List of requested PMIDs
- `content`: Combined article content
- `article_count`: Number of articles requested
- `content_length`: Length of content

#### 4. `get_article_summaries`

Get document summaries for articles (metadata without full content).

**Parameters:**
- `pmids` (list, required): List of PubMed IDs

**Returns:**
- `pmids`: List of requested PMIDs
- `summaries`: XML summary data
- `article_count`: Number of articles requested

### Symptom → Disease Tools

#### 5. `find_conditions_by_symptoms`

Rank candidate diseases by how well they match a set of symptoms (the headline tool). Best for rare & genetic disease.

**Parameters:**
- `symptoms` (list, required): Free-text symptoms (e.g. `["arachnodactyly", "ectopia lentis", "tall stature"]`) or HPO codes (e.g. `"HP:0001166"`)
- `max_results` (int, optional): Candidate conditions to return, 1–50 (default: 10)
- `metric` (string, optional): `ancestor_information_content` (default), `jaccard_similarity`, or `phenodigm_score`

**Returns:** `ranked_conditions` (each with MONDO id, name, score, cross_references, description), `hpo_terms_used`, `symptom_mapping`, and a disclaimer.

#### 6. `get_disease_info`

Get a structured summary for a disease by ontology ID.

**Parameters:**
- `disease_id` (string, required): A disease CURIE, preferably MONDO (e.g. `"MONDO:0007947"`). OMIM/Orphanet IDs also resolve where Monarch has a mapping.

**Returns:** name, description, inheritance, `causal_genes`, characteristic `phenotypes`, `cross_references` (OMIM/Orphanet/ICD/...), and `association_counts`.

#### 7. `lookup_hpo_terms`

Map free-text symptoms to standardized HPO terms — useful to inspect or disambiguate before ranking.

**Parameters:**
- `symptoms` (list, required): Free-text symptom descriptions or HP: codes

**Returns:** `hpo_terms` (chosen HP: codes), a per-symptom `mapping` (with alternatives), and `count`.

**Example:**
```json
{
  "symptoms": ["seizures", "intellectual disability", "ataxia"],
  "max_results": 10
}
```

### Evidence Tools

#### 8. `search_literature`

Search the biomedical literature via Europe PMC (a PubMed superset with abstracts inline, open-access/full-text flags, preprints, and citation counts).

**Parameters:**
- `query` (string, required): Search query (e.g. `"FBN1 aortic aneurysm"`)
- `max_results` (int, optional): 1–100 (default: 10)
- `open_access_only` (bool, optional): Restrict to open-access articles (default: false)

**Returns:** `total_hits` and `results` (each: id, pmid, doi, title, authors, journal, year, open-access/full-text flags, citation count, abstract).

#### 9. `search_clinical_trials`

Search ClinicalTrials.gov (v2 API) for studies of a condition.

**Parameters:**
- `condition` (string, required): Disease/condition (e.g. `"Marfan syndrome"`)
- `status` (string, optional): Overall-status filter — `RECRUITING`, `COMPLETED`, `ACTIVE_NOT_RECRUITING`, `TERMINATED`, ... (default: any)
- `max_results` (int, optional): 1–50 (default: 10)

**Returns:** `trials` (each: nct_id, title, status, phases, study_type, conditions, summary, url).

### Genetics Tools

#### 10. `find_genetic_variants`

Find clinically-relevant variants for a gene from NCBI ClinVar. Pairs with `get_disease_info` to complete the **symptom → disease → gene → variant** chain.

**Parameters:**
- `gene` (string, required): Gene symbol (e.g. `"FBN1"`)
- `clinical_significance` (string, optional): `pathogenic` (default), `likely pathogenic`, `benign`, `likely benign`, `uncertain significance`, or `any`
- `max_results` (int, optional): 1–50 (default: 15)

**Returns:** `total_matches` and `variants` (each: accession, name/HGVS, type, gene, clinical_significance, review_status, protein_change, conditions, location).

## Search Query Examples

### Basic Searches
- `"COVID-19"` - Search for COVID-19 articles
- `"machine learning"` - Search for machine learning articles
- `"breast cancer"` - Search for breast cancer articles

### Advanced Searches
- `"COVID-19 AND vaccine"` - Articles about COVID-19 vaccines
- `"machine learning AND healthcare"` - ML in healthcare
- `"CRISPR[Title]"` - CRISPR in article titles only
- `"Nature[Journal]"` - Articles from Nature journal
- `"2023[PDAT]"` - Articles published in 2023
- `"Smith J[Author]"` - Articles by author "Smith J"

### Field-Specific Searches
- `[Title]` - Search in title only
- `[Author]` - Search by author
- `[Journal]` - Search by journal name
- `[PDAT]` - Search by publication date
- `[MeSH]` - Search MeSH terms

## Integration

This server speaks MCP over stdio and works with any MCP client.

### Claude Code (CLI)

```bash
# Use absolute paths to the venv Python and server.py
claude mcp add biomed -- /path/to/pubmed-mcp/venv/bin/python /path/to/pubmed-mcp/server.py
```

Add `--scope user` to make it available across all your projects (the default scope is this project only). Verify with `claude mcp list`, then start a new Claude Code session to load the tools. Optional keys (e.g. `NCBI_API_KEY`, `OMIM_API_KEY`) are read from a `.env` file next to `server.py`, or pass them with `--env KEY=value`.

### Claude Desktop

### Option 1: Using .env file (Recommended)

If you configured your API key in the `.env` file during installation:

```json
{
  "mcpServers": {
    "biomed": {
      "command": "/path/to/pubmed-mcp/venv/bin/python",
      "args": ["/path/to/pubmed-mcp/server.py"]
    }
  }
}
```

### Option 2: Configure in Claude Desktop

Alternatively, you can specify the API key directly in the Claude Desktop configuration:

```json
{
  "mcpServers": {
    "biomed": {
      "command": "/path/to/pubmed-mcp/venv/bin/python",
      "args": ["/path/to/pubmed-mcp/server.py"],
      "env": {
        "NCBI_API_KEY": "your_api_key_here",
        "NCBI_EMAIL": "your_email@example.com"
      }
    }
  }
}
```

**Recommendation**: Use Option 1 (.env file) for better security and easier management.

**Note**: Make sure to use the full path to the Python executable in the virtual environment (`venv/bin/python`) to ensure the correct dependencies are available.

## Rate Limits

- **Without API key**: 3 requests per second
- **With API key**: 10 requests per second
- **Batch size limit**: 50 articles per batch request

## Error Handling

The server provides comprehensive error handling:
- Invalid PMIDs are automatically cleaned (non-numeric characters removed)
- Empty queries return descriptive errors
- API failures are caught and reported
- Rate limiting prevents API abuse

## Development

### Project Structure
```
pubmed-mcp/
├── server.py                   # MCP server: builds shared clients, registers tools
├── clients/                    # One HTTP client per data source
│   ├── base.py                 #   shared session, rate limiting, retries
│   ├── ncbi_client.py          #   NCBI E-utilities via db= (PubMed/ClinVar/Gene/MeSH/...)
│   ├── monarch_client.py       #   Monarch Initiative v3 (phenotype→disease semsim, entity)
│   ├── hpo_client.py           #   HPO term autocomplete (symptom → HP: code)
│   ├── orphanet_client.py      #   Orphanet rare-disease definitions (api.orphacode.org)
│   ├── medlineplus_client.py   #   MedlinePlus Connect (patient-friendly info by ICD-10-CM)
│   ├── europepmc_client.py     #   Europe PMC literature search
│   ├── clinicaltrials_client.py#   ClinicalTrials.gov v2
│   └── omim_client.py          #   OMIM (optional; needs OMIM_API_KEY)
├── tools/                      # Task-oriented MCP tools, grouped by capability
│   ├── literature.py           #   PubMed search / download
│   ├── evidence.py             #   Europe PMC literature + clinical trials
│   ├── genetics.py             #   ClinVar variants
│   └── conditions.py           #   symptom→disease, enriched disease info, HPO lookup
├── test_smoke.py               # Live smoke test (venv/bin/python test_smoke.py)
├── TODO.md                     # Build roadmap
├── requirements.txt            # Python dependencies
├── setup.sh                    # Automated setup script
├── README.md                   # This file
├── .env.example                # Environment variables template
└── venv/                       # Virtual environment (created by setup)
```

### Dependencies
- `mcp[cli]` - MCP Python SDK
- `requests` - HTTP client for PubMed API
- `python-dotenv` - Environment variables
- `typing-extensions` - Type hints support

## License

This project is open source. Please check PubMed's terms of service for API usage guidelines.

## Support

For issues with this MCP server, please check:
1. Your API key and email configuration
2. Network connectivity to NCBI servers
3. Rate limiting compliance
4. Valid PMID formats

For PubMed API documentation, visit: https://www.ncbi.nlm.nih.gov/books/NBK25500/