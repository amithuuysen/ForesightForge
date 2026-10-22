import ipaddress
import socket
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from typing import Callable
from urllib.parse import urljoin, urlsplit, urlunsplit
from uuid import uuid4

import httpx
import trafilatura
from ddgs import DDGS

from .config import settings


SEARCH_TIMEOUT_SECONDS = settings.search.search_timeout_seconds
FETCH_TIMEOUT_SECONDS = settings.search.fetch_timeout_seconds
MAX_QUERIES = settings.search.max_queries
RESULTS_PER_QUERY = settings.search.results_per_query
MAX_SOURCES = settings.search.max_sources
MAX_REDIRECTS = settings.search.max_redirects
MAX_PAGE_BYTES = settings.search.max_page_bytes
MAX_CONTENT_CHARS = settings.search.max_content_chars
USER_AGENT = settings.search.user_agent
SEARCH_RETRIES = settings.search.search_retries
SEARCH_RETRY_DELAY_SECONDS = settings.search.search_retry_delay_seconds
BLOCK_PAGE_MARKERS = (
    "client challenge",
    "checking your browser",
    "enable javascript",
    "access denied",
    "captcha",
    "couldn't load",
    "couldn’t load",
    "could not load",
)


class SearchProviderError(RuntimeError):
    """Raised when all web search query attempts fail."""


def build_search_queries(domain: str, question: str) -> list[tuple[str, str | None]]:
    domain = " ".join(domain.split())
    question = " ".join(question.split())
    candidates = [
        (question, None),
        (f"{domain} latest developments", "y"),
        (f"{domain} evidence data study report", None),
    ]
    queries: list[tuple[str, str | None]] = []
    seen: set[str] = set()
    for query, time_limit in candidates:
        normalized = query.casefold()
        if normalized not in seen:
            seen.add(normalized)
            queries.append((query, time_limit))
    return queries[:MAX_QUERIES]


def _canonical_url(url: str) -> str | None:
    try:
        parts = urlsplit(url.strip())
        if parts.scheme not in {"http", "https"} or not parts.hostname or parts.username or parts.password:
            return None
        default_port = 80 if parts.scheme == "http" else 443
        if parts.port not in {None, default_port}:
            return None
        hostname = parts.hostname.rstrip(".").casefold()
        if hostname in {"localhost", "localhost.localdomain"} or hostname.endswith((".localhost", ".local", ".internal")):
            return None
        netloc = f"[{hostname}]" if ":" in hostname else hostname
        clean = parts._replace(netloc=netloc, fragment="")
        return urlunsplit(clean)
    except ValueError:
        return None


def _is_public_destination(url: str) -> bool:
    canonical = _canonical_url(url)
    if canonical is None:
        return False
    hostname = urlsplit(canonical).hostname
    if hostname is None:
        return False
    try:
        literal = ipaddress.ip_address(hostname)
        return literal.is_global
    except ValueError:
        try:
            addresses = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
        except OSError:
            return False
        resolved = {ipaddress.ip_address(address[4][0]) for address in addresses}
        return bool(resolved) and all(address.is_global for address in resolved)


def _fetch_html(url: str) -> tuple[str, str] | None:
    current_url = _canonical_url(url)
    if current_url is None:
        return None

    timeout = httpx.Timeout(FETCH_TIMEOUT_SECONDS, connect=4.0)
    with httpx.Client(timeout=timeout, headers={"User-Agent": USER_AGENT}, follow_redirects=False) as client:
        for _ in range(MAX_REDIRECTS + 1):
            if not _is_public_destination(current_url):
                return None
            with client.stream("GET", current_url) as response:
                if response.status_code in {301, 302, 303, 307, 308}:
                    location = response.headers.get("location")
                    if not location:
                        return None
                    redirected_url = _canonical_url(urljoin(current_url, location))
                    if redirected_url is None:
                        return None
                    current_url = redirected_url
                    continue

                response.raise_for_status()
                content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().casefold()
                if content_type not in {"text/html", "application/xhtml+xml"}:
                    return None
                content_length = response.headers.get("content-length")
                if content_length and int(content_length) > MAX_PAGE_BYTES:
                    return None

                chunks: list[bytes] = []
                byte_count = 0
                for chunk in response.iter_bytes(chunk_size=16_384):
                    byte_count += len(chunk)
                    if byte_count > MAX_PAGE_BYTES:
                        return None
                    chunks.append(chunk)
                encoding = response.encoding or "utf-8"
                return b"".join(chunks).decode(encoding, errors="replace"), current_url
    return None


def _published_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10]).isoformat()
    except ValueError:
        return None


ProgressCallback = Callable[[dict[str, object]], None]


