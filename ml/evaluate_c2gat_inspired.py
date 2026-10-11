"""
Fraud Detection System — Phase 6
File: ml/evaluate_c2gat_inspired.py

Purpose:
    Run inference on trained C2GAT-inspired model to:
    1. Generate per-transaction anomaly scores
    2. Compute embedding statistics
    3. Save ml/c2gat_scores.csv
    4. Compare with Phase-5 reference scores

IMPORTANT:
    - Anomaly scores are NOT fraud probabilities
    - They are learned risk signals / representation-based anomaly scores
    - No fraud labels are created or inferred
    - Phase-5 scores are reference comparisons, NOT ground truth
"""

import os
import sys
import pickle
import random
import numpy as np
import pandas as pd
import torch
from scipy.stats import spearmanr

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "ml"))

from temporal_graph_data import (
    load_and_merge_data,
    compute_temporal_features,
    build_temporal_graph,
    ML_FEATURE_COLS,
    K_NEIGHBORS,
)
from c2gat_inspired_model import (
    C2GATInspiredModel,
    generate_fixed_eval_mask,
)
from train_c2gat_inspired import (
    build_batch_tensors,
    FEAT_DIM, TIME_DIM, LATENT_DIM, N_HEADS, DROPOUT,
    MODEL_PATH, SCALER_PATH,
)

SEED = 42
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)

SCORES_CSV = os.path.join(PROJECT_ROOT, "ml", "c2gat_scores.csv")
DEVICE = "cpu"
BATCH_SIZE = 64


def run_inference(
    model: C2GATInspiredModel,
    X_scaled: np.ndarray,
    T: np.ndarray,
    neighbor_matrix: np.ndarray,
    eval_mask: torch.Tensor,
) -> tuple:
    """
    Run full-dataset inference and collect anomaly scores + embeddings.

    Args:
        eval_mask: fixed single-sample mask (n_features,) — applied uniformly

    Returns:
        anomaly_scores: (N,) — reconstruction MSE per transaction
        embeddings: (N, latent_dim) — latent z vectors
        embedding_norms: (N,) — L2 norm of z
    """
    model.eval()
    n = len(X_scaled)
    all_scores = []
    all_embeddings = []

    with torch.no_grad():
        for start in range(0, n, BATCH_SIZE):
            batch_idx = np.arange(start, min(start + BATCH_SIZE, n))
            x, t, x_nbrs, t_nbrs, nbr_mask = build_batch_tensors(
                batch_idx, X_scaled, T, neighbor_matrix, DEVICE
            )

            # Apply the same fixed mask to every sample in the batch
            B = len(batch_idx)
            feature_mask = eval_mask.unsqueeze(0).expand(B, -1)  # (B, 15)

            x_hat, z = model(x, t, x_nbrs, t_nbrs, nbr_mask, feature_mask)

            # Per-sample reconstruction error (mean over masked features)
            diff = (x - x_hat) ** 2  # (B, 15)
            # Only masked positions contribute to score
            masked_diff = diff * feature_mask.float()
            n_masked = feature_mask.float().sum(dim=1).clamp(min=1)
            sample_score = (masked_diff.sum(dim=1) / n_masked).cpu().numpy()

            all_scores.append(sample_score)
            all_embeddings.append(z.cpu().numpy())

    anomaly_scores = np.concatenate(all_scores)
    embeddings = np.concatenate(all_embeddings, axis=0)
    embedding_norms = np.linalg.norm(embeddings, axis=1)

    return anomaly_scores, embeddings, embedding_norms


