from __future__ import annotations

from typing import Any

import pandas as pd

from core.utils import write_json


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Tao bo evaluation set tu cleaned dataframe."""
    if len(df) < 4:
        raise ValueError(f"Need at least 4 documents, got {len(df)}")

    # Pick up to 8 representative papers (evenly spaced)
    n = min(8, len(df))
    step = max(1, len(df) // n)
    selected = df.iloc[::step].head(n)

    samples: list[dict[str, Any]] = []
    idx = 0

    for _, row in selected.iterrows():
        paper_id = str(row["paper_id"])
        title = str(row["title"])
        summary = str(row["summary"])
        authors_joined = str(row.get("authors_joined", ""))
        published = str(row.get("published", ""))
        categories_joined = str(row.get("categories_joined", ""))

        # 1. summary question
        if summary:
            samples.append(
                {
                    "id": f"q{idx:03d}",
                    "question_type": "summary",
                    "question": f"What is the paper '{title}' about?",
                    "ground_truth": summary[:500] if len(summary) > 500 else summary,
                    "ground_truth_doc_ids": [paper_id],
                }
            )
            idx += 1

        # 2. authors question
        if authors_joined:
            samples.append(
                {
                    "id": f"q{idx:03d}",
                    "question_type": "authors",
                    "question": f"Who authored the paper '{title}'?",
                    "ground_truth": authors_joined,
                    "ground_truth_doc_ids": [paper_id],
                }
            )
            idx += 1

        # 3. date question
        if published:
            samples.append(
                {
                    "id": f"q{idx:03d}",
                    "question_type": "date",
                    "question": f"When was the paper '{title}' published?",
                    "ground_truth": published,
                    "ground_truth_doc_ids": [paper_id],
                }
            )
            idx += 1

        # 4. categories question
        if categories_joined:
            samples.append(
                {
                    "id": f"q{idx:03d}",
                    "question_type": "categories",
                    "question": f"What categories does the paper '{title}' belong to?",
                    "ground_truth": categories_joined,
                    "ground_truth_doc_ids": [paper_id],
                }
            )
            idx += 1

    write_json(output_path, samples)
    print(f"[testset] Built {len(samples)} evaluation samples -> {output_path}")
    return samples