def _source_from_result(
    result: dict[str, object],
    query: str,
    progress_callback: ProgressCallback | None = None,
) -> dict[str, object] | None:
    raw_url = result.get("href") or result.get("url")
    title = str(result.get("title") or "Untitled source").strip()
    search_snippet = " ".join(str(result.get("body") or result.get("snippet") or "").split())[:1600]
    if not isinstance(raw_url, str):
        return None
    canonical = _canonical_url(raw_url)
    if canonical is None:
        return None

    if progress_callback:
        progress_callback({
            "type": "page_fetch_started",
            "title": title[:300],
            "url": canonical,
            "query": query,
        })

    content = ""
    published_at = None
    publisher = urlsplit(canonical).hostname or ""
    try:
        fetched = _fetch_html(canonical)
    except (httpx.HTTPError, OSError, ValueError):
        fetched = None
    if fetched:
        html, final_url = fetched
        canonical = final_url
        try:
            metadata = trafilatura.extract_metadata(html, default_url=canonical)
            extracted = trafilatura.extract(html, url=canonical, favor_precision=True)
            if metadata.title:
                title = metadata.title.strip()
            if metadata.sitename:
                publisher = metadata.sitename.strip()
            published_at = _published_date(metadata.date)
            content = " ".join((extracted or "").split())[:MAX_CONTENT_CHARS]
            metadata_title = (metadata.title or "").casefold()
            if any(marker in content.casefold() or marker in metadata_title for marker in BLOCK_PAGE_MARKERS):
                content = ""
                published_at = None
                if any(marker in metadata_title for marker in BLOCK_PAGE_MARKERS):
                    title = str(result.get("title") or "Untitled source").strip()
        except (ValueError, TypeError):
            content = ""

    excerpt = content[:1200] if content else search_snippet
    retrieved_at = datetime.now(timezone.utc).isoformat()
    source = {
        "id": str(uuid4()),
        "url": canonical,
        "title": title[:500],
        "excerpt": excerpt,
        "content": content,
        "search_snippet": search_snippet,
        "published_at": published_at,
        "publisher": publisher[:300],
        "query": query,
        "provider": "ddgs",
        "retrieved_at": retrieved_at,
    }
    if progress_callback:
        progress_callback({
            "type": "page_fetch_finished",
            "title": source["title"],
            "url": source["url"],
            "publisher": source["publisher"],
            "query": query,
            "extracted": bool(content),
            "published_at": published_at,
        })
    return source


def search_web(
    domain: str,
    question: str,
    progress_callback: ProgressCallback | None = None,
    queries: list[tuple[str, str | None]] | None = None,
) -> list[dict[str, object]]:
    """Search the public web and fetch the resulting pages.

    ``queries`` overrides the derived query set. Each entry is a query string
    and an optional DDGS time limit. The caller owns the budget: without this
    the function always ran its own three queries, so a caller looping over
    N queries would issue N x 3 searches.
    """
    if queries is None:
        queries = build_search_queries(domain, question)
    query_results: list[tuple[str, list[dict[str, object]]]] = []
    errors: list[str] = []
    successful_queries = 0

    try:
        with DDGS(timeout=SEARCH_TIMEOUT_SECONDS) as search_client:
            for query, time_limit in queries:
                if progress_callback:
                    progress_callback({"type": "search_query_started", "query": query})
                options: dict[str, object] = {"max_results": RESULTS_PER_QUERY, "safesearch": "moderate"}
                if time_limit:
                    options["timelimit"] = time_limit
                # The provider rate-limits bursts. Retry a couple of times with
                # a short backoff before giving up on this query.
                valid_results: list[dict[str, object]] = []
                for attempt in range(SEARCH_RETRIES):
                    try:
                        results = search_client.text(query, **options)
                        valid_results = [result for result in results if isinstance(result, dict)]
                        break
                    except Exception as error:
                        if attempt < SEARCH_RETRIES - 1:
                            if progress_callback:
                                progress_callback(
                                    {
                                        "type": "search_query_retry",
                                        "query": query,
                                        "attempt": attempt + 1,
                                        "error": type(error).__name__,
                                    }
                                )
                            time.sleep(SEARCH_RETRY_DELAY_SECONDS * (attempt + 1))
                        else:
                            errors.append(f"{query}: {type(error).__name__}")
                            if progress_callback:
                                progress_callback(
                                    {
                                        "type": "search_query_failed",
                                        "query": query,
                                        "error": type(error).__name__,
                                    }
                                )
                if valid_results:
                    successful_queries += 1
                    query_results.append((query, valid_results))
                    if progress_callback:
                        progress_callback(
                            {
                                "type": "search_query_finished",
                                "query": query,
                                "result_count": len(valid_results),
                            }
                        )
    except Exception as error:
        errors.append(f"provider: {type(error).__name__}")

    if successful_queries == 0:
        raise SearchProviderError("All web search queries failed: " + "; ".join(errors))

    candidates: list[tuple[dict[str, object], str]] = []
    for result_index in range(RESULTS_PER_QUERY):
        for query, results in query_results:
            if result_index < len(results):
                candidates.append((results[result_index], query))

    unique_candidates: list[tuple[dict[str, object], str]] = []
    seen_urls: set[str] = set()
    for result, query in candidates:
        raw_url = result.get("href") or result.get("url")
        if not isinstance(raw_url, str):
            continue
        canonical = _canonical_url(raw_url)
        if canonical is None or canonical in seen_urls:
            continue
        seen_urls.add(canonical)
        unique_candidates.append((result, query))
        if len(unique_candidates) == MAX_SOURCES:
            break

    with ThreadPoolExecutor(max_workers=settings.search.max_fetch_workers) as executor:
        futures = [executor.submit(_safe_source_from_result, result, query, progress_callback) for result, query in unique_candidates]
        sources = [source for future in futures if (source := future.result()) is not None]

    return sources


def _safe_source_from_result(
    result: dict[str, object],
    query: str,
    progress_callback: ProgressCallback | None = None,
) -> dict[str, object] | None:
    try:
        return _source_from_result(result, query, progress_callback)
    except Exception:
        return None