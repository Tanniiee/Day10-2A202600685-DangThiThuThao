from __future__ import annotations


def main() -> None:
    """Corruption -> evaluate -> repair -> compare flow."""
    from core.config import load_settings
    from core.utils import read_json, write_csv, write_json
    from evaluation.metrics import evaluate_pipeline
    from ingestion.cleaning import build_clean_dataframe
    from ingestion.corruption import corrupt_clean_dataframe
    from ingestion.crossref import load_raw_records
    from observability.quality import build_freshness_report, run_data_quality_checks
    from observability.reporting import generate_corruption_report
    from retrieval.index import LocalEmbeddingIndex

    import pandas as pd
    from datetime import UTC, datetime

    settings = load_settings()
    run_date = datetime.now(UTC)

    print("=" * 60)
    print("Corruption Flow")
    print("=" * 60)

    # Step 1: Load baseline clean dataset
    if not settings.paths.clean_csv.exists():
        raise FileNotFoundError(
            f"Baseline clean CSV not found at {settings.paths.clean_csv}. "
            "Run phase1 first."
        )
    baseline_metrics = read_json(settings.paths.baseline_metrics)
    df_clean = pd.read_csv(settings.paths.clean_csv)
    # Restore list columns from string representation
    import ast
    for col in ["authors", "categories"]:
        if col in df_clean.columns:
            df_clean[col] = df_clean[col].apply(
                lambda x: ast.literal_eval(x) if isinstance(x, str) and x.startswith("[") else []
            )
    print(f"[corruption_flow] Baseline: {len(df_clean)} rows")

    # Step 2: Corrupt
    print("[corruption_flow] Corrupting data ...")
    df_corrupted = corrupt_clean_dataframe(df_clean, settings.paths.corruption_log)
    write_csv(df_corrupted, settings.paths.corrupted_clean_csv)
    write_json(settings.paths.corrupted_clean_json, df_corrupted.to_dict(orient="records"))

    # Step 3: Build corrupted index & evaluate
    print("[corruption_flow] Building corrupted index ...")
    corrupted_index = LocalEmbeddingIndex.build(
        df_corrupted,
        settings,
        embeddings_output_path=settings.paths.corrupted_embeddings_json,
    )
    print("[corruption_flow] Evaluating corrupted dataset ...")
    corrupted_bundle = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )
    corrupted_metrics = corrupted_bundle.summary
    print(f"[corruption_flow] Corrupted hit rate: {corrupted_metrics.get('retrieval_hit_rate', 0):.1%}")

    # Step 4: Quality + freshness on corrupted
    corrupted_quality = run_data_quality_checks(df_corrupted, settings, "corrupted_quality")
    corrupted_freshness = build_freshness_report(
        df_corrupted,
        settings,
        settings.paths.quality_dir / "corrupted_freshness.json",
    )

    # Step 5: Repair – re-clean from raw records
    print("[corruption_flow] Repairing from raw records ...")
    raw_records = load_raw_records(settings.paths.raw_records_json)
    df_repaired = build_clean_dataframe(raw_records, run_date)
    write_csv(df_repaired, settings.paths.repaired_clean_csv)
    write_json(settings.paths.repaired_clean_json, df_repaired.to_dict(orient="records"))
    print(f"[corruption_flow] Repaired: {len(df_repaired)} rows")

    # Step 6: Build repaired index & evaluate
    print("[corruption_flow] Building repaired index ...")
    repaired_index = LocalEmbeddingIndex.build(
        df_repaired,
        settings,
        embeddings_output_path=settings.paths.repaired_embeddings_json,
    )
    print("[corruption_flow] Evaluating repaired dataset ...")
    repaired_bundle = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )
    repaired_metrics = repaired_bundle.summary
    print(f"[corruption_flow] Repaired hit rate: {repaired_metrics.get('retrieval_hit_rate', 0):.1%}")

    # Step 7: Quality + freshness on repaired
    repaired_quality = run_data_quality_checks(df_repaired, settings, "repaired_quality")
    repaired_freshness = build_freshness_report(
        df_repaired,
        settings,
        settings.paths.quality_dir / "repaired_freshness.json",
    )

    # Step 8: Comparison report
    generate_corruption_report(
        settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_metrics,
        repaired_metrics=repaired_metrics,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )

    print("=" * 60)
    print("Corruption flow complete!")
    print(f"  Corrupted metrics: {settings.paths.corrupted_metrics}")
    print(f"  Repaired metrics:  {settings.paths.repaired_metrics}")
    print(f"  Comparison report: {settings.paths.comparison_report}")
    print("=" * 60)
