"""Shared HTTP client base.

Provides a persistent ``requests`` session with simple per-client rate limiting
(a minimum interval between requests), light retry/backoff on transient errors,
and JSON/text helpers. Each source client subclasses this.
"""

import time
from typing import Any, Dict, Optional

import requests

DEFAULT_TIMEOUT = 25
DEFAULT_USER_AGENT = "biomed-mcp/0.2 (Model Context Protocol server for biomedical research)"
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class UpstreamError(RuntimeError):
    """An upstream API call failed after exhausting retries (library-agnostic)."""


class UpstreamTimeout(UpstreamError):
    """The upstream API did not respond within the timeout (after retries)."""


class UpstreamUnavailable(UpstreamError):
    """The upstream API could not be reached — DNS/connection error (after retries)."""


class BaseHTTPClient:
    """Minimal HTTP wrapper with throttling and retries."""

    def __init__(
        self,
        base_url: str,
        *,
        min_interval: float = 0.0,
        default_params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = 2,
    ):
        self.base_url = base_url.rstrip("/")
        self.min_interval = min_interval
        self.default_params = dict(default_params or {})
        self.timeout = timeout
        self.max_retries = max_retries
        self._last_request = 0.0
        self.session = requests.Session()
        self.session.headers["User-Agent"] = DEFAULT_USER_AGENT
        if headers:
            self.session.headers.update(headers)

    def _throttle(self) -> None:
        if self.min_interval <= 0:
            return
        elapsed = time.monotonic() - self._last_request
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)

    def _url(self, path: str) -> str:
        if not path:
            return self.base_url
        if path.startswith("http://") or path.startswith("https://"):
            return path
        return f"{self.base_url}/{path.lstrip('/')}"

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Any] = None,
        timeout: Optional[float] = None,
        retries: Optional[int] = None,
    ) -> requests.Response:
        """Issue a request with throttling + retries.

        ``timeout`` and ``retries`` override this client's defaults for a single call —
        useful for compute-heavy endpoints (e.g. Monarch semsim) that need a longer budget
        without slowing down the lightweight calls.
        """
        merged = dict(self.default_params)
        if params:
            merged.update({k: v for k, v in params.items() if v is not None})
        url = self._url(path)
        eff_timeout = self.timeout if timeout is None else timeout
        eff_retries = self.max_retries if retries is None else max(0, retries)

        for attempt in range(eff_retries + 1):
            self._throttle()
            try:
                resp = self.session.request(
                    method, url, params=merged, json=json_body, timeout=eff_timeout
                )
                self._last_request = time.monotonic()
            except requests.RequestException as exc:
                self._last_request = time.monotonic()
                if attempt < eff_retries:
                    time.sleep(0.5 * (2 ** attempt))
                    continue
                # Out of retries: surface a clean, library-agnostic error so tools can
                # report "temporarily unavailable" instead of a raw urllib3 traceback.
                if isinstance(exc, requests.exceptions.Timeout):
                    raise UpstreamTimeout(
                        f"{self.base_url} did not respond within {eff_timeout:g}s "
                        f"(after {eff_retries + 1} attempt(s))."
                    ) from exc
                if isinstance(exc, requests.exceptions.ConnectionError):
                    raise UpstreamUnavailable(
                        f"could not connect to {self.base_url} — network/DNS error "
                        f"(after {eff_retries + 1} attempt(s))."
                    ) from exc
                raise

            # Retry only transient server/throttle statuses; let 4xx surface immediately.
            if resp.status_code in _RETRYABLE_STATUS and attempt < eff_retries:
                time.sleep(0.5 * (2 ** attempt))
                continue
            resp.raise_for_status()
            return resp

        # Unreachable, but keeps type checkers happy.
        raise RuntimeError("request retry loop exhausted")

    def get(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        *,
        timeout: Optional[float] = None,
        retries: Optional[int] = None,
    ) -> requests.Response:
        return self.request("GET", path, params=params, timeout=timeout, retries=retries)

    def get_json(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        *,
        timeout: Optional[float] = None,
        retries: Optional[int] = None,
    ) -> Any:
        return self.get(path, params=params, timeout=timeout, retries=retries).json()

    def get_text(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        *,
        timeout: Optional[float] = None,
        retries: Optional[int] = None,
    ) -> str:
        return self.get(path, params=params, timeout=timeout, retries=retries).text

    def post_json(
        self,
        path: str,
        json_body: Any,
        params: Optional[Dict[str, Any]] = None,
        *,
        timeout: Optional[float] = None,
        retries: Optional[int] = None,
    ) -> Any:
        return self.request(
            "POST", path, params=params, json_body=json_body, timeout=timeout, retries=retries
        ).json()
