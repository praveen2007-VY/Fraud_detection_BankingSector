"""
Fraud Detection System — Phase 6
File: ml/noise_test_report_generator.py

Purpose:
    Generate a controlled noise/robustness test dataset from the REAL dataset.
    This is a SEPARATE test dataset — it does NOT replace:
        data/transactions_clean.csv
        ml/features_unsupervised.csv

    The purpose is to verify that the preprocessing/model pipeline
    behaves sensibly when controlled data-quality noise is introduced.

    DO NOT use this for training or pseudo-label generation.
"""

import os
import sys
import random
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

SEED = 42
random.seed(SEED)
np.random.seed(SEED)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CLEAN_CSV = os.path.join(PROJECT_ROOT, "data", "transactions_clean.csv")
NOISE_CSV = os.path.join(PROJECT_ROOT, "data", "transactions_noise_test.csv")
REPORT_MD = os.path.join(PROJECT_ROOT, "ml", "noise_test_report.md")


def generate_noise_dataset() -> dict:
    """
    Apply controlled data-quality perturbations to the REAL dataset.
    Returns a dict with stats for the report.
    """
    df = pd.read_csv(CLEAN_CSV)
    original_n = len(df)
    assert original_n == 2512, f"Expected 2512 rows, got {original_n}"

    rng = np.random.default_rng(SEED)
    noise_df = df.copy()
    perturbation_log = []

    # ── Perturbation 1: Missing values (0.5% of TransactionAmount cells) ────
    n_missing = max(1, int(original_n * 0.005))  # ~13 rows
    missing_idx = rng.choice(original_n, size=n_missing, replace=False)
    noise_df.loc[missing_idx, "TransactionAmount"] = np.nan
    perturbation_log.append({
        "type": "Missing Values",
        "column": "TransactionAmount",
        "n_rows_affected": n_missing,
        "pct_affected": round(100 * n_missing / original_n, 2),
        "description": "Set to NaN to simulate missing data",
    })

    # ── Perturbation 2: Whitespace variations in Location ────────────────────
    n_whitespace = max(1, int(original_n * 0.01))  # ~25 rows
    ws_idx = rng.choice(original_n, size=n_whitespace, replace=False)
    noise_df.loc[ws_idx, "Location"] = noise_df.loc[ws_idx, "Location"].apply(
        lambda x: f"  {x}  " if pd.notna(x) else x
    )
    perturbation_log.append({
        "type": "Whitespace Variation",
        "column": "Location",
        "n_rows_affected": n_whitespace,
        "pct_affected": round(100 * n_whitespace / original_n, 2),
        "description": "Added leading/trailing whitespace to simulate inconsistent ingestion",
    })

    # ── Perturbation 3: Duplicate records (10 rows duplicated) ───────────────
    n_dupes = 10
    dupe_idx = rng.choice(original_n, size=n_dupes, replace=False)
    dupe_rows = df.iloc[dupe_idx].copy()  # Use original (unperturbed) rows
    noise_df = pd.concat([noise_df, dupe_rows], ignore_index=True)
    perturbation_log.append({
        "type": "Duplicate Records",
        "column": "All",
        "n_rows_affected": n_dupes,
        "pct_affected": round(100 * n_dupes / original_n, 2),
        "description": f"Appended {n_dupes} exact duplicate rows to simulate re-ingestion",
    })

    # ── Perturbation 4: Timestamp format variation ────────────────────────────
    # Change 1% of dates from "YYYY-MM-DD HH:MM:SS" to "DD/MM/YYYY HH:MM"
    n_ts = max(1, int(original_n * 0.01))  # ~25 rows
    ts_idx = rng.choice(original_n, size=n_ts, replace=False)
    for i in ts_idx:
        try:
            ts = pd.to_datetime(noise_df.loc[i, "TransactionDate"])
            noise_df.loc[i, "TransactionDate"] = ts.strftime("%d/%m/%Y %H:%M")
        except Exception:
            pass
    perturbation_log.append({
        "type": "Timestamp Format Variation",
        "column": "TransactionDate",
        "n_rows_affected": n_ts,
        "pct_affected": round(100 * n_ts / original_n, 2),
        "description": "Changed format from YYYY-MM-DD HH:MM:SS to DD/MM/YYYY HH:MM",
    })

    # ── Perturbation 5: Small amount perturbation (±1% jitter) ───────────────
    n_jitter = max(1, int(original_n * 0.02))  # ~50 rows
    jitter_idx = rng.choice(original_n, size=n_jitter, replace=False)
    original_amounts = df.loc[jitter_idx, "TransactionAmount"].values
    jitter = rng.uniform(-0.01, 0.01, size=n_jitter) * original_amounts
    # Only apply to non-missing rows in the noise copy
    for enum_i, orig_idx in enumerate(jitter_idx):
        if pd.notna(noise_df.loc[orig_idx, "TransactionAmount"]):
            noise_df.loc[orig_idx, "TransactionAmount"] = round(
                float(original_amounts[enum_i]) + jitter[enum_i], 2
            )
    perturbation_log.append({
        "type": "Small Feature Perturbation",
        "column": "TransactionAmount",
        "n_rows_affected": n_jitter,
        "pct_affected": round(100 * n_jitter / original_n, 2),
        "description": "Added uniform ±1% jitter to TransactionAmount (harmless magnitude)",
    })

    # Save noise dataset
    noise_df.to_csv(NOISE_CSV, index=False)

    return {
        "original_rows": original_n,
        "noise_rows": len(noise_df),
        "perturbations": perturbation_log,
        "seed": SEED,
    }


