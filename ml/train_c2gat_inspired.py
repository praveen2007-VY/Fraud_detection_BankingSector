"""
Fraud Detection System — Phase 6
File: ml/train_c2gat_inspired.py

Purpose:
    Train the C2GAT-inspired self-supervised model on real transaction data.

Training procedure:
    - Chronological 80/20 train/val split (no random leakage between future/past)
    - Self-supervised masked feature reconstruction objective (MSE on masked positions)
    - StandardScaler fitted on training data only (no test-set contamination)
    - Fixed random seed (42) for deterministic reproducibility
    - Early stopping on validation loss

Output:
    ml/c2gat_model.pt         — saved model state dict
    ml/c2gat_scaler.pkl       — fitted StandardScaler
    ml/c2gat_train_log.csv    — loss curve per epoch

CRITICAL CONSTRAINTS:
    - NO synthetic transactions used
    - NO fraud labels created or used
    - Temporal order strictly respected in train/val split
    - Phase-5 reference scores NOT used as training targets
"""

import os
import sys
import random
import time
import pickle
import numpy as np
import pandas as pd
import torch
import torch.optim as optim

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
    generate_feature_mask,
)

# ── Reproducibility ──────────────────────────────────────────────────────────
SEED = 42
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed_all(SEED)

# ── Paths ────────────────────────────────────────────────────────────────────
MODEL_PATH = os.path.join(PROJECT_ROOT, "ml", "c2gat_model.pt")
SCALER_PATH = os.path.join(PROJECT_ROOT, "ml", "c2gat_scaler.pkl")
TRAIN_LOG_PATH = os.path.join(PROJECT_ROOT, "ml", "c2gat_train_log.csv")

# ── Hyperparameters ───────────────────────────────────────────────────────────
TRAIN_RATIO = 0.80          # Chronological split: 80% train, 20% val
EPOCHS = 150
BATCH_SIZE = 64
LR = 1e-3
MASK_RATIO = 0.30
EARLY_STOP_PATIENCE = 25
LR_PATIENCE = 15
LR_FACTOR = 0.5
DROPOUT = 0.1
FEAT_DIM = 32
TIME_DIM = 16
LATENT_DIM = 64
N_HEADS = 2
DEVICE = "cpu"  # GPU unavailable (DLL init error on this machine)


def build_batch_tensors(
    indices: np.ndarray,
    X_scaled: np.ndarray,
    T: np.ndarray,
    neighbor_matrix: np.ndarray,
    device: str = "cpu",
):
    """
    Build tensors for a batch of transaction indices.

    Returns:
        x:        (B, 15) float32
        t:        (B,) float32
        x_nbrs:   (B, k, 15) float32
        t_nbrs:   (B, k) float32
        nbr_mask: (B, k) bool
    """
    B = len(indices)
    k = neighbor_matrix.shape[1]

    x = torch.tensor(X_scaled[indices], dtype=torch.float32, device=device)
    t = torch.tensor(T[indices, 0], dtype=torch.float32, device=device)  # t_norm

    x_nbrs_np = np.zeros((B, k, X_scaled.shape[1]), dtype=np.float32)
    t_nbrs_np = np.zeros((B, k), dtype=np.float32)
    nbr_mask_np = np.zeros((B, k), dtype=bool)

    for b, idx in enumerate(indices):
        neighbors = neighbor_matrix[idx]  # (k,) with -1 for padding
        valid = neighbors >= 0
        nbr_mask_np[b] = valid
        x_nbrs_np[b, valid] = X_scaled[neighbors[valid]]
        t_nbrs_np[b, valid] = T[neighbors[valid], 0]  # t_norm of neighbors

    x_nbrs = torch.tensor(x_nbrs_np, dtype=torch.float32, device=device)
    t_nbrs = torch.tensor(t_nbrs_np, dtype=torch.float32, device=device)
    nbr_mask = torch.tensor(nbr_mask_np, dtype=torch.bool, device=device)

    return x, t, x_nbrs, t_nbrs, nbr_mask


