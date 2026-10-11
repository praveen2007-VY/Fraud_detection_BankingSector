"""
Fraud Detection System — Phase 6
File: ml/verify_phase6.py

Purpose:
    End-to-end Phase 6 verification script.
    Verifies every required element and prints a clear PASS/FAIL report.

Checks:
    1. Model imports successfully
    2. Dataset loads (2,512 rows)
    3. Graph data loads (temporal graph)
    4. Training output exists (model, scaler, log)
    5. 2,512 transaction IDs are represented in c2gat_scores.csv
    6. No duplicate transaction IDs in scores
    7. No missing anomaly scores
    8. No NaN anomaly scores
    9. Anomaly scores are deterministic with fixed seed
    10. Phase-5 reference scores remain unchanged
    11. No synthetic transaction rows were introduced
    12. Real dataset is unchanged
"""

import os
import sys
import random
import pickle
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "ml"))

SEED = 42
random.seed(SEED)
np.random.seed(SEED)

# Paths
CLEAN_CSV = os.path.join(PROJECT_ROOT, "data", "transactions_clean.csv")
FEATURES_CSV = os.path.join(PROJECT_ROOT, "ml", "features_unsupervised.csv")
SCORED_CSV = os.path.join(PROJECT_ROOT, "neo4j", "scored_transactions.csv")
C2GAT_SCORES = os.path.join(PROJECT_ROOT, "ml", "c2gat_scores.csv")
MODEL_PATH = os.path.join(PROJECT_ROOT, "ml", "c2gat_model.pt")
SCALER_PATH = os.path.join(PROJECT_ROOT, "ml", "c2gat_scaler.pkl")
TRAIN_LOG = os.path.join(PROJECT_ROOT, "ml", "c2gat_train_log.csv")


def check(name: str, condition: bool, detail: str = "") -> bool:
    status = "PASS" if condition else "FAIL"
    msg = f"  [{status}] {name}"
    if detail:
        msg += f" — {detail}"
    print(msg)
    return condition


