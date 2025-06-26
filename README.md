# PubMed MCP Server

A Model Context Protocol (MCP) server that provides access to PubMed's E-utilities API for searching and downloading scientific articles. This server enables LLM applications to search PubMed's vast database of biomedical literature and retrieve article metadata, abstracts, and full content.

## Features

- **Article Search**: Search PubMed database with flexible query terms
- **Article Download**: Retrieve full article metadata, abstracts, and available content  
- **Batch Operations**: Download multiple articles in a single request
- **Article Summaries**: Get document summaries with metadata
- **Multiple Formats**: Support for XML, JSON, and text output formats
- **Rate Limiting**: Automatic rate limiting to respect PubMed API limits
- **Error Handling**: Robust error handling for API failures

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

## Integration with Claude Desktop

### Option 1: Using .env file (Recommended)

If you configured your API key in the `.env` file during installation:

```json
{
  "mcpServers": {
    "pubmed": {
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
    "pubmed": {
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
├── server.py              # Main MCP server implementation
├── pubmed_client.py       # PubMed API client wrapper
├── requirements.txt       # Python dependencies
├── setup.sh              # Automated setup script
├── .gitignore            # Git ignore file
├── README.md             # This file
├── .env.example          # Environment variables template
└── venv/                 # Virtual environment (created by setup)
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