def main():
    print("=" * 70)
    print("PHASE 6 — C2GAT-Inspired Evaluation & Anomaly Scoring")
    print("=" * 70)

    # ── Load data ─────────────────────────────────────────────────────────────
    print("\n[1/6] Loading data...")
    df = load_and_merge_data()
    df = compute_temporal_features(df)
    graph = build_temporal_graph(df, k=K_NEIGHBORS)

    neighbor_matrix = np.full((len(df), K_NEIGHBORS), -1, dtype=np.int32)
    for i, neighbors in enumerate(graph["neighbors"]):
        for rank, j in enumerate(neighbors):
            neighbor_matrix[i, rank] = j

    X_raw = df[ML_FEATURE_COLS].values.astype(np.float32)
    temp_cols = ["t_norm", "day_of_week", "hour_of_day", "month_of_year",
                 "inter_tx_gap_norm", "rolling_tx_count_7d"]
    T = df[temp_cols].values.astype(np.float32)
    print(f"  Loaded {len(df)} transactions.")

    # ── Load scaler ────────────────────────────────────────────────────────────
    print("\n[2/6] Loading scaler and scaling features...")
    assert os.path.exists(SCALER_PATH), f"Scaler not found: {SCALER_PATH}. Run train first."
    with open(SCALER_PATH, "rb") as f:
        scaler = pickle.load(f)
    X_scaled = scaler.transform(X_raw).astype(np.float32)
    print(f"  Features scaled using pre-fitted StandardScaler.")

    # ── Load model ─────────────────────────────────────────────────────────────
    print("\n[3/6] Loading trained model...")
    assert os.path.exists(MODEL_PATH), f"Model not found: {MODEL_PATH}. Run train first."
    model = C2GATInspiredModel(
        n_features=15, feat_dim=FEAT_DIM, time_dim=TIME_DIM,
        latent_dim=LATENT_DIM, n_heads=N_HEADS, dropout=DROPOUT,
    ).to(DEVICE)
    model.load_state_dict(torch.load(MODEL_PATH, map_location=DEVICE, weights_only=True))
    total_params = sum(p.numel() for p in model.parameters())
    print(f"  Model loaded. Parameters: {total_params:,}")

    # ── Generate fixed eval mask ─────────────────────────────────────────────
    eval_mask = generate_fixed_eval_mask(n_features=15, mask_ratio=0.30)
    masked_features = [ML_FEATURE_COLS[i] for i in range(15) if eval_mask[i].item()]
    print(f"\n[4/6] Evaluation mask (fixed, seed=42):")
    print(f"  Masked {eval_mask.sum().item()} of 15 features: {masked_features}")

    # ── Run inference ─────────────────────────────────────────────────────────
    print(f"\n[5/6] Running inference on all {len(df)} transactions...")
    anomaly_scores, embeddings, embedding_norms = run_inference(
        model, X_scaled, T, neighbor_matrix, eval_mask
    )
    print(f"  Anomaly scores shape: {anomaly_scores.shape}")
    print(f"  Embeddings shape: {embeddings.shape}")

    # Normalize anomaly score to [0, 100] for interpretability
    score_min = anomaly_scores.min()
    score_max = anomaly_scores.max()
    anomaly_score_normalized = 100.0 * (anomaly_scores - score_min) / (score_max - score_min + 1e-9)

    # ── Assemble output CSV ───────────────────────────────────────────────────
    print(f"\n[6/6] Assembling and saving output...")
    output_df = pd.DataFrame({
        "transaction_id": df["transaction_id"].values,
        "account_id": df["account_id_x"].values,
        "timestamp": df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S"),
        "c2gat_embedding_norm": embedding_norms.round(6),
        "anomaly_score": anomaly_score_normalized.round(4),
        "anomaly_score_raw": anomaly_scores.round(8),
        "ref_approach_a_score": df["approach_a_score"].values,
        "ref_approach_b_score": df["approach_b_score"].values,
        # Temporal features (for analysis)
        "t_norm": df["t_norm"].values.round(6),
        "inter_tx_gap_norm": df["inter_tx_gap_norm"].values.round(6),
    })

    output_df.to_csv(SCORES_CSV, index=False)
    print(f"  Saved: {SCORES_CSV}")
    print(f"  Rows: {len(output_df)}")

    # ── Statistics ────────────────────────────────────────────────────────────
    print("\n--- ANOMALY SCORE STATISTICS ---")
    for p in [0, 25, 50, 75, 90, 95, 99, 100]:
        print(f"  p{p:3d}: {np.percentile(anomaly_score_normalized, p):.2f}")

    print("\n--- EMBEDDING NORM STATISTICS ---")
    print(f"  min={embedding_norms.min():.4f}, max={embedding_norms.max():.4f}, "
          f"mean={embedding_norms.mean():.4f}, std={embedding_norms.std():.4f}")

    # ── Top anomalies ─────────────────────────────────────────────────────────
    print("\n--- TOP 10 ANOMALOUS TRANSACTIONS ---")
    top10 = output_df.nlargest(10, "anomaly_score")[
        ["transaction_id", "account_id", "timestamp", "anomaly_score",
         "c2gat_embedding_norm", "ref_approach_a_score", "ref_approach_b_score"]
    ]
    print(top10.to_string(index=False))

    # ── Phase-5 Correlation ───────────────────────────────────────────────────
    print("\n--- PHASE-5 COMPARISON (Spearman Rank Correlation) ---")
    valid_mask = ~(np.isnan(output_df["ref_approach_a_score"]) |
                   np.isnan(output_df["ref_approach_b_score"]))
    rho_a, p_a = spearmanr(
        output_df.loc[valid_mask, "anomaly_score"],
        output_df.loc[valid_mask, "ref_approach_a_score"]
    )
    rho_b, p_b = spearmanr(
        output_df.loc[valid_mask, "anomaly_score"],
        output_df.loc[valid_mask, "ref_approach_b_score"]
    )
    print(f"  C2GAT vs Approach A: rho={rho_a:.4f}, p={p_a:.4f}")
    print(f"  C2GAT vs Approach B: rho={rho_b:.4f}, p={p_b:.4f}")
    print(f"  NOTE: Correlation analysis only — Phase-5 scores are NOT ground truth.")

    # ── Rank overlap analysis ─────────────────────────────────────────────────
    print("\n--- TOP-N RANK OVERLAP (Top 50 = ~2% of 2,512) ---")
    top50_c2gat = set(output_df.nlargest(50, "anomaly_score")["transaction_id"])
    top50_a = set(output_df.nlargest(50, "ref_approach_a_score")["transaction_id"])
    top50_b = set(output_df.nlargest(50, "ref_approach_b_score")["transaction_id"])
    print(f"  C2GAT top-50 overlap with Approach A top-50: {len(top50_c2gat & top50_a)} transactions")
    print(f"  C2GAT top-50 overlap with Approach B top-50: {len(top50_c2gat & top50_b)} transactions")
    print(f"  C2GAT-only (not in A or B top-50): {len(top50_c2gat - top50_a - top50_b)} transactions")

    print("\n[SUCCESS] Evaluation complete.")
    return output_df


if __name__ == "__main__":
    main()
