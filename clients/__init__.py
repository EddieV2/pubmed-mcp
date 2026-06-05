"""HTTP client modules — one per upstream data source.

Each client wraps a single biomedical API behind a small, typed surface. They share
``BaseHTTPClient`` for rate limiting, retries, and JSON/text helpers.
"""