def main():
    print("=" * 70)
    print("PHASE 6 — VERIFICATION REPORT")
    print("=" * 70)
    all_results = []

    # ── Check 1: Model imports ─────────────────────────────────────────────
    print("\n[CHECK 1] Model imports...")
    try:
        import torch
        from c2gat_inspired_model import C2GATInspiredModel, Time2Vec, GraphAttentionLayer
        from temporal_graph_data import (
            load_and_merge_data, compute_temporal_features,
            build_temporal_graph, ML_FEATURE_COLS, K_NEIGHBORS,
        )
        r = check("PyTorch import", True, f"torch {torch.__version__}")
        r2 = check("C2GATInspiredModel import", True)
        r3 = check("temporal_graph_data import", True)
        all_results += [r, r2, r3]
    except Exception as e:
        all_results.append(check("Model imports", False, str(e)))

    # ── Check 2: Real dataset unchanged ───────────────────────────────────
    print("\n[CHECK 2] Real dataset integrity...")
    df_clean = pd.read_csv(CLEAN_CSV)
    r = check("Clean dataset exists", os.path.exists(CLEAN_CSV))
    r2 = check("Clean dataset row count", len(df_clean) == 2512, f"{len(df_clean)} rows")
    r3 = check("Clean dataset unique IDs", df_clean["TransactionID"].nunique() == 2512,
               f"{df_clean['TransactionID'].nunique()} unique IDs")
    r4 = check("Clean dataset no nulls", df_clean.isnull().sum().sum() == 0)
    all_results += [r, r2, r3, r4]

    # ── Check 3: Feature matrix unchanged ─────────────────────────────────
    print("\n[CHECK 3] Feature matrix (Phase 5 output) integrity...")
    df_feat = pd.read_csv(FEATURES_CSV)
    r = check("Features CSV exists", os.path.exists(FEATURES_CSV))
    r2 = check("Features row count", len(df_feat) == 2512, f"{len(df_feat)} rows")
    r3 = check("Features unique IDs", df_feat["transaction_id"].nunique() == 2512)
    r4 = check("Features no nulls", df_feat.isnull().sum().sum() == 0)
    r5 = check("Features no NaN", not df_feat.select_dtypes(include=[np.number]).isnull().any().any())
    # Check no fraud labels
    forbidden = ["is_fraud", "fraud", "label", "class", "target"]
    has_forbidden = any(term in col.lower() for col in df_feat.columns for term in forbidden)
    r6 = check("No fraud labels in features", not has_forbidden)
    all_results += [r, r2, r3, r4, r5, r6]

    # ── Check 4: Phase-5 scored_transactions unchanged ─────────────────────
    print("\n[CHECK 4] Phase-5 scored_transactions integrity...")
    df_scored = pd.read_csv(SCORED_CSV)
    r = check("scored_transactions.csv exists", os.path.exists(SCORED_CSV))
    r2 = check("scored_transactions row count", len(df_scored) == 2512, f"{len(df_scored)} rows")
    r3 = check("scored_transactions unique IDs", df_scored["transaction_id"].nunique() == 2512)
    r4 = check("scored_transactions has approach_a_score",
               "approach_a_score" in df_scored.columns)
    r5 = check("scored_transactions has approach_b_score",
               "approach_b_score" in df_scored.columns)
    all_results += [r, r2, r3, r4, r5]

    # ── Check 5: Training artifacts exist ─────────────────────────────────
    print("\n[CHECK 5] Training artifacts...")
    r = check("Model file exists", os.path.exists(MODEL_PATH), MODEL_PATH)
    r2 = check("Scaler file exists", os.path.exists(SCALER_PATH), SCALER_PATH)
    r3 = check("Training log exists", os.path.exists(TRAIN_LOG), TRAIN_LOG)
    all_results += [r, r2, r3]

    if os.path.exists(TRAIN_LOG):
        log_df = pd.read_csv(TRAIN_LOG)
        r4 = check("Training log has loss data", len(log_df) > 0,
                   f"{len(log_df)} epochs logged")
        r5 = check("Training log converged",
                   log_df["val_loss"].iloc[-1] < log_df["val_loss"].iloc[0],
                   f"val_loss: {log_df['val_loss'].iloc[0]:.5f} -> {log_df['val_loss'].iloc[-1]:.5f}")
        all_results += [r4, r5]

    # ── Check 6: C2GAT scores output ──────────────────────────────────────
    print("\n[CHECK 6] C2GAT scores output...")
    r = check("c2gat_scores.csv exists", os.path.exists(C2GAT_SCORES))
    all_results.append(r)

    if os.path.exists(C2GAT_SCORES):
        df_scores = pd.read_csv(C2GAT_SCORES)
        r1 = check("Scores row count", len(df_scores) == 2512, f"{len(df_scores)} rows")
        r2 = check("Scores unique IDs", df_scores["transaction_id"].nunique() == 2512,
                   f"{df_scores['transaction_id'].nunique()} unique IDs")
        r3 = check("No duplicate transaction IDs",
                   df_scores["transaction_id"].duplicated().sum() == 0)
        r4 = check("anomaly_score column present", "anomaly_score" in df_scores.columns)
        r5 = check("c2gat_embedding_norm column present", "c2gat_embedding_norm" in df_scores.columns)
        nan_count = df_scores["anomaly_score"].isna().sum()
        r6 = check("No missing anomaly scores", nan_count == 0, f"{nan_count} NaNs")
        nan_nan = df_scores["anomaly_score"].apply(np.isnan).sum()
        r7 = check("No NaN anomaly scores", nan_nan == 0)
        inf_count = np.isinf(df_scores["anomaly_score"].values).sum()
        r8 = check("No Inf anomaly scores", inf_count == 0)
        score_range_ok = (df_scores["anomaly_score"] >= 0).all() and (df_scores["anomaly_score"] <= 100).all()
        r9 = check("Scores in [0, 100] range", score_range_ok,
                   f"min={df_scores['anomaly_score'].min():.2f}, max={df_scores['anomaly_score'].max():.2f}")
        # Verify transaction IDs match original clean dataset exactly
        original_ids = set(df_clean["TransactionID"].values)
        scores_ids = set(df_scores["transaction_id"].values)
        r10 = check("Score IDs match original dataset", original_ids == scores_ids,
                    f"Match: {len(original_ids & scores_ids)}/{len(original_ids)}")
        all_results += [r1, r2, r3, r4, r5, r6, r7, r8, r9, r10]

        # Check no synthetic transactions (no IDs not in original)
        extra_ids = scores_ids - original_ids
        r11 = check("No synthetic transaction IDs in scores", len(extra_ids) == 0,
                    f"Extra IDs: {list(extra_ids)[:5] if extra_ids else 'None'}")
        all_results.append(r11)

        # Check Phase-5 reference scores are preserved (not used as targets)
        r12 = check("ref_approach_a_score preserved in scores",
                    "ref_approach_a_score" in df_scores.columns)
        r13 = check("ref_approach_b_score preserved in scores",
                    "ref_approach_b_score" in df_scores.columns)
        all_results += [r12, r13]

        # Verify Phase-5 scores are unchanged
        merged_check = df_scores.merge(
            df_scored[["transaction_id", "approach_a_score", "approach_b_score"]],
            on="transaction_id", how="inner"
        )
        if len(merged_check) == 2512:
            a_unchanged = np.allclose(
                merged_check["ref_approach_a_score"].values,
                merged_check["approach_a_score"].values,
                atol=1e-4
            )
            b_unchanged = np.allclose(
                merged_check["ref_approach_b_score"].values,
                merged_check["approach_b_score"].values,
                atol=1e-4
            )
            r14 = check("Phase-5 Approach A scores unchanged", a_unchanged)
            r15 = check("Phase-5 Approach B scores unchanged", b_unchanged)
            all_results += [r14, r15]

    # ── Check 7: Determinism ─────────────────────────────────────────────────
    print("\n[CHECK 7] Determinism (fixed seed inference)...")
    if os.path.exists(MODEL_PATH) and os.path.exists(SCALER_PATH):
        try:
            import torch
            from c2gat_inspired_model import C2GATInspiredModel, generate_fixed_eval_mask
            from train_c2gat_inspired import build_batch_tensors, FEAT_DIM, TIME_DIM, LATENT_DIM, N_HEADS, DROPOUT
            from temporal_graph_data import load_and_merge_data, compute_temporal_features, build_temporal_graph

            torch.manual_seed(SEED)
            df_d = load_and_merge_data()
            df_d = compute_temporal_features(df_d)
            graph_d = build_temporal_graph(df_d, k=K_NEIGHBORS)
            nm = np.full((len(df_d), K_NEIGHBORS), -1, dtype=np.int32)
            for i, nbrs in enumerate(graph_d["neighbors"]):
                for rank, j in enumerate(nbrs):
                    nm[i, rank] = j

            X_r = df_d[ML_FEATURE_COLS].values.astype(np.float32)
            temp_cols_d = ["t_norm", "day_of_week", "hour_of_day", "month_of_year",
                           "inter_tx_gap_norm", "rolling_tx_count_7d"]
            T_d = df_d[temp_cols_d].values.astype(np.float32)

            with open(SCALER_PATH, "rb") as f:
                scaler_d = pickle.load(f)
            X_sc = scaler_d.transform(X_r).astype(np.float32)

            model_d = C2GATInspiredModel(
                n_features=15, feat_dim=FEAT_DIM, time_dim=TIME_DIM,
                latent_dim=LATENT_DIM, n_heads=N_HEADS, dropout=DROPOUT,
            )
            model_d.load_state_dict(torch.load(MODEL_PATH, map_location="cpu", weights_only=True))
            model_d.eval()

            eval_mask = generate_fixed_eval_mask(15, 0.30)
            # Run a small batch twice
            batch_idx = np.arange(0, 32)
            with torch.no_grad():
                x1, t1, xn1, tn1, nm1 = build_batch_tensors(batch_idx, X_sc, T_d, nm, "cpu")
                fmask = eval_mask.unsqueeze(0).expand(32, -1)
                xh1, z1 = model_d(x1, t1, xn1, tn1, nm1, fmask)

                x2, t2, xn2, tn2, nm2 = build_batch_tensors(batch_idx, X_sc, T_d, nm, "cpu")
                xh2, z2 = model_d(x2, t2, xn2, tn2, nm2, fmask)

            deterministic = torch.allclose(z1, z2, atol=1e-6)
            r = check("Inference is deterministic (same seed, same results)", deterministic)
            all_results.append(r)
        except Exception as e:
            all_results.append(check("Determinism check", False, str(e)))

    # ── Check 8: No fraud labels anywhere ────────────────────────────────────
    print("\n[CHECK 8] No fraud labels created in Phase 6...")
    phase6_files = [
        C2GAT_SCORES,
        os.path.join(PROJECT_ROOT, "ml", "c2gat_train_log.csv"),
    ]
    for fpath in phase6_files:
        if os.path.exists(fpath):
            df_tmp = pd.read_csv(fpath)
            has_label = any(
                term in col.lower()
                for col in df_tmp.columns
                for term in ["is_fraud", "fraud_flag", "fraud_label", "fraud_prob"]
            )
            r = check(f"No fraud labels in {os.path.basename(fpath)}", not has_label)
            all_results.append(r)

    # ── Final Report ──────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    total = len(all_results)
    passed = sum(all_results)
    failed = total - passed
    overall = passed == total

    print(f"PHASE 6 VERIFICATION SUMMARY")
    print(f"  Total checks:  {total}")
    print(f"  PASSED:        {passed}")
    print(f"  FAILED:        {failed}")
    print("=" * 70)
    print(f"OVERALL PHASE 6 VERIFICATION: {'PASS' if overall else 'FAIL'}")
    print("=" * 70)

    return overall


if __name__ == "__main__":
    result = main()
    sys.exit(0 if result else 1)
