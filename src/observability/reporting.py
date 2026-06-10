from __future__ import annotations

from typing import Any

from core.utils import write_text


def _fmt_pct(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.1%}"


def _fmt_float(value: float | None, digits: int = 3) -> str:
    if value is None:
        return "N/A"
    return f"{value:.{digits}f}"


def _quality_table(quality: dict[str, Any]) -> str:
    checks = quality.get("checks", [])
    if not checks:
        return "_No checks recorded._\n"
    lines = ["| Check | Status | Detail |", "|-------|--------|--------|"]
    for c in checks:
        icon = "✅" if c["status"] == "PASS" else "❌"
        lines.append(f"| {c['check']} | {icon} {c['status']} | {c.get('detail', '')} |")
    return "\n".join(lines) + "\n"


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Viet markdown report cho baseline phase."""
    lines: list[str] = []

    lines.append("# Phase 1 — Baseline Pipeline Report\n")

    # Source summary
    lines.append("## 1. Data Source\n")
    lines.append(f"- **API**: {source_summary.get('source_api', 'Crossref REST API')}")
    lines.append(f"- **Query**: `{source_summary.get('source_query', '')}`")
    lines.append(f"- **Filter**: `{source_summary.get('source_filter', '')}`")
    lines.append(f"- **Records fetched**: {source_summary.get('total_records', 'N/A')}")
    lines.append(f"- **Clean records**: {source_summary.get('clean_records', 'N/A')}")
    lines.append("")

    # Evaluation metrics
    lines.append("## 2. Evaluation Metrics\n")
    lines.append(f"- **Samples evaluated**: {metrics.get('samples', 'N/A')}")
    lines.append(f"- **Retrieval hit rate**: {_fmt_pct(metrics.get('retrieval_hit_rate'))}")
    lines.append(f"- **Mean token F1**: {_fmt_float(metrics.get('mean_token_f1'))}")
    lines.append(f"- **Judge accuracy**: {_fmt_pct(metrics.get('judge_accuracy'))}")
    lines.append(f"- **Mean judge score**: {_fmt_float(metrics.get('mean_judge_score'))}")
    ragas = metrics.get("ragas", {})
    if isinstance(ragas, dict) and "skipped" not in ragas and "error" not in ragas:
        lines.append(f"- **Ragas answer relevancy**: {_fmt_float(ragas.get('answer_relevancy'))}")
        lines.append(f"- **Ragas faithfulness**: {_fmt_float(ragas.get('faithfulness'))}")
    lines.append("")

    # Data quality
    lines.append("## 3. Data Quality\n")
    lines.append(
        f"- Checks passed: **{quality.get('checks_passed', 'N/A')}** / "
        f"{quality.get('checks_passed', 0) + quality.get('checks_failed', 0)}"
    )
    lines.append("")
    lines.append(_quality_table(quality))

    # Freshness
    lines.append("## 4. Freshness\n")
    lines.append(f"- **Latest published**: {freshness.get('latest_published', 'N/A')}")
    lines.append(f"- **Oldest published**: {freshness.get('oldest_published', 'N/A')}")
    lines.append(f"- **Stale rows**: {freshness.get('stale_rows', 'N/A')} / {freshness.get('total_rows', 'N/A')}")
    lines.append(f"- **Is fresh**: {'✅ Yes' if freshness.get('is_fresh') else '❌ No'}")
    lines.append("")

    write_text(report_path, "\n".join(lines))
    print(f"[report] Phase 1 report -> {report_path}")


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """Viet markdown report so sanh baseline/corrupted/repaired."""
    lines: list[str] = []

    lines.append("# Corruption & Repair Report\n")
    lines.append(
        "This report compares agent evaluation metrics across three dataset states: "
        "**Baseline** (clean), **Corrupted**, and **Repaired**.\n"
    )

    # Metrics comparison table
    lines.append("## 1. Metrics Comparison\n")
    headers = ["Metric", "Baseline", "Corrupted", "Repaired", "Δ Corrupt vs Base", "Δ Repaired vs Base"]
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("|" + "|".join(["---"] * len(headers)) + "|")

    def _row(label: str, key: str, pct: bool = False) -> str:
        b = baseline_metrics.get(key)
        c = corrupted_metrics.get(key)
        r = repaired_metrics.get(key)
        fmt = _fmt_pct if pct else _fmt_float

        def _delta(new, base):
            if new is None or base is None:
                return "N/A"
            d = new - base
            sign = "+" if d >= 0 else ""
            return f"{sign}{_fmt_pct(d) if pct else _fmt_float(d)}"

        return f"| {label} | {fmt(b)} | {fmt(c)} | {fmt(r)} | {_delta(c, b)} | {_delta(r, b)} |"

    lines.append(_row("Retrieval hit rate", "retrieval_hit_rate", pct=True))
    lines.append(_row("Mean token F1", "mean_token_f1"))
    lines.append(_row("Judge accuracy", "judge_accuracy", pct=True))
    lines.append(_row("Mean judge score", "mean_judge_score"))
    lines.append("")

    # Quality comparison
    lines.append("## 2. Data Quality\n")
    for label, quality in [("Corrupted", corrupted_quality), ("Repaired", repaired_quality)]:
        passed = quality.get("checks_passed", "N/A")
        failed = quality.get("checks_failed", "N/A")
        total = quality.get("total_rows", "N/A")
        lines.append(f"### {label} (rows: {total})\n")
        lines.append(f"Checks: **{passed} passed**, **{failed} failed**\n")
        lines.append(_quality_table(quality))

    # Freshness comparison
    lines.append("## 3. Freshness\n")
    lines.append("| Field | Corrupted | Repaired |")
    lines.append("|-------|-----------|---------|")
    for field in ["latest_published", "oldest_published", "stale_rows", "total_rows", "is_fresh"]:
        cv = corrupted_freshness.get(field, "N/A")
        rv = repaired_freshness.get(field, "N/A")
        lines.append(f"| {field} | {cv} | {rv} |")
    lines.append("")

    # Analysis
    lines.append("## 4. Analysis\n")
    b_hit = baseline_metrics.get("retrieval_hit_rate", 0) or 0
    c_hit = corrupted_metrics.get("retrieval_hit_rate", 0) or 0
    r_hit = repaired_metrics.get("retrieval_hit_rate", 0) or 0
    lines.append(
        f"- Corruption reduced retrieval hit rate from **{_fmt_pct(b_hit)}** to **{_fmt_pct(c_hit)}** "
        f"({_fmt_pct(c_hit - b_hit)})."
    )
    lines.append(
        f"- After repair, retrieval hit rate recovered to **{_fmt_pct(r_hit)}** "
        f"({_fmt_pct(r_hit - b_hit)} vs baseline)."
    )
    lines.append(
        "- This demonstrates that data quality directly impacts RAG agent performance, "
        "and that repairing from the raw source restores it."
    )
    lines.append("")

    write_text(report_path, "\n".join(lines))
    print(f"[report] Corruption report -> {report_path}")
