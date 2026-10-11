"""
Fraud Detection System — Phase 6
File: ml/c2gat_inspired_model.py

Purpose:
    Implements the C2GAT-inspired self-supervised model for transaction
    anomaly detection on the real unlabeled bank transaction dataset.

Architecture:
    1. Feature Encoder:     Linear(15 -> 32) + ReLU
    2. Temporal Encoder:    Time2Vec (sinusoidal + learnable)
    3. Graph Attention:     Multi-head attention over k temporal neighbors
    4. Fusion Layer:        Concatenate [feature, temporal, context] -> z [64]
    5. Decoder:             Linear(64 -> 15) for masked feature reconstruction

Self-Supervised Objective:
    Masked Feature Reconstruction — reconstruct randomly masked input features.
    Anomaly score = per-transaction reconstruction error at inference time.

IMPORTANT DISCLAIMER:
    This is a C2GAT-inspired adaptation for unlabeled transaction anomaly
    detection, NOT a reproduction of the original C2GAT fraud-classification
    system. No fraud labels are used or created.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Optional, Tuple


class Time2Vec(nn.Module):
    """
    Learnable time embedding inspired by Time2Vec (Kazemi et al., 2019).
    Encodes a scalar timestamp into a d-dimensional embedding:
        [w_0 * t + phi_0,  sin(w_1 * t + phi_1), ..., sin(w_{d-1} * t + phi_{d-1})]
    where w_0, phi_0 are linear (trend), w_k, phi_k for k>0 are periodic.
    """

    def __init__(self, d_model: int = 16):
        super().__init__()
        assert d_model >= 2, "d_model must be at least 2"
        self.d_model = d_model
        # Linear term
        self.w0 = nn.Parameter(torch.randn(1))
        self.phi0 = nn.Parameter(torch.zeros(1))
        # Periodic terms
        n_periodic = d_model - 1
        self.w = nn.Parameter(torch.randn(n_periodic))
        self.phi = nn.Parameter(torch.zeros(n_periodic))

    def forward(self, t: torch.Tensor) -> torch.Tensor:
        """
        Args:
            t: scalar timestamps, shape (batch,) or (batch, 1)
        Returns:
            embedding: shape (batch, d_model)
        """
        if t.dim() == 1:
            t = t.unsqueeze(-1)  # (batch, 1)
        linear_part = self.w0 * t + self.phi0           # (batch, 1)
        periodic_part = torch.sin(self.w * t + self.phi)  # (batch, n_periodic)
        return torch.cat([linear_part, periodic_part], dim=-1)  # (batch, d_model)


class GraphAttentionLayer(nn.Module):
    """
    Single-layer multi-head graph attention over temporal neighbors.

    Given a query transaction embedding and key/value embeddings of k neighbors,
    computes attention-weighted context aggregation.

    Input dimensions:
        query_dim: dimension of query (h_i concat e_i = 32 + 16 = 48)
        key_dim:   dimension of keys (same as query_dim for simplicity)
        n_heads:   number of attention heads
    """

    def __init__(self, query_dim: int = 48, n_heads: int = 2, dropout: float = 0.1):
        super().__init__()
        assert query_dim % n_heads == 0, "query_dim must be divisible by n_heads"
        self.n_heads = n_heads
        self.d_k = query_dim // n_heads
        self.query_dim = query_dim

        self.W_q = nn.Linear(query_dim, query_dim, bias=False)
        self.W_k = nn.Linear(query_dim, query_dim, bias=False)
        self.W_v = nn.Linear(query_dim, query_dim // n_heads * n_heads, bias=False)
        self.out_proj = nn.Linear(query_dim, query_dim // 2)  # 48 -> 24... adjusted below
        self.dropout = nn.Dropout(dropout)

    def forward(
        self,
        query: torch.Tensor,        # (batch, query_dim)
        keys: torch.Tensor,         # (batch, k, query_dim) or (batch, 0, query_dim) if isolated
        mask: Optional[torch.Tensor] = None,  # (batch, k) bool — True for valid neighbors
    ) -> torch.Tensor:
        """
        Returns:
            context: (batch, query_dim)  — attention-aggregated neighbor context
        """
        batch_size = query.size(0)
        k = keys.size(1)

        if k == 0:
            # No neighbors — return zero context
            return torch.zeros(batch_size, self.query_dim, device=query.device)

        # Project query and keys
        q = self.W_q(query).unsqueeze(1)         # (batch, 1, query_dim)
        K = self.W_k(keys)                        # (batch, k, query_dim)
        V = self.W_v(keys)                        # (batch, k, query_dim)

        # Reshape for multi-head: (batch, n_heads, seq, d_k)
        q = q.view(batch_size, 1, self.n_heads, self.d_k).transpose(1, 2)  # (B, h, 1, d_k)
        K = K.view(batch_size, k, self.n_heads, self.d_k).transpose(1, 2)  # (B, h, k, d_k)
        V = V.view(batch_size, k, self.n_heads, self.d_k).transpose(1, 2)  # (B, h, k, d_k)

        # Scaled dot-product attention
        scores = torch.matmul(q, K.transpose(-2, -1)) / (self.d_k ** 0.5)  # (B, h, 1, k)

        if mask is not None:
            # mask: (B, k), True = valid neighbor
            # We want to mask OUT invalid positions (where mask == False)
            attn_mask = ~mask.unsqueeze(1).unsqueeze(2)  # (B, 1, 1, k)
            scores = scores.masked_fill(attn_mask, float('-inf'))

        alpha = F.softmax(scores, dim=-1)  # (B, h, 1, k)
        alpha = self.dropout(alpha)

        # Replace NaN (from all-masked rows) with uniform attention
        alpha = torch.nan_to_num(alpha, nan=0.0)

        context = torch.matmul(alpha, V)  # (B, h, 1, d_k)
        context = context.squeeze(2)      # (B, h, d_k)
        context = context.transpose(1, 2).contiguous().view(batch_size, -1)  # (B, query_dim)

        return context


class C2GATInspiredModel(nn.Module):
    """
    C2GAT-Inspired Self-Supervised Anomaly Detection Model.

    Architecture:
        - Feature Encoder: 15 -> 32 (ReLU)
        - Time2Vec: 1 -> 16
        - Graph Attention: multi-head over k temporal neighbors
        - Fusion: [32+16+48] = 96 -> 64 (latent z)
        - Decoder: 64 -> 15 (reconstruction)

    Self-supervised objective: Masked Feature Reconstruction (MSE on masked positions).
    """

    def __init__(
        self,
        n_features: int = 15,
        feat_dim: int = 32,
        time_dim: int = 16,
        latent_dim: int = 64,
        n_heads: int = 2,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.n_features = n_features
        self.feat_dim = feat_dim
        self.time_dim = time_dim
        self.latent_dim = latent_dim

        # Shared feature encoder (used for both anchor and neighbors)
        self.feature_encoder = nn.Sequential(
            nn.Linear(n_features, feat_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
        )

        # Temporal encoder
        self.time_encoder = Time2Vec(d_model=time_dim)

        # Graph attention: query_dim = feat_dim + time_dim = 48
        self.attn_dim = feat_dim + time_dim  # 48
        self.graph_attention = GraphAttentionLayer(
            query_dim=self.attn_dim,
            n_heads=n_heads,
            dropout=dropout,
        )

        # Fusion: concatenate [h_i(32), e_i(16), context(48)] = 96 -> 64
        fusion_input_dim = feat_dim + time_dim + self.attn_dim  # 96
        self.fusion = nn.Sequential(
            nn.Linear(fusion_input_dim, latent_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
        )

        # Decoder: 64 -> 15
        self.decoder = nn.Linear(latent_dim, n_features)

        # Initialize weights
        self._init_weights()

    def _init_weights(self):
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)

    def encode(
        self,
        x: torch.Tensor,           # (batch, n_features) — anchor features
        t: torch.Tensor,            # (batch,) — anchor timestamps
        x_nbrs: torch.Tensor,       # (batch, k, n_features) — neighbor features
        t_nbrs: torch.Tensor,       # (batch, k) — neighbor timestamps
        nbr_mask: torch.Tensor,     # (batch, k) bool — valid neighbor positions
    ) -> torch.Tensor:
        """
        Encode transactions with graph context.

        Returns:
            z: latent embeddings, shape (batch, latent_dim)
        """
        batch_size, k = x_nbrs.shape[0], x_nbrs.shape[1]

        # --- Feature encoding ---
        h_i = self.feature_encoder(x)                        # (B, feat_dim=32)
        e_i = self.time_encoder(t)                           # (B, time_dim=16)

        # --- Neighbor encodings ---
        if k > 0:
            x_nbrs_flat = x_nbrs.view(batch_size * k, self.n_features)
            h_nbrs_flat = self.feature_encoder(x_nbrs_flat)         # (B*k, 32)
            h_nbrs = h_nbrs_flat.view(batch_size, k, self.feat_dim)  # (B, k, 32)

            t_nbrs_flat = t_nbrs.view(batch_size * k)
            e_nbrs_flat = self.time_encoder(t_nbrs_flat)             # (B*k, 16)
            e_nbrs = e_nbrs_flat.view(batch_size, k, self.time_dim)  # (B, k, 16)

            # Concatenate neighbor feature + time embeddings: (B, k, 48)
            keys = torch.cat([h_nbrs, e_nbrs], dim=-1)
        else:
            keys = torch.zeros(batch_size, 0, self.attn_dim, device=x.device)

        # --- Graph attention ---
        query = torch.cat([h_i, e_i], dim=-1)               # (B, 48)
        context = self.graph_attention(query, keys, nbr_mask)  # (B, 48)

        # --- Fusion ---
        fused = torch.cat([h_i, e_i, context], dim=-1)      # (B, 96)
        z = self.fusion(fused)                               # (B, 64)

        return z

    def decode(self, z: torch.Tensor) -> torch.Tensor:
        """
        Decode latent representation to reconstructed features.
        Returns: x_hat, shape (batch, n_features)
        """
        return self.decoder(z)

    def forward(
        self,
        x: torch.Tensor,
        t: torch.Tensor,
        x_nbrs: torch.Tensor,
        t_nbrs: torch.Tensor,
        nbr_mask: torch.Tensor,
        feature_mask: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Full forward pass.

        Args:
            x:            (batch, 15) — input features
            t:            (batch,) — normalized timestamps
            x_nbrs:       (batch, k, 15) — neighbor features
            t_nbrs:       (batch, k) — neighbor timestamps
            nbr_mask:     (batch, k) bool — valid neighbors
            feature_mask: (batch, 15) bool — True at positions to MASK (zero out) during encoding

        Returns:
            x_hat: (batch, 15) — reconstructed features
            z:     (batch, latent_dim) — latent embeddings
        """
        # Apply feature mask to input (zero out masked positions)
        x_masked = x.clone()
        if feature_mask is not None:
            x_masked = x_masked * (~feature_mask).float()

        z = self.encode(x_masked, t, x_nbrs, t_nbrs, nbr_mask)
        x_hat = self.decode(z)

        return x_hat, z

    def masked_reconstruction_loss(
        self,
        x: torch.Tensor,
        x_hat: torch.Tensor,
        feature_mask: torch.Tensor,
    ) -> torch.Tensor:
        """
        Compute MSE loss on masked feature positions only.

        Args:
            x:            (batch, 15) — original (unmasked) features
            x_hat:        (batch, 15) — reconstructed features
            feature_mask: (batch, 15) bool — True at masked positions

        Returns:
            loss: scalar MSE over masked positions
        """
        # Only compute loss on masked positions
        masked_orig = x[feature_mask]
        masked_recon = x_hat[feature_mask]

        if masked_orig.numel() == 0:
            return torch.tensor(0.0, device=x.device, requires_grad=True)

        return F.mse_loss(masked_recon, masked_orig)


