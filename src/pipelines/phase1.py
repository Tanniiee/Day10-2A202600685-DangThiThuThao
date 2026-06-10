from __future__ import annotations

from datetime import UTC, datetime


def main() -> None:
    """Baseline pipeline end-to-end."""
    from core.config import load_settings
    from core.utils import read_json, write_csv, write_json
    from evaluation.metrics import evaluate_pipeline
    from evaluation.testset import build_test_set
    from ingestion.cleaning import build_clean_dataframe
    from ingestion.crossref import fetch_source_records, load_raw_records
    from observability.quality import build_freshness_report, run_data_quality_checks
    from observability.reporting import generate_phase1_report
    from retrieval.index import LocalEmbeddingIndex

    settings = load_settings()
    run_date = datetime.now(UTC)

    print("=" * 60)
    print("Phase 1: Baseline Pipeline")
    print("=" * 60)

    # Step 1: Load or fetch raw records
    raw_path = settings.paths.raw_records_json
    if not settings.refresh_source and raw_path.exists():
        print(f"[phase1] Loading cached raw records from {raw_path}")
        records = load_raw_records(raw_path)
    else:
        print("[phase1] Fetching from Crossref ...")
        records = fetch_source_records(settings)

    print(f"[phase1] {len(records)} raw records loaded")

    # Step 2: Clean data
    df = build_clean_dataframe(records, run_date)
    print(f"[phase1] {len(df)} clean records")

    if df.empty:
        raise RuntimeError("No records after cleaning — check Crossref API response.")

    # Step 3: Save clean artifacts
    write_csv(df, settings.paths.clean_csv)
    write_json(
        settings.paths.clean_json,
        df.to_dict(orient="records"),
    )
    print(f"[phase1] Saved clean data -> {settings.paths.clean_csv}")

    # Step 4: Build embedding index
    print("[phase1] Building ChromaDB index ...")
    index = LocalEmbeddingIndex.build(
        df,
        settings,
        embeddings_output_path=settings.paths.embeddings_json,
    )
    print(f"[phase1] Index built: {len(index.documents)} documents")

    # Step 5: Build or load evaluation test set
    if not settings.refresh_test_set and settings.paths.eval_testset.exists():
        print(f"[phase1] Using existing test set from {settings.paths.eval_testset}")
    else:
        print("[phase1] Building evaluation test set ...")
        build_test_set(df, settings.paths.eval_testset)

    # Step 6: Evaluate
    print("[phase1] Running evaluation ...")
    bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    metrics = bundle.summary
    print(f"[phase1] Retrieval hit rate: {metrics.get('retrieval_hit_rate', 0):.1%}")
    print(f"[phase1] Mean token F1:      {metrics.get('mean_token_f1', 0):.3f}")
    print(f"[phase1] Judge accuracy:     {metrics.get('judge_accuracy', 0):.1%}")

    # Step 7: Data quality checks
    print("[phase1] Running data quality checks ...")
    quality = run_data_quality_checks(df, settings, report_name="baseline_quality")

    # Step 8: Freshness report
    print("[phase1] Building freshness report ...")
    freshness = build_freshness_report(df, settings, settings.paths.freshness_report)

    # Step 9: Generate markdown report
    source_summary = {
        "source_api": settings.source_api,
        "source_query": settings.source_query,
        "source_filter": settings.source_filter,
        "total_records": len(records),
        "clean_records": len(df),
    }
    generate_phase1_report(
        settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=metrics,
        quality=quality,
        freshness=freshness,
    )

    # Step 10: Quick agent demo
    try:
        from retrieval.qa import answer_question
        demo_questions = [
            "What is the most recent paper about RAG?",
            "Who are the authors of the first paper in the corpus?",
        ]
        demo_answers = []
        for q in demo_questions:
            result = answer_question(q, settings=settings, index=index)
            demo_answers.append({"question": q, "answer": result.answer, "retrieved_titles": result.retrieved_titles})
            print(f"  Q: {q}\n  A: {result.answer}\n")
        write_json(settings.paths.demo_answers, demo_answers)
    except Exception as exc:
        print(f"[phase1] Demo agent skipped: {exc}")

    print("=" * 60)
    print("Phase 1 complete!")
    print(f"  Clean data:   {settings.paths.clean_csv}")
    print(f"  Metrics:      {settings.paths.baseline_metrics}")
    print(f"  Report:       {settings.paths.baseline_report}")
    print("=" * 60)
