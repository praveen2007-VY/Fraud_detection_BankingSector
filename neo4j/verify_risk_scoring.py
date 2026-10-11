"""
Fraud Detection System — Verification Script for Risk Scoring Engine
File: neo4j/verify_risk_scoring.py

Verifies:
1. Exactly 2,512 transaction scores generated.
2. No duplicate Transaction IDs.
3. No missing Transaction IDs (TX000001 through TX002512).
4. No NaN / null values.
5. Approach A in [0, 100], Approach B in [0, 100].
6. Full explainability attribution on all transactions.
7. Candidate risk band distributions.
8. Top 20 highest Approach A and Approach B scores.
9. Identification of all 4-signal transactions and approach overlap.
"""

import importlib.util
import os
import sys
import numpy as np
import pandas as pd

# Load risk_scoring module directly to avoid collision with installed pip 'neo4j' package
_script_dir = os.path.dirname(os.path.abspath(__file__))
_scoring_path = os.path.join(_script_dir, "risk_scoring.py")
_spec = importlib.util.spec_from_file_location("risk_scoring_module", _scoring_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
RiskScoringEngine = _mod.RiskScoringEngine

sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def verify_risk_scoring():
    print("=" * 80)
    print("PHASE 5 — STEP 4: RISK SCORING VERIFICATION")
    print("=" * 80)

    with RiskScoringEngine() as engine:
        print("[1/5] Querying Neo4j and calculating risk scores across all transactions...")
        df = engine.score_all_transactions()

    total_count = len(df)
    print(f"Total transactions scored: {total_count}")

    # Check 1: Count == 2512
    assert total_count == 2512, f"Expected 2512 transactions, got {total_count}"
    print("  [PASS] Transaction count = 2512")

    # Check 2: No duplicate IDs
    unique_ids = df['transaction_id'].nunique()
    dups = total_count - unique_ids
    assert dups == 0, f"Found {dups} duplicate transaction IDs"
    print(f"  [PASS] Unique Transaction IDs = {unique_ids}, Duplicates = {dups}")

    # Check 3: Expected ID set TX000001 to TX002512
    expected_ids = {f"TX{i:06d}" for i in range(1, 2513)}
    actual_ids = set(df['transaction_id'])
    missing_ids = expected_ids - actual_ids
    assert len(missing_ids) == 0, f"Missing IDs: {missing_ids}"
    print(f"  [PASS] Missing IDs = 0 (Complete range TX000001 to TX002512 verified)")

    # Check 4: No NaN / Nulls
    null_counts = df.isnull().sum().to_dict()
    has_nulls = any(v > 0 for v in null_counts.values())
    assert not has_nulls, f"Found null values: {null_counts}"
    print("  [PASS] No NaN / Null values in any column")

    # Check 5: Score bounds [0, 100]
    min_a, max_a = df['approach_a_score'].min(), df['approach_a_score'].max()
    min_b, max_b = df['approach_b_score'].min(), df['approach_b_score'].max()
    assert 0.0 <= min_a and max_a <= 100.0, f"Approach A score out of bounds: [{min_a}, {max_a}]"
    assert 0.0 <= min_b and max_b <= 100.0, f"Approach B score out of bounds: [{min_b}, {max_b}]"
    print(f"  [PASS] Approach A range: [{min_a:.2f}, {max_a:.2f}] (within [0, 100])")
    print(f"  [PASS] Approach B range: [{min_b:.2f}, {max_b:.2f}] (within [0, 100])")

    # Check 6: Explainability attribution check
    empty_reasons = (df['risk_reasons'].str.strip() == '').sum()
    assert empty_reasons == 0, f"Found {empty_reasons} transactions with missing risk reasons"
    print(f"  [PASS] 100% of transactions have explainable risk reasons (0 empty)")

    # Distribution summaries
    print("\n" + "=" * 80)
    print("SCORE DISTRIBUTION SUMMARY")
    print("=" * 80)
    def get_summary(series, label):
        return {
            "Model": label,
            "Min": float(series.min()),
            "Max": float(series.max()),
            "Mean": round(float(series.mean()), 2),
            "Median": round(float(series.median()), 2),
            "p75": round(float(series.quantile(0.75)), 2),
            "p90": round(float(series.quantile(0.90)), 2),
            "p95": round(float(series.quantile(0.95)), 2),
            "p99": round(float(series.quantile(0.99)), 2),
            "Std Dev": round(float(series.std()), 2)
        }
    dist_df = pd.DataFrame([
        get_summary(df['approach_a_score'], "Approach A (Normalized Composite)"),
        get_summary(df['approach_b_score'], "Approach B (Additive Points)")
    ])
    print(dist_df.to_string(index=False))

    # Candidate Risk Bands
    print("\n" + "=" * 80)
    print("CANDIDATE RISK BANDS BREAKDOWN")
    print("=" * 80)
    print("Candidate Risk Bands definition for exploratory evaluation:")
    print("  - Low Risk: [0, 30)")
    print("  - Medium Risk: [30, 50)")
    print("  - High Risk: [50, 70)")
    print("  - Critical Risk: [70, 100]")

    def band_counts(series):
        low = ((series >= 0) & (series < 30)).sum()
        med = ((series >= 30) & (series < 50)).sum()
        high = ((series >= 50) & (series < 70)).sum()
        crit = ((series >= 70) & (series <= 100)).sum()
        return [low, med, high, crit]

    bands_a = band_counts(df['approach_a_score'])
    bands_b = band_counts(df['approach_b_score'])

    band_table = pd.DataFrame({
        "Risk Band": ["Low Risk [0, 30)", "Medium Risk [30, 50)", "High Risk [50, 70)", "Critical Risk [70, 100]"],
        "Approach A Tx Count": bands_a,
        "Approach A %": [round(c / total_count * 100, 2) for c in bands_a],
        "Approach B Tx Count": bands_b,
        "Approach B %": [round(c / total_count * 100, 2) for c in bands_b],
    })
    print(band_table.to_string(index=False))

    # Correlation between Approach A and Approach B
    corr_pearson = round(float(df['approach_a_score'].corr(df['approach_b_score'], method='pearson')), 4)
    corr_spearman = round(float(df['approach_a_score'].corr(df['approach_b_score'], method='spearman')), 4)
    print(f"\nCorrelation between Approach A and B:")
    print(f"  - Pearson r: {corr_pearson}")
    print(f"  - Spearman rho: {corr_spearman}")

    # Top 20 Highest Approach A scores
    print("\n" + "=" * 80)
    print("TOP 20 HIGHEST APPROACH A SCORES")
    print("=" * 80)
    top_a = df.sort_values(by='approach_a_score', ascending=False).head(20)
    print(top_a[['transaction_id', 'account_id', 'transaction_amount', 'approach_a_score', 'approach_b_score', 'approach_a_prominent_factors']].to_string(index=False))

    # Top 20 Highest Approach B scores
    print("\n" + "=" * 80)
    print("TOP 20 HIGHEST APPROACH B SCORES")
    print("=" * 80)
    top_b = df.sort_values(by=['approach_b_score', 'approach_a_score'], ascending=[False, False]).head(20)
    print(top_b[['transaction_id', 'account_id', 'transaction_amount', 'approach_b_score', 'approach_a_score', 'risk_reasons']].to_string(index=False))

    # Transactions containing ALL 4 Core Signals:
    # 1. Shared Device (>1)
    # 2. Shared IP (>1)
    # 3. High Value (> 589.54)
    # 4. Rapid Velocity (>= 1 in 24h)
    core_4 = df[
        (df['shared_device_accounts'] > 1) &
        (df['shared_ip_accounts'] > 1) &
        (df['transaction_amount'] > 589.54) &
        (df['rapid_velocity_count_24h'] >= 1)
    ].sort_values(by=['approach_b_score', 'approach_a_score'], ascending=[False, False])

    print("\n" + "=" * 80)
    print(f"TRANSACTIONS WITH ALL 4 CORE SIGNALS (N = {len(core_4)})")
    print("=" * 80)
    print(core_4[['transaction_id', 'account_id', 'transaction_amount', 'shared_device_accounts', 'shared_ip_accounts', 'rapid_velocity_count_24h', 'approach_a_score', 'approach_b_score']].to_string(index=False))

    # Save verified scores to a reference dataset
    output_path = "neo4j/scored_transactions.csv"
    df.to_csv(output_path, index=False)
    print(f"\n[DONE] Saved scored dataset with explainability to {output_path}")

    return {
        "count": total_count,
        "duplicates": dups,
        "missing": len(missing_ids),
        "nulls": sum(null_counts.values()),
        "approach_a_bounds": [min_a, max_a],
        "approach_b_bounds": [min_b, max_b],
        "correlation_pearson": corr_pearson,
        "core_4_count": len(core_4)
    }


if __name__ == "__main__":
    verify_risk_scoring()
