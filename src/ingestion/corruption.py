from __future__ import annotations

import random
import string

import pandas as pd

from core.utils import write_json


def _rebuild_text_for_embedding(df: pd.DataFrame) -> pd.Series:
    parts_series = []
    for _, row in df.iterrows():
        parts = [f"Title: {row.get('title', '')}"]
        authors = row.get("authors_joined", "")
        categories = row.get("categories_joined", "")
        published = row.get("published", "")
        summary = row.get("summary", "")
        comment = row.get("comment", "")
        if authors:
            parts.append(f"Authors: {authors}")
        if categories:
            parts.append(f"Categories: {categories}")
        if published:
            parts.append(f"Published: {published}")
        if summary:
            parts.append(f"Abstract: {summary}")
        if comment:
            parts.append(f"Journal: {comment}")
        parts_series.append(" | ".join(parts))
    return pd.Series(parts_series, index=df.index)


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Simulate nhieu dang data corruption."""
    rng = random.Random(42)
    log: dict = {"operations": [], "rows_before": len(df)}

    corrupted = df.copy()

    # 1. Drop some latest records (top 3 newest)
    drop_n = min(3, max(1, len(corrupted) // 8))
    drop_ids = corrupted.head(drop_n).index.tolist()
    corrupted = corrupted.drop(index=drop_ids)
    log["operations"].append({"op": "drop_latest_records", "rows_dropped": len(drop_ids)})

    # 2. Blank summary on ~15% of rows
    blank_n = max(1, int(len(corrupted) * 0.15))
    blank_idx = rng.sample(corrupted.index.tolist(), min(blank_n, len(corrupted)))
    corrupted.loc[blank_idx, "summary"] = ""
    corrupted.loc[blank_idx, "summary_chars"] = 0
    log["operations"].append({"op": "blank_summary", "rows_affected": len(blank_idx)})

    # 3. Inject noise into summary text (~10% of rows)
    noise_n = max(1, int(len(corrupted) * 0.10))
    noise_idx = rng.sample(corrupted.index.tolist(), min(noise_n, len(corrupted)))
    for i in noise_idx:
        noise = "".join(rng.choices(string.ascii_lowercase + " ", k=30))
        original = str(corrupted.at[i, "summary"])
        corrupted.at[i, "summary"] = original + " " + noise if original else noise
    log["operations"].append({"op": "inject_noise", "rows_affected": len(noise_idx)})

    # 4. Truncate title on ~10% of rows
    trunc_n = max(1, int(len(corrupted) * 0.10))
    trunc_idx = rng.sample(corrupted.index.tolist(), min(trunc_n, len(corrupted)))
    for i in trunc_idx:
        title = str(corrupted.at[i, "title"])
        corrupted.at[i, "title"] = title[:15] + "..." if len(title) > 15 else title
    log["operations"].append({"op": "truncate_title", "rows_affected": len(trunc_idx)})

    # 5. Make published date stale (~10% of rows — shift back 2 years)
    stale_n = max(1, int(len(corrupted) * 0.10))
    stale_idx = rng.sample(corrupted.index.tolist(), min(stale_n, len(corrupted)))
    for i in stale_idx:
        pub = str(corrupted.at[i, "published"])
        if pub and len(pub) >= 4:
            try:
                year = int(pub[:4]) - 2
                corrupted.at[i, "published"] = f"{year}{pub[4:]}"
                # Recompute age_days
                if corrupted.at[i, "age_days"] is not None:
                    corrupted.at[i, "age_days"] = corrupted.at[i, "age_days"] + 730
            except ValueError:
                pass
    log["operations"].append({"op": "stale_published_date", "rows_affected": len(stale_idx)})

    # 6. Add duplicate rows (~5% duplicates)
    dup_n = max(1, int(len(corrupted) * 0.05))
    dup_rows = corrupted.sample(n=min(dup_n, len(corrupted)), random_state=42)
    corrupted = pd.concat([corrupted, dup_rows], ignore_index=True)
    log["operations"].append({"op": "add_duplicates", "rows_added": len(dup_rows)})

    # 7. Rebuild text_for_embedding
    corrupted["text_for_embedding"] = _rebuild_text_for_embedding(corrupted)

    log["rows_after"] = len(corrupted)
    write_json(output_log_path, log)
    print(f"[corruption] {len(df)} -> {len(corrupted)} rows, log -> {output_log_path}")
    return corrupted