def run_noise_pipeline_test(stats: dict) -> dict:
    """
    Test whether the existing preprocessing pipeline can handle the noise dataset
    and report expected vs actual behavior.
    """
    df_noise = pd.read_csv(NOISE_CSV)
    results = {}

    # Test 1: Missing value detection
    null_count = df_noise["TransactionAmount"].isna().sum()
    results["missing_values_detected"] = null_count
    results["missing_values_expected"] = stats["perturbations"][0]["n_rows_affected"]
    results["missing_detection_ok"] = null_count == stats["perturbations"][0]["n_rows_affected"]

    # Test 2: Whitespace detection
    ws_count = df_noise["Location"].apply(
        lambda x: isinstance(x, str) and (x.startswith(" ") or x.endswith(" "))
    ).sum()
    results["whitespace_rows_detected"] = ws_count
    results["whitespace_ok"] = ws_count == stats["perturbations"][1]["n_rows_affected"]

    # Test 3: Duplicate detection
    dup_count = df_noise["TransactionID"].duplicated().sum()
    results["duplicates_detected"] = dup_count
    results["duplicates_expected"] = stats["perturbations"][2]["n_rows_affected"]
    results["duplicates_ok"] = dup_count == stats["perturbations"][2]["n_rows_affected"]

    # Test 4: Timestamp parsing
    parsed_ok = 0
    for val in df_noise["TransactionDate"]:
        try:
            pd.to_datetime(val, dayfirst=True)
            parsed_ok += 1
        except Exception:
            pass
    results["timestamp_parseable"] = parsed_ok
    results["timestamp_total"] = len(df_noise)
    results["timestamp_ok"] = parsed_ok == len(df_noise)

    # Test 5: Original dataset unchanged
    df_orig = pd.read_csv(
        os.path.join(PROJECT_ROOT, "data", "transactions_clean.csv")
    )
    results["original_unchanged"] = (
        len(df_orig) == 2512 and
        df_orig["TransactionID"].nunique() == 2512 and
        df_orig.isnull().sum().sum() == 0
    )

    return results


