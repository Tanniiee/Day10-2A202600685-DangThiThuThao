from __future__ import annotations

from datetime import datetime

import pandas as pd

from core.utils import normalize_whitespace
from ingestion.crossref import PaperRecord


def _safe_date(value: str) -> pd.Timestamp | pd.NaT:
    try:
        return pd.Timestamp(value)
    except Exception:
        return pd.NaT


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records thanh dataframe san sang de embed."""
    rows = []
    for r in records:
        title = normalize_whitespace(r.title)
        summary = normalize_whitespace(r.summary)
        authors = [normalize_whitespace(a) for a in r.authors if a and a.strip()]
        categories = [normalize_whitespace(c) for c in r.categories if c and c.strip()]
        primary_category = normalize_whitespace(r.primary_category)
        published = normalize_whitespace(r.published)
        updated = normalize_whitespace(r.updated)

        # Skip records missing essential fields
        if not r.paper_id or not title:
            continue

        # Compute age_days (both naive UTC to avoid tz mismatch)
        pub_ts = _safe_date(published)
        if pd.isna(pub_ts):
            age_days = None
        else:
            run_ts = pd.Timestamp(run_date).tz_localize(None) if pd.Timestamp(run_date).tzinfo is None else pd.Timestamp(run_date).tz_convert(None)
            pub_ts_naive = pub_ts.tz_localize(None) if pub_ts.tzinfo is not None else pub_ts
            age_days = max(0, (run_ts - pub_ts_naive).days)

        authors_joined = ", ".join(authors)
        categories_joined = ", ".join(categories)
        summary_chars = len(summary)

        # text_for_embedding: rich context block
        parts = [f"Title: {title}"]
        if authors_joined:
            parts.append(f"Authors: {authors_joined}")
        if categories_joined:
            parts.append(f"Categories: {categories_joined}")
        if published:
            parts.append(f"Published: {published}")
        if summary:
            parts.append(f"Abstract: {summary}")
        if r.comment:
            parts.append(f"Journal: {normalize_whitespace(r.comment)}")
        text_for_embedding = " | ".join(parts)

        rows.append(
            {
                "paper_id": r.paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "categories": categories,
                "primary_category": primary_category,
                "published": published,
                "updated": updated,
                "abs_url": r.abs_url,
                "pdf_url": r.pdf_url,
                "comment": normalize_whitespace(r.comment),
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "summary_chars": summary_chars,
                "age_days": age_days,
                "text_for_embedding": text_for_embedding,
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    # Drop rows with empty title or paper_id
    df = df[df["paper_id"].notna() & (df["paper_id"] != "")]
    df = df[df["title"].notna() & (df["title"] != "")]

    # Drop duplicates by paper_id (keep first)
    df = df.drop_duplicates(subset=["paper_id"], keep="first")

    # Sort by published descending (newest first)
    df = df.sort_values("published", ascending=False, na_position="last").reset_index(drop=True)

    return df