def train():
    print("=" * 70)
    print("PHASE 6 — C2GAT-Inspired Model Training")
    print("=" * 70)
    print(f"\nConfiguration:")
    print(f"  Device:       {DEVICE}")
    print(f"  Random seed:  {SEED}")
    print(f"  Epochs:       {EPOCHS} (early stop patience={EARLY_STOP_PATIENCE})")
    print(f"  Batch size:   {BATCH_SIZE}")
    print(f"  LR:           {LR}")
    print(f"  Mask ratio:   {MASK_RATIO}")
    print(f"  Train/val:    {int(TRAIN_RATIO*100)}/{int((1-TRAIN_RATIO)*100)} (chronological)")

    # ── Step 1: Load data ────────────────────────────────────────────────────
    print("\n[1/6] Loading and preparing data...")
    df = load_and_merge_data()
    df = compute_temporal_features(df)
    print(f"  Loaded {len(df)} transactions.")
    print(f"  Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")

    # ── Step 2: Build temporal graph ─────────────────────────────────────────
    print(f"\n[2/6] Building temporal graph...")
    graph = build_temporal_graph(df, k=K_NEIGHBORS)
    neighbor_matrix = np.full((len(df), K_NEIGHBORS), -1, dtype=np.int32)
    for i, neighbors in enumerate(graph["neighbors"]):
        for rank, j in enumerate(neighbors):
            neighbor_matrix[i, rank] = j
    print(f"  Nodes: {graph['n_nodes']}, Edges: {graph['n_edges']}")

    # ── Step 3: Feature matrix and chronological split ───────────────────────
    print(f"\n[3/6] Preparing feature matrix and chronological split...")
    X_raw = df[ML_FEATURE_COLS].values.astype(np.float32)
    temp_cols = ["t_norm", "day_of_week", "hour_of_day", "month_of_year",
                 "inter_tx_gap_norm", "rolling_tx_count_7d"]
    T = df[temp_cols].values.astype(np.float32)

    n = len(df)
    n_train = int(n * TRAIN_RATIO)  # 2009 or 2010 depending on rounding
    n_val = n - n_train

    train_idx = np.arange(n_train)
    val_idx = np.arange(n_train, n)

    print(f"  Total: {n}, Train: {n_train}, Val: {n_val}")
    print(f"  Train period: {df['timestamp'].iloc[0]} to {df['timestamp'].iloc[n_train-1]}")
    print(f"  Val period:   {df['timestamp'].iloc[n_train]} to {df['timestamp'].iloc[-1]}")

    # Fit StandardScaler on training data only
    from sklearn.preprocessing import StandardScaler
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_raw)
    X_scaled = X_scaled.astype(np.float32)

    with open(SCALER_PATH, "wb") as f:
        pickle.dump(scaler, f)
    print(f"  Scaler fitted on {n_train} training samples. Saved: {SCALER_PATH}")

    # ── Step 4: Initialize model ─────────────────────────────────────────────
    print(f"\n[4/6] Initializing model...")
    model = C2GATInspiredModel(
        n_features=15,
        feat_dim=FEAT_DIM,
        time_dim=TIME_DIM,
        latent_dim=LATENT_DIM,
        n_heads=N_HEADS,
        dropout=DROPOUT,
    ).to(DEVICE)
    total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"  Total trainable parameters: {total_params:,}")

    optimizer = optim.Adam(model.parameters(), lr=LR)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode='min', patience=LR_PATIENCE, factor=LR_FACTOR
    )

    # ── Step 5: Training loop ─────────────────────────────────────────────────
    print(f"\n[5/6] Training...")
    train_log = []
    best_val_loss = float('inf')
    best_epoch = 0
    no_improve_count = 0
    start_time = time.time()

    for epoch in range(1, EPOCHS + 1):
        model.train()
        epoch_loss = 0.0
        n_batches = 0

        # Shuffle training indices each epoch (within train set only)
        rng = np.random.default_rng(SEED + epoch)
        shuffled_train = rng.permutation(train_idx)

        for start in range(0, n_train, BATCH_SIZE):
            batch_idx = shuffled_train[start:start + BATCH_SIZE]
            x, t, x_nbrs, t_nbrs, nbr_mask = build_batch_tensors(
                batch_idx, X_scaled, T, neighbor_matrix, DEVICE
            )

            # Generate random mask for this batch
            feature_mask = generate_feature_mask(
                len(batch_idx), 15, mask_ratio=MASK_RATIO, device=DEVICE
            )

            optimizer.zero_grad()
            x_hat, z = model(x, t, x_nbrs, t_nbrs, nbr_mask, feature_mask)
            loss = model.masked_reconstruction_loss(x, x_hat, feature_mask)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

            epoch_loss += loss.item()
            n_batches += 1

        train_loss = epoch_loss / max(n_batches, 1)

        # Validation
        model.eval()
        val_loss_total = 0.0
        val_batches = 0
        with torch.no_grad():
            for start in range(0, n_val, BATCH_SIZE):
                batch_idx = val_idx[start:start + BATCH_SIZE]
                x, t, x_nbrs, t_nbrs, nbr_mask = build_batch_tensors(
                    batch_idx, X_scaled, T, neighbor_matrix, DEVICE
                )
                # Fixed val mask (seed=42 for reproducibility)
                torch.manual_seed(42)
                feature_mask = generate_feature_mask(
                    len(batch_idx), 15, mask_ratio=MASK_RATIO, device=DEVICE
                )
                x_hat, z = model(x, t, x_nbrs, t_nbrs, nbr_mask, feature_mask)
                val_loss = model.masked_reconstruction_loss(x, x_hat, feature_mask)
                val_loss_total += val_loss.item()
                val_batches += 1
            torch.manual_seed(SEED)  # restore seed

        val_loss_avg = val_loss_total / max(val_batches, 1)
        current_lr = optimizer.param_groups[0]['lr']
        scheduler.step(val_loss_avg)

        train_log.append({
            "epoch": epoch,
            "train_loss": round(train_loss, 6),
            "val_loss": round(val_loss_avg, 6),
            "lr": current_lr,
        })

        if epoch % 10 == 0 or epoch == 1:
            elapsed = time.time() - start_time
            print(f"  Epoch {epoch:3d}/{EPOCHS} | "
                  f"train_loss={train_loss:.5f} | "
                  f"val_loss={val_loss_avg:.5f} | "
                  f"lr={current_lr:.6f} | "
                  f"elapsed={elapsed:.1f}s")

        # Early stopping
        if val_loss_avg < best_val_loss - 1e-6:
            best_val_loss = val_loss_avg
            best_epoch = epoch
            no_improve_count = 0
            torch.save(model.state_dict(), MODEL_PATH)
        else:
            no_improve_count += 1
            if no_improve_count >= EARLY_STOP_PATIENCE:
                print(f"\n  Early stopping at epoch {epoch} "
                      f"(best val_loss={best_val_loss:.5f} at epoch {best_epoch})")
                break

    total_time = time.time() - start_time

    # Save training log
    log_df = pd.DataFrame(train_log)
    log_df.to_csv(TRAIN_LOG_PATH, index=False)
    print(f"\n  Training complete. Best val_loss={best_val_loss:.5f} at epoch {best_epoch}")
    print(f"  Total training time: {total_time:.1f}s")
    print(f"  Model saved: {MODEL_PATH}")
    print(f"  Training log: {TRAIN_LOG_PATH}")

    # ── Step 6: Summary ───────────────────────────────────────────────────────
    print(f"\n[6/6] Training summary:")
    print(f"  Dataset: {n} transactions (real data only)")
    print(f"  Train: {n_train} | Val: {n_val}")
    print(f"  Epochs run: {len(train_log)}")
    print(f"  Best epoch: {best_epoch}")
    print(f"  Best val_loss: {best_val_loss:.6f}")
    print(f"  Final train_loss: {train_log[-1]['train_loss']:.6f}")
    print(f"\n[SUCCESS] Training complete.")

    return model, scaler, train_log


if __name__ == "__main__":
    train()
