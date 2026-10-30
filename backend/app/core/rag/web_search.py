"""Live Web Search & Full-Article Extraction Engine for RAG Knowledge Expansion.

Queries authoritative online publications (VnExpress, CafeF, VietnamNet, Dân Trí...) via DuckDuckGo
and fetches full article/PDF content for on-the-fly Recursive Chunking without external scraping dependencies.
Uses Python's built-in html.parser for speed, portability, and zero-dependency reliability.
"""

from __future__ import annotations

import html as html_lib
import io
import logging
import re
import time
import urllib.parse
from html.parser import HTMLParser
from typing import NotRequired, TypedDict

import httpx

logger = logging.getLogger(__name__)


class WebSearchResult(TypedDict):
    title: str
    snippet: str
    source_name: str
    source_url: str
    content: NotRequired[str]


_SEARCH_CACHE: dict[str, tuple[float, list[WebSearchResult]]] = {}
_ARTICLE_CACHE: dict[str, tuple[float, str]] = {}
_CACHE_TTL = 300.0  # 5 minutes cache

_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
}

_NOISE_PATTERNS = (
    "bản quyền thuộc",
    "all rights reserved",
    "đăng ký nhận bản tin",
    "chia sẻ bài viết",
    "vui lòng bật javascript",
    "chính sách bảo mật",
    "điều khoản sử dụng",
    "quảng cáo liên hệ",
)


def _clean_domain_name(url: str) -> str:
    """Extract a friendly publisher name from URL domain."""
    try:
        if not url.startswith("http"):
            url = f"https://{url}"
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        domain_map = {
            "vnexpress.net": "VnExpress",
            "cafef.vn": "CafeF",
            "vietnamnet.vn": "VietnamNet",
            "tuoitre.vn": "Báo Tuổi Trẻ",
            "thanhnien.vn": "Báo Thanh Niên",
            "dantri.com.vn": "Dân Trí",
            "thuvienphapluat.vn": "Thư Viện Pháp Luật",
            "forbes.vn": "Forbes Vietnam",
            "vneconomy.vn": "VnEconomy",
            "timo.vn": "Timo Digital Bank",
            "homecredit.vn": "Home Credit",
            "dnse.com.vn": "Chứng khoán DNSE",
            "zalopay.vn": "ZaloPay",
            "momo.vn": "MoMo",
            "vib.com.vn": "Ngân hàng VIB",
            "techcombank.com": "Techcombank",
            "acb.com.vn": "Ngân hàng ACB",
            "prudential.com.vn": "Prudential",
            "aia.com.vn": "AIA Vietnam",
            "luatvietnam.vn": "Luật Việt Nam",
        }
        for k, v in domain_map.items():
            if k in domain:
                return v
        return domain.capitalize()
    except Exception:
        return "Báo chí tài chính"


class DuckDuckGoHTMLParser(HTMLParser):
    """Zero-dependency parser for DuckDuckGo HTML search results using Python standard library."""

    def __init__(self):
        super().__init__()
        self.results: list[dict[str, str]] = []
        self._current: dict[str, str] = {}
        self._in_title = False
        self._in_snippet = False
        self._buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
        attrs_map = {k: v or "" for k, v in attrs}
        classes = attrs_map.get("class", "").split()

        if "result__a" in classes:
            self._in_title = True
            self._buffer = []
            if "href" in attrs_map:
                self._current["href"] = attrs_map["href"]
        elif any("result__snippet" in c for c in classes):
            self._in_snippet = True
            self._buffer = []
            if "href" in attrs_map and "href" not in self._current:
                self._current["href"] = attrs_map["href"]

    def handle_endtag(self, tag: str):
        text = html_lib.unescape("".join(self._buffer)).strip()
        if self._in_title and tag == "a":
            self._current["title"] = text
            self._in_title = False
        elif self._in_snippet and tag in ("a", "span", "div"):
            self._current["snippet"] = text
            self._in_snippet = False
            if "title" in self._current and "snippet" in self._current:
                self.results.append(dict(self._current))
                self._current = {}

    def handle_data(self, data: str):
        if self._in_title or self._in_snippet:
            self._buffer.append(data)


