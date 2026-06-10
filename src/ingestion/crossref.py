from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path

import requests

from core.config import Settings
from core.utils import ensure_parent, normalize_whitespace, write_json


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def _safe_str(value) -> str:
    if isinstance(value, list):
        return normalize_whitespace(" ".join(str(v) for v in value))
    return normalize_whitespace(str(value)) if value else ""


def _parse_date(item: dict, key: str) -> str:
    """Extract YYYY-MM-DD from a Crossref date dict."""
    date_obj = item.get(key, {})
    if not isinstance(date_obj, dict):
        return ""
    parts = date_obj.get("date-parts", [[]])
    if parts and parts[0]:
        dp = parts[0]
        year = dp[0] if len(dp) > 0 else 1970
        month = dp[1] if len(dp) > 1 else 1
        day = dp[2] if len(dp) > 2 else 1
        return f"{year:04d}-{month:02d}-{day:02d}"
    raw = date_obj.get("date-time", "")
    return raw[:10] if raw else ""


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref payload thanh list PaperRecord."""
    items = payload.get("message", {}).get("items", [])
    records: list[PaperRecord] = []

    for item in items:
        # paper_id = DOI
        paper_id = _safe_str(item.get("DOI", ""))
        if not paper_id:
            continue

        # title
        title_raw = item.get("title", [])
        title = _safe_str(title_raw[0] if title_raw else "")
        if not title:
            continue

        # abstract / summary – strip JATS XML tags
        raw_abstract = item.get("abstract", "") or ""
        summary = re.sub(r"<[^>]+>", " ", raw_abstract)
        summary = normalize_whitespace(summary)

        # authors
        authors: list[str] = []
        for author in item.get("author", []):
            given = author.get("given", "")
            family = author.get("family", "")
            name = f"{given} {family}".strip()
            if name:
                authors.append(name)

        # categories / subjects
        categories: list[str] = [_safe_str(s) for s in item.get("subject", []) if s]
        primary_category = categories[0] if categories else ""

        # dates
        published = (
            _parse_date(item, "published")
            or _parse_date(item, "published-print")
            or _parse_date(item, "published-online")
            or _parse_date(item, "created")
        )
        updated = _parse_date(item, "deposited") or _parse_date(item, "indexed") or published

        # URLs
        abs_url = f"https://doi.org/{paper_id}"
        pdf_url = ""
        for link in item.get("link", []):
            ct = link.get("content-type", "").lower()
            url = link.get("URL", "")
            if "pdf" in ct or "pdf" in url.lower():
                pdf_url = url
                break

        # comment = journal / container title
        container = item.get("container-title", [])
        comment = _safe_str(container[0] if container else "")

        records.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=primary_category,
                published=published,
                updated=updated,
                abs_url=abs_url,
                pdf_url=pdf_url,
                comment=comment,
            )
        )

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Goi Crossref API, luu raw response, parse thanh records."""
    base_url = "https://api.crossref.org/works"
    params: dict = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
        "mailto": "student@example.com",
        "select": (
            "DOI,title,abstract,author,subject,published,published-print,"
            "published-online,created,deposited,indexed,link,container-title"
        ),
    }

    payload: dict = {}
    for attempt in range(5):
        try:
            resp = requests.get(base_url, params=params, timeout=30)
            if resp.status_code in (429, 503):
                wait = 2 ** attempt
                print(f"[crossref] HTTP {resp.status_code}, retry in {wait}s ...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            payload = resp.json()
            break
        except requests.RequestException as exc:
            if attempt == 4:
                raise RuntimeError(f"Crossref fetch failed: {exc}") from exc
            time.sleep(2 ** attempt)

    # Save raw response
    ensure_parent(settings.paths.raw_api_response)
    settings.paths.raw_api_response.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8"
    )
    print(f"[crossref] Raw response -> {settings.paths.raw_api_response}")

    records = parse_crossref_payload(payload)
    print(f"[crossref] Parsed {len(records)} records")

    write_json(
        settings.paths.raw_records_json,
        [
            {
                "paper_id": r.paper_id,
                "title": r.title,
                "summary": r.summary,
                "authors": r.authors,
                "categories": r.categories,
                "primary_category": r.primary_category,
                "published": r.published,
                "updated": r.updated,
                "abs_url": r.abs_url,
                "pdf_url": r.pdf_url,
                "comment": r.comment,
            }
            for r in records
        ],
    )
    print(f"[crossref] Raw records -> {settings.paths.raw_records_json}")
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Doc JSON snapshot va map thanh PaperRecord."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return [
        PaperRecord(
            paper_id=item["paper_id"],
            title=item["title"],
            summary=item["summary"],
            authors=item["authors"],
            categories=item["categories"],
            primary_category=item["primary_category"],
            published=item["published"],
            updated=item["updated"],
            abs_url=item["abs_url"],
            pdf_url=item["pdf_url"],
            comment=item["comment"],
        )
        for item in data
    ]
