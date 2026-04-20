#!/usr/bin/env python3
"""
Compute all reported metrics for a set of predictions.

Accepts a predictions CSV with columns [filename, label, prediction] and
(optionally) [probability] for AUC-ROC computation. Reports:
  - Accuracy, sensitivity, specificity, precision, F1
  - Matthews correlation coefficient (MCC)
  - AUC-ROC (when probabilities provided)
  - 95% Wilson score intervals for proportion-based metrics
  - Two-proportion z-test for head-to-head accuracy comparison
  - Prevalence-adjusted PPV / NPV / FP-per-100 / FP/TP at 5, 10, 15% prevalence

Usage
-----
python evaluate.py \
    --predictions results/llava_qlora_test.csv \
    --output results/llava_qlora_metrics.json \
    --bootstrap 10000

# Head-to-head comparison
python evaluate.py \
    --predictions results/llava_qlora_test.csv \
    --compare results/swin_t_test.csv \
    --output results/llava_vs_swint.json
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import (
    accuracy_score, confusion_matrix, f1_score,
    matthews_corrcoef, precision_score, recall_score, roc_auc_score,
)
from statsmodels.stats.proportion import proportion_confint


def wilson_ci(k: int, n: int, alpha: float = 0.05) -> Tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    return proportion_confint(k, n, alpha=alpha, method="wilson")


def basic_metrics(labels: np.ndarray, preds: np.ndarray,
                  probs: np.ndarray | None = None) -> Dict:
    tn, fp, fn, tp = confusion_matrix(labels, preds, labels=[0, 1]).ravel()
    n = len(labels)
    n_pos = int((labels == 1).sum())
    n_neg = int((labels == 0).sum())

    acc = accuracy_score(labels, preds)
    sens = tp / (tp + fn) if (tp + fn) else float("nan")
    spec = tn / (tn + fp) if (tn + fp) else float("nan")
    prec = precision_score(labels, preds, zero_division=0)
    f1 = f1_score(labels, preds, zero_division=0)
    mcc = matthews_corrcoef(labels, preds)
    auc = roc_auc_score(labels, probs) if probs is not None else None

    return {
        "n": n,
        "tp": int(tp), "tn": int(tn), "fp": int(fp), "fn": int(fn),
        "accuracy": acc,
        "accuracy_ci95": list(wilson_ci(tp + tn, n)),
        "sensitivity": sens,
        "sensitivity_ci95": list(wilson_ci(tp, n_pos)),
        "specificity": spec,
        "specificity_ci95": list(wilson_ci(tn, n_neg)),
        "precision": prec,
        "f1": f1,
        "mcc": mcc,
        "auc_roc": auc,
    }


def two_proportion_z(k1: int, n1: int, k2: int, n2: int) -> Dict[str, float]:
    p1, p2 = k1 / n1, k2 / n2
    p = (k1 + k2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    z = (p1 - p2) / se if se > 0 else 0.0
    p_val = 2 * (1 - stats.norm.cdf(abs(z)))
    return {"p1": p1, "p2": p2, "z": z, "p_value": p_val}


def prevalence_adjusted(sens: float, spec: float,
                        prevalences=(0.05, 0.10, 0.15)) -> Dict[str, Dict]:
    out = {}
    for prev in prevalences:
        tpr, fpr = sens, 1 - spec
        ppv = (tpr * prev) / (tpr * prev + fpr * (1 - prev))
        npv = (spec * (1 - prev)) / ((1 - tpr) * prev + spec * (1 - prev))
        fp_per_100 = fpr * (1 - prev) * 100
        fp_tp = fpr * (1 - prev) / (tpr * prev) if tpr * prev > 0 else float("inf")
        out[f"prev_{int(prev * 100)}pct"] = {
            "ppv": ppv, "npv": npv,
            "fp_per_100": fp_per_100, "fp_over_tp": fp_tp,
        }
    return out


def bootstrap_mcc(labels: np.ndarray, preds: np.ndarray,
                  n_boot: int, seed: int = 42) -> Tuple[float, float]:
    rng = np.random.default_rng(seed)
    n = len(labels)
    vals = np.empty(n_boot)
    for i in range(n_boot):
        idx = rng.integers(0, n, size=n)
        vals[i] = matthews_corrcoef(labels[idx], preds[idx])
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--predictions", required=True, type=Path,
                   help="CSV with columns filename,label,prediction[,probability]")
    p.add_argument("--compare", type=Path,
                   help="Optional second predictions CSV for two-proportion z-test.")
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--bootstrap", type=int, default=0,
                   help="If > 0, add a bootstrap 95% CI for MCC.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    df = pd.read_csv(args.predictions).dropna(subset=["prediction"])
    labels = df["label"].astype(int).to_numpy()
    preds = df["prediction"].astype(int).to_numpy()
    probs = df["probability"].to_numpy() if "probability" in df.columns else None

    result = {
        "predictions_file": str(args.predictions),
        "metrics": basic_metrics(labels, preds, probs),
        "prevalence_adjusted": prevalence_adjusted(
            basic_metrics(labels, preds)["sensitivity"],
            basic_metrics(labels, preds)["specificity"],
        ),
    }

    if args.bootstrap > 0:
        lo, hi = bootstrap_mcc(labels, preds, args.bootstrap)
        result["metrics"]["mcc_ci95"] = [lo, hi]

    if args.compare is not None:
        df2 = pd.read_csv(args.compare).dropna(subset=["prediction"])
        labels2 = df2["label"].astype(int).to_numpy()
        preds2 = df2["prediction"].astype(int).to_numpy()
        # Align on filename if both include it
        if "filename" in df.columns and "filename" in df2.columns:
            merged = df.merge(df2, on="filename", suffixes=("_1", "_2"))
            labels = merged["label_1"].astype(int).to_numpy()
            preds = merged["prediction_1"].astype(int).to_numpy()
            preds2 = merged["prediction_2"].astype(int).to_numpy()
        k1 = int((preds == labels).sum())
        k2 = int((preds2 == labels).sum())
        n = len(labels)
        result["two_proportion_z_test"] = two_proportion_z(k1, n, k2, n)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(result, f, indent=2, default=float)
    print(f"✓ Metrics written: {args.output}")


if __name__ == "__main__":
    main()
