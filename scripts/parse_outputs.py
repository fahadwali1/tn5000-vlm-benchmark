#!/usr/bin/env python3
"""
Three-level parsing pipeline for zero-shot VLM completions.

Level 1: explicit malignant/benign keyword matching (case-insensitive).
Level 2: TI-RADS category extraction (TR4/TR5 -> malignant, TR1/TR2/TR3 -> benign).
Level 3: rule-based sentiment classification using predefined term lists.

Input:  JSONL produced by zero_shot_inference.py (one record per image).
Output: CSV with columns
        [filename, label, prediction, level_used, parsed_ok]
        prediction in {0: benign, 1: malignant, NaN: parse failure}

Usage
-----
python parse_outputs.py \
    --input results/zs_gemini25pro_baseline.jsonl \
    --output results/zs_gemini25pro_baseline_parsed.csv
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd

# --- Term lists for Level 3 (sentiment-based) fallback ---
MALIGNANT_TERMS = [
    "malignant", "malignancy", "suspicious for cancer", "highly suspicious",
    "suspicious", "concerning", "worrisome", "cancer", "carcinoma",
    "papillary", "follicular carcinoma", "anaplastic", "medullary carcinoma",
    "ti-rads 4", "ti-rads 5", "tr 4", "tr 5",
    "microcalcifications", "punctate echogenic foci", "taller-than-wide",
    "irregular margin", "lobulated margin", "extra-thyroidal extension",
]
BENIGN_TERMS = [
    "benign", "not suspicious", "non-suspicious", "reassuring",
    "colloid", "spongiform", "cystic", "simple cyst",
    "ti-rads 1", "ti-rads 2", "ti-rads 3", "tr 1", "tr 2", "tr 3",
    "smooth margin", "wider-than-tall", "follow-up", "no follow-up needed",
]

TI_RADS_PATTERN = re.compile(
    r"\b(?:ti[-\s]?rads|tr)\s*[:\-]?\s*([1-5])\b",
    flags=re.IGNORECASE,
)


def level1_keyword(text: str) -> int | None:
    """Explicit word match on the FINAL line if present, else whole text."""
    if not text:
        return None
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    candidates = [lines[-1], " ".join(lines)] if lines else [text]
    for candidate in candidates:
        lower = candidate.lower()
        has_mal = re.search(r"\bmalignant\b", lower) is not None
        has_ben = re.search(r"\bbenign\b", lower) is not None
        if has_mal and not has_ben:
            return 1
        if has_ben and not has_mal:
            return 0
    return None


def level2_tirads(text: str) -> int | None:
    """Map TR4/TR5 → malignant, TR1/TR2/TR3 → benign. Use the LAST occurrence."""
    if not text:
        return None
    matches = TI_RADS_PATTERN.findall(text)
    if not matches:
        return None
    try:
        last = int(matches[-1])
    except ValueError:
        return None
    if last in (4, 5):
        return 1
    if last in (1, 2, 3):
        return 0
    return None


def level3_sentiment(text: str) -> int | None:
    """Rule-based tally of malignant vs benign terms."""
    if not text:
        return None
    lower = text.lower()
    mal = sum(lower.count(t) for t in MALIGNANT_TERMS)
    ben = sum(lower.count(t) for t in BENIGN_TERMS)
    if mal == ben == 0:
        return None
    if mal > ben:
        return 1
    if ben > mal:
        return 0
    return None


def parse_completion(text: str) -> tuple[int | float, int, bool]:
    """Return (prediction, level_used, parsed_ok). prediction NaN if all levels fail."""
    for level_idx, fn in enumerate([level1_keyword, level2_tirads, level3_sentiment], start=1):
        pred = fn(text)
        if pred is not None:
            return pred, level_idx, True
    return float("nan"), 0, False


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--input", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    with open(args.input, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            pred, level, ok = parse_completion(rec.get("completion", ""))
            rows.append({
                "filename": rec["filename"],
                "label": rec["label"],
                "model": rec["model"],
                "prompt_file": rec.get("prompt_file", ""),
                "prediction": pred,
                "level_used": level,
                "parsed_ok": ok,
            })

    df = pd.DataFrame(rows)
    df.to_csv(args.output, index=False)
    n = len(df)
    n_ok = int(df["parsed_ok"].sum())
    n_l1 = int((df["level_used"] == 1).sum())
    n_l2 = int((df["level_used"] == 2).sum())
    n_l3 = int((df["level_used"] == 3).sum())
    print(f"✓ Parsed {n_ok}/{n} ({100 * n_ok / n:.1f}%)")
    print(f"    Level 1 (keyword):  {n_l1}")
    print(f"    Level 2 (TI-RADS):  {n_l2}")
    print(f"    Level 3 (sentiment): {n_l3}")
    print(f"    Failed:              {n - n_ok}")
    print(f"  Written: {args.output}")


if __name__ == "__main__":
    main()