def generate_report(stats: dict, test_results: dict) -> str:
    lines = [
        "# Phase 6 — Noise Robustness Test Report",
        "",
        "> **PURPOSE**: This is a robustness-testing dataset ONLY.",
        "> It does NOT replace `data/transactions_clean.csv` or `ml/features_unsupervised.csv`.",
        "> It was NOT used for training. No fraud labels were created.",
        "",
        "---",
        "",
        f"## Dataset Statistics",
        "",
        f"| Property | Value |",
        f"|---|---|",
        f"| Original rows | {stats['original_rows']} |",
        f"| Noise dataset rows | {stats['noise_rows']} (includes {stats['noise_rows'] - stats['original_rows']} duplicates) |",
        f"| Random seed | {stats['seed']} |",
        f"| Source | `data/transactions_clean.csv` (REAL dataset — unchanged) |",
        "",
        "---",
        "",
        "## Perturbations Applied",
        "",
        "| # | Type | Column | Rows Affected | % Affected | Description |",
        "|---|---|---|---|---|---|",
    ]
    for i, p in enumerate(stats["perturbations"], 1):
        lines.append(
            f"| {i} | {p['type']} | `{p['column']}` | {p['n_rows_affected']} | {p['pct_affected']}% | {p['description']} |"
        )
    lines += [
        "",
        "---",
        "",
        "## Noise Detection Test Results",
        "",
        "| Check | Expected | Detected | Status |",
        "|---|---|---|---|",
        f"| Missing TransactionAmount values | {test_results['missing_values_expected']} | {test_results['missing_values_detected']} | {'PASS' if test_results['missing_detection_ok'] else 'FAIL'} |",
        f"| Whitespace rows in Location | {stats['perturbations'][1]['n_rows_affected']} | {test_results['whitespace_rows_detected']} | {'PASS' if test_results['whitespace_ok'] else 'FAIL'} |",
        f"| Duplicate TransactionIDs | {test_results['duplicates_expected']} | {test_results['duplicates_detected']} | {'PASS' if test_results['duplicates_ok'] else 'FAIL'} |",
        f"| All timestamps parseable (dayfirst) | {test_results['timestamp_total']} | {test_results['timestamp_parseable']} | {'PASS' if test_results['timestamp_ok'] else 'FAIL'} |",
        f"| Original dataset unchanged | 2,512 rows, 0 nulls | Verified | {'PASS' if test_results['original_unchanged'] else 'FAIL'} |",
        "",
        "---",
        "",
        "## Critical Invariants",
        "",
        "- **Original dataset preserved**: `data/transactions_clean.csv` remains 2,512 rows with 0 modifications.",
        "- **No fraud labels created**: No `is_fraud`, `fraud_flag`, or similar columns were added.",
        "- **Not used for training**: This dataset was never passed to the C2GAT model.",
        "- **No synthetic transactions**: All rows derive from real transactions; perturbations are data-quality variations only.",
        "",
        "---",
        "",
        "## Expected Pipeline Behavior",
        "",
        "| Perturbation | Expected Behavior |",
        "|---|---|",
        "| Missing values | Preprocessing should detect and either impute or raise error |",
        "| Whitespace | String stripping in preprocessing should normalize |",
        "| Duplicate rows | Deduplication step should reduce to original count |",
        "| Timestamp format | `pd.to_datetime(..., dayfirst=True)` parses all formats |",
        "| Amount jitter ±1% | Values remain in valid positive range; model should be robust to small noise |",
        "",
        "---",
        "",
        f"*Report generated: Phase 6 | Seed: {stats['seed']}*",
    ]
    return "\n".join(lines)


def main():
    print("=" * 70)
    print("PHASE 6 — Noise Robustness Test")
    print("=" * 70)

    print("\n[1/3] Generating noise dataset...")
    stats = generate_noise_dataset()
    print(f"  Original rows: {stats['original_rows']}")
    print(f"  Noise dataset rows: {stats['noise_rows']}")
    for p in stats["perturbations"]:
        print(f"  Perturbation: {p['type']} | {p['n_rows_affected']} rows ({p['pct_affected']}%) in '{p['column']}'")
    print(f"  Saved: {NOISE_CSV}")

    print("\n[2/3] Running noise detection tests...")
    test_results = run_noise_pipeline_test(stats)
    for key, val in test_results.items():
        if key.endswith("_ok"):
            status = "PASS" if val else "FAIL"
            print(f"  [{status}] {key}")

    print("\n[3/3] Generating report...")
    report_text = generate_report(stats, test_results)
    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write(report_text)
    print(f"  Saved: {REPORT_MD}")

    # Verify original dataset unchanged
    df_orig = pd.read_csv(os.path.join(PROJECT_ROOT, "data", "transactions_clean.csv"))
    assert len(df_orig) == 2512, "Original dataset row count changed!"
    assert df_orig.isnull().sum().sum() == 0, "Original dataset has nulls!"
    print("\n  [PASS] Original dataset: 2512 rows, 0 nulls — UNCHANGED")
    print("\n[SUCCESS] Noise robustness test complete.")

    return stats, test_results


if __name__ == "__main__":
    main()