class ArticleContentHTMLParser(HTMLParser):
    """Extracts clean readable article paragraphs and headings from raw HTML pages."""

    _IGNORED_TAGS = {
        "script",
        "style",
        "nav",
        "header",
        "footer",
        "aside",
        "noscript",
        "form",
        "svg",
        "button",
        "iframe",
        "select",
        "option",
    }
    _BLOCK_TAGS = {"h1", "h2", "h3", "h4", "p", "li", "blockquote"}

    def __init__(self):
        super().__init__()
        self.blocks: list[str] = []
        self._ignored_depth = 0
        self._active_block_tag: str | None = None
        self._buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
        tag_l = tag.lower()
        if tag_l in self._IGNORED_TAGS:
            self._ignored_depth += 1
            return
        if self._ignored_depth == 0 and tag_l in self._BLOCK_TAGS:
            self._active_block_tag = tag_l
            self._buffer = []

    def handle_endtag(self, tag: str):
        tag_l = tag.lower()
        if tag_l in self._IGNORED_TAGS and self._ignored_depth > 0:
            self._ignored_depth -= 1
            return
        if self._ignored_depth == 0 and tag_l == self._active_block_tag:
            raw = html_lib.unescape(" ".join("".join(self._buffer).split())).strip()
            self._active_block_tag = None
            self._buffer = []
            if not raw:
                return

            lower_raw = raw.lower()
            if any(pat in lower_raw for pat in _NOISE_PATTERNS):
                return

            if tag_l in ("h1", "h2", "h3") and len(raw) >= 8:
                prefix = "# " if tag_l == "h1" else "## "
                formatted = f"{prefix}{raw}"
                if formatted not in self.blocks:
                    self.blocks.append(formatted)
            elif len(raw) >= 35:
                prefix = "- " if tag_l == "li" and not raw.startswith("-") else ""
                formatted = f"{prefix}{raw}"
                if formatted not in self.blocks:
                    self.blocks.append(formatted)

    def handle_data(self, data: str):
        if self._ignored_depth == 0 and self._active_block_tag is not None:
            self._buffer.append(data)


def fetch_url_full_text(url: str, timeout: float = 3.0, max_chars: int = 8000) -> str:
    """Fetch an online article or PDF URL and extract its raw readable text for chunking."""
    if not url or not url.startswith("http"):
        return ""

    now = time.time()
    if url in _ARTICLE_CACHE:
        cached_time, cached_text = _ARTICLE_CACHE[url]
        if now - cached_time < _CACHE_TTL:
            return cached_text

    extracted = ""
    try:
        with httpx.Client(headers=_DEFAULT_HEADERS, timeout=timeout, follow_redirects=True) as client:
            resp = client.get(url)
            if resp.status_code != 200:
                _ARTICLE_CACHE[url] = (now, "")
                return ""

            content_type = resp.headers.get("content-type", "").lower()
            if "application/pdf" in content_type or url.lower().endswith(".pdf"):
                import pypdf

                reader = pypdf.PdfReader(io.BytesIO(resp.content))
                pages = []
                for page in reader.pages[:10]:
                    t = page.extract_text()
                    if t:
                        pages.append(t.strip())
                extracted = "\n\n".join(pages)[:max_chars].strip()
            else:
                parser = ArticleContentHTMLParser()
                parser.feed(resp.text)
                extracted = "\n\n".join(parser.blocks)[:max_chars].strip()
                # Normalize multiple spaces
                extracted = re.sub(r"[ \t]{2,}", " ", extracted)
    except Exception as e:
        logger.debug("Could not fetch full text from %s: %s", url, e)

    _ARTICLE_CACHE[url] = (now, extracted)
    return extracted


def search_online_financial_knowledge(
    query: str,
    max_results: int = 3,
    fetch_full_content: bool = True,
) -> list[WebSearchResult]:
    """Search online for financial articles and optionally fetch full raw article text for chunking."""
    cleaned_query = query.strip()
    if not cleaned_query or len(cleaned_query) < 3:
        return []

    cache_key = f"{cleaned_query.lower()}::{int(fetch_full_content)}"
    now = time.time()
    if cache_key in _SEARCH_CACHE:
        cached_time, cached_results = _SEARCH_CACHE[cache_key]
        if now - cached_time < _CACHE_TTL:
            return cached_results

    search_term = f"{cleaned_query} tài chính cá nhân chi tiêu"
    results: list[WebSearchResult] = []

    try:
        with httpx.Client(headers=_DEFAULT_HEADERS, timeout=5.0, follow_redirects=True) as client:
            resp = client.post(
                "https://html.duckduckgo.com/html/",
                data={"q": search_term},
            )
            if resp.status_code == 200:
                parser = DuckDuckGoHTMLParser()
                parser.feed(resp.text)

                for item in parser.results:
                    raw_title = item.get("title", "")
                    raw_snippet = item.get("snippet", "")
                    raw_href = item.get("href", "")

                    if not raw_title or not raw_snippet:
                        continue

                    raw_url = raw_href
                    if "uddg=" in raw_href:
                        parsed_qs = urllib.parse.parse_qs(urllib.parse.urlparse(raw_href).query)
                        raw_url = parsed_qs.get("uddg", [raw_href])[0]

                    if not raw_url.startswith("http"):
                        raw_url = f"https://{raw_url}" if raw_url else ""

                    if not raw_url or len(raw_snippet) < 15:
                        continue

                    source_name = _clean_domain_name(raw_url)
                    full_content = raw_snippet
                    if fetch_full_content and len(results) < 2:
                        article_body = fetch_url_full_text(raw_url, timeout=2.5)
                        if len(article_body) >= 200:
                            full_content = f"{raw_snippet}\n\n{article_body}"

                    results.append({
                        "title": raw_title,
                        "snippet": raw_snippet,
                        "content": full_content,
                        "source_name": source_name,
                        "source_url": raw_url,
                    })

                    if len(results) >= max_results:
                        break
    except Exception as e:
        logger.warning("Online web search failed (offline or network timeout): %s", e)

    _SEARCH_CACHE[cache_key] = (now, results)
    return results
