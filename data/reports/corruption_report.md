# Corruption & Repair Report

This report compares agent evaluation metrics across three dataset states: **Baseline** (clean), **Corrupted**, and **Repaired**.

## 1. Metrics Comparison

| Metric | Baseline | Corrupted | Repaired | Δ Corrupt vs Base | Δ Repaired vs Base |
|---|---|---|---|---|---|
| Retrieval hit rate | 100.0% | 87.5% | 100.0% | -12.5% | +0.0% |
| Mean token F1 | 0.862 | 0.717 | 0.862 | -0.145 | +0.000 |
| Judge accuracy | 70.8% | 70.8% | 70.8% | +0.0% | +0.0% |
| Mean judge score | 4.333 | 4.125 | 4.333 | -0.208 | +0.000 |

## 2. Data Quality

### Corrupted (rows: 22)

Checks: **5 passed**, **1 failed**

| Check | Status | Detail |
|-------|--------|--------|
| row_count_min_5 | ✅ PASS | row_count=22 |
| paper_id_not_null | ✅ PASS | null_paper_ids=0 |
| paper_id_unique | ❌ FAIL | duplicate_paper_ids=1 |
| title_not_null | ✅ PASS | null_or_empty_titles=0 |
| summary_length_ok | ✅ PASS | short_summary_rows=5 (22.7%) |
| freshness_ok | ✅ PASS | stale_rows=2 (9.1%) threshold=180d |

### Repaired (rows: 24)

Checks: **6 passed**, **0 failed**

| Check | Status | Detail |
|-------|--------|--------|
| row_count_min_5 | ✅ PASS | row_count=24 |
| paper_id_not_null | ✅ PASS | null_paper_ids=0 |
| paper_id_unique | ✅ PASS | duplicate_paper_ids=0 |
| title_not_null | ✅ PASS | null_or_empty_titles=0 |
| summary_length_ok | ✅ PASS | short_summary_rows=1 (4.2%) |
| freshness_ok | ✅ PASS | stale_rows=0 (0.0%) threshold=180d |

## 3. Freshness

| Field | Corrupted | Repaired |
|-------|-----------|---------|
| latest_published | 2026-05-06 | 2026-06-02 |
| oldest_published | 2024-02-26 | 2025-12-19 |
| stale_rows | 2 | 0 |
| total_rows | 22 | 24 |
| is_fresh | True | True |

## 4. Analysis

- Corruption reduced retrieval hit rate from **100.0%** to **87.5%** (-12.5%).
- After repair, retrieval hit rate recovered to **100.0%** (0.0% vs baseline).
- This demonstrates that data quality directly impacts RAG agent performance, and that repairing from the raw source restores it.