def generate_feature_mask(
    batch_size: int,
    n_features: int,
    mask_ratio: float = 0.30,
    seed: Optional[int] = None,
    device: str = "cpu",
) -> torch.Tensor:
    """
    Generate a random binary feature mask.

    Args:
        mask_ratio: fraction of features to mask (set to 0) per sample
    Returns:
        mask: (batch_size, n_features) bool tensor, True = masked
    """
    if seed is not None:
        torch.manual_seed(seed)

    mask = torch.rand(batch_size, n_features, device=device) < mask_ratio
    return mask


def generate_fixed_eval_mask(n_features: int, mask_ratio: float = 0.30) -> torch.Tensor:
    """
    Generate a deterministic fixed mask for evaluation (same across all transactions).
    Uses seed=42 for reproducibility.
    """
    torch.manual_seed(42)
    mask = torch.rand(n_features) < mask_ratio
    return mask


if __name__ == "__main__":
    # Quick smoke test
    torch.manual_seed(42)
    model = C2GATInspiredModel()
    print("Model architecture:")
    print(model)
    total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"\nTotal trainable parameters: {total_params:,}")

    # Test forward pass
    B, k = 8, 5
    x = torch.randn(B, 15)
    t = torch.rand(B)
    x_nbrs = torch.randn(B, k, 15)
    t_nbrs = torch.rand(B, k)
    nbr_mask = torch.ones(B, k, dtype=torch.bool)
    feature_mask = generate_feature_mask(B, 15, mask_ratio=0.30)

    x_hat, z = model(x, t, x_nbrs, t_nbrs, nbr_mask, feature_mask)
    loss = model.masked_reconstruction_loss(x, x_hat, feature_mask)

    print(f"\nSmoke test:")
    print(f"  x_hat shape: {x_hat.shape}   (expected: {B}, 15)")
    print(f"  z shape: {z.shape}            (expected: {B}, 64)")
    print(f"  Masked reconstruction loss: {loss.item():.4f}")
    print("\n[PASS] Model smoke test succeeded.")
