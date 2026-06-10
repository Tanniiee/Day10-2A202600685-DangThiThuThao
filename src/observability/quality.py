from __future__ import annotations

from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Tao bo data quality checks va ghi ket qua."""
    checks: list[dict[str, Any]] = []

    def _check(name: str, passed: bool, detail: str) -> dict[str, Any]:
        result = {"check": name, "status": "PASS" if passed else "FAIL", "detail": detail}
        checks.append(result)
        return result

    # 1. Row count
    row_count = len(df)
    _check("row_count_min_5", row_count >= 5, f"row_count={row_count}")

    # 2. paper_id not null
    null_ids = int(df["paper_id"].isna().sum()) if "paper_id" in df.columns else row_count
    _check("paper_id_not_null", null_ids == 0, f"null_paper_ids={null_ids}")

    # 3. paper_id unique
    if "paper_id" in df.columns:
        dup_ids = int(df["paper_id"].duplicated().sum())
        _check("paper_id_unique", dup_ids == 0, f"duplicate_paper_ids={dup_ids}")

    # 4. title not null
    null_titles = int(df["title"].isna().sum() + (df["title"] == "").sum()) if "title" in df.columns else row_count
    _check("title_not_null", null_titles == 0, f"null_or_empty_titles={null_titles}")

    # 5. summary length (at least 20 chars for most rows)
    if "summary" in df.columns:
        short_summary = int((df["summary"].fillna("").str.len() < 20).sum())
        pct = short_summary / max(row_count, 1)
        _check("summary_length_ok", pct < 0.3, f"short_summary_rows={short_summary} ({pct:.1%})")

    # 6. freshness via age_days
    if "age_days" in df.columns:
        stale = int((df["age_days"].fillna(9999) > settings.freshness_threshold_days).sum())
        pct_stale = stale / max(row_count, 1)
        _check(
            "freshness_ok",
            pct_stale < 0.5,
            f"stale_rows={stale} ({pct_stale:.1%}) threshold={settings.freshness_threshold_days}d",
        )

    passed = sum(1 for c in checks if c["status"] == "PASS")
    failed = sum(1 for c in checks if c["status"] == "FAIL")
    report: dict[str, Any] = {
        "report_name": report_name,
        "total_rows": row_count,
        "checks_passed": passed,
        "checks_failed": failed,
        "checks": checks,
    }

    out_path = settings.paths.quality_dir / f"{report_name}.json"
    write_json(out_path, report)
    print(f"[quality] {report_name}: {passed} passed, {failed} failed -> {out_path}")
    return report


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Tong hop freshness report."""
    total_rows = len(df)

    if "published" in df.columns and total_rows > 0:
        pub_series = pd.to_datetime(df["published"], errors="coerce").dropna()
        latest_published = str(pub_series.max().date()) if len(pub_series) > 0 else ""
        oldest_published = str(pub_series.min().date()) if len(pub_series) > 0 else ""
    else:
        latest_published = ""
        oldest_published = ""

    stale_rows = 0
    if "age_days" in df.columns:
        stale_rows = int((df["age_days"].fillna(9999) > settings.freshness_threshold_days).sum())

    is_fresh = (stale_rows / max(total_rows, 1)) < 0.5 and bool(latest_published)

    payload: dict[str, Any] = {
        "latest_published": latest_published,
        "oldest_published": oldest_published,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "freshness_threshold_days": settings.freshness_threshold_days,
        "is_fresh": is_fresh,
    }

    write_json(report_path, payload)
    print(f"[freshness] latest={latest_published}, stale={stale_rows}/{total_rows}, is_fresh={is_fresh}")
    return payload
