# Phase 1 — Baseline Pipeline Report

## 1. Data Source

- **API**: Crossref REST API
- **Query**: `agentic retrieval augmented generation large language model`
- **Filter**: `from-pub-date:2025-12-12,has-abstract:true`
- **Records fetched**: 24
- **Clean records**: 24

## 2. Evaluation Metrics

- **Samples evaluated**: 24
- **Retrieval hit rate**: 100.0%
- **Mean token F1**: 0.862
- **Judge accuracy**: 70.8%
- **Mean judge score**: 4.333

## 3. Data Quality

- Checks passed: **6** / 6

| Check | Status | Detail |
|-------|--------|--------|
| row_count_min_5 | ✅ PASS | row_count=24 |
| paper_id_not_null | ✅ PASS | null_paper_ids=0 |
| paper_id_unique | ✅ PASS | duplicate_paper_ids=0 |
| title_not_null | ✅ PASS | null_or_empty_titles=0 |
| summary_length_ok | ✅ PASS | short_summary_rows=1 (4.2%) |
| freshness_ok | ✅ PASS | stale_rows=0 (0.0%) threshold=180d |

## 4. Freshness

- **Latest published**: 2026-06-02
- **Oldest published**: 2025-12-19
- **Stale rows**: 0 / 24
- **Is fresh**: ✅ Yes
