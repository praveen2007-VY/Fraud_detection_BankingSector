import logging
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np

from backend.config import (
    SCORED_TRANSACTIONS_CSV,
    C2GAT_SCORES_CSV,
    C2GAT_MODEL_PT,
    C2GAT_SCALER_PKL,
    RISK_SCORE_THRESHOLD,
    ANOMALY_SCORE_THRESHOLD,
)

logger = logging.getLogger("scoring_service")


class ScoringService:
    _instance: Optional["ScoringService"] = None

    def __init__(self):
        self.phase5_data: Dict[str, Dict[str, Any]] = {}
        self.phase6_data: Dict[str, Dict[str, Any]] = {}
        self.is_phase5_loaded = False
        self.is_phase6_loaded = False
        self.load_scores()

    @classmethod
    def get_instance(cls) -> "ScoringService":
        if cls._instance is None:
            cls._instance = ScoringService()
        return cls._instance

    def load_scores(self):
        # Load Phase 5 Graph Scores
        if SCORED_TRANSACTIONS_CSV.exists():
            try:
                df5 = pd.read_csv(SCORED_TRANSACTIONS_CSV, dtype={"transaction_id": str, "account_id": str})
                for _, row in df5.iterrows():
                    tx_id = str(row["transaction_id"]).strip()
                    self.phase5_data[tx_id] = {
                        "approach_a_score": float(row["approach_a_score"]) if pd.notna(row.get("approach_a_score")) else None,
                        "approach_b_score": float(row["approach_b_score"]) if pd.notna(row.get("approach_b_score")) else None,
                        "shared_device_accounts": int(row["shared_device_accounts"]) if pd.notna(row.get("shared_device_accounts")) else 0,
                        "shared_ip_accounts": int(row["shared_ip_accounts"]) if pd.notna(row.get("shared_ip_accounts")) else 0,
                        "merchant_cluster_accounts": int(row["merchant_cluster_accounts"]) if pd.notna(row.get("merchant_cluster_accounts")) else 0,
                        "rapid_velocity_count_24h": int(row["rapid_velocity_count_24h"]) if pd.notna(row.get("rapid_velocity_count_24h")) else 0,
                        "account_network_sprawl_degree": int(row["account_network_sprawl_degree"]) if pd.notna(row.get("account_network_sprawl_degree")) else 0,
                        "risk_reasons": str(row["risk_reasons"]) if pd.notna(row.get("risk_reasons")) else "",
                        "approach_a_prominent_factors": str(row["approach_a_prominent_factors"]) if pd.notna(row.get("approach_a_prominent_factors")) else "",
                    }
                self.is_phase5_loaded = True
                logger.info("Loaded %d Phase 5 scored transactions from %s", len(self.phase5_data), SCORED_TRANSACTIONS_CSV)
            except Exception as e:
                logger.error("Failed to load Phase 5 scores: %s", e)

        # Load Phase 6 ML Anomaly Scores
        if C2GAT_SCORES_CSV.exists():
            try:
                df6 = pd.read_csv(C2GAT_SCORES_CSV, dtype={"transaction_id": str, "account_id": str})
                for _, row in df6.iterrows():
                    tx_id = str(row["transaction_id"]).strip()
                    self.phase6_data[tx_id] = {
                        "anomaly_score": float(row["anomaly_score"]) if pd.notna(row.get("anomaly_score")) else None,
                        "anomaly_score_raw": float(row["anomaly_score_raw"]) if pd.notna(row.get("anomaly_score_raw")) else None,
                        "c2gat_embedding_norm": float(row["c2gat_embedding_norm"]) if pd.notna(row.get("c2gat_embedding_norm")) else None,
                    }
                self.is_phase6_loaded = True
                logger.info("Loaded %d Phase 6 anomaly scores from %s", len(self.phase6_data), C2GAT_SCORES_CSV)
            except Exception as e:
                logger.error("Failed to load Phase 6 scores: %s", e)

    def get_scores_for_transaction(self, transaction_id: str, record: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        tx_id = str(transaction_id).strip()
        p5 = self.phase5_data.get(tx_id, {})
        p6 = self.phase6_data.get(tx_id, {})

        approach_a = p5.get("approach_a_score")
        approach_b = p5.get("approach_b_score")
        anomaly = p6.get("anomaly_score")
        risk_reasons = p5.get("risk_reasons", "")

        # Fallback to dynamic evaluation for live records not in precomputed CSV
        if (approach_b is None and approach_a is None) and record is not None:
            reasons_list = []
            pts = 0.0
            try:
                amt = float(record.get("TransactionAmount") or record.get("transaction_amount", 0.0))
            except (ValueError, TypeError):
                amt = 0.0

            if amt >= 589.54:
                pts += 20.0
                reasons_list.append("High transaction amount (>= $589.54)")

            try:
                login_attempts = int(record.get("LoginAttempts") or record.get("login_attempts", 0))
                if login_attempts >= 3:
                    pts += 15.0
                    reasons_list.append(f"Multiple failed login attempts ({login_attempts})")
            except (ValueError, TypeError):
                pass

            approach_b = min(100.0, pts)
            risk_reasons = "; ".join(reasons_list)

        score_val = approach_b if approach_b is not None else approach_a

        if score_val is not None:
            if score_val >= 70.0:
                risk_level = "critical"
            elif score_val >= 50.0:
                risk_level = "high"
            elif score_val >= 30.0:
                risk_level = "medium"
            else:
                risk_level = "low"
        else:
            risk_level = "low"

        # Flagged if rule risk >= threshold OR ML anomaly >= threshold
        is_flagged = False
        if score_val is not None and score_val >= RISK_SCORE_THRESHOLD:
            is_flagged = True
        if anomaly is not None and anomaly >= ANOMALY_SCORE_THRESHOLD:
            is_flagged = True

        return {
            "approach_a_score": approach_a,
            "approach_b_score": approach_b,
            "anomaly_score": anomaly,
            "anomaly_score_raw": p6.get("anomaly_score_raw"),
            "c2gat_embedding_norm": p6.get("c2gat_embedding_norm"),
            "shared_device_accounts": p5.get("shared_device_accounts", 0),
            "shared_ip_accounts": p5.get("shared_ip_accounts", 0),
            "merchant_cluster_accounts": p5.get("merchant_cluster_accounts", 0),
            "rapid_velocity_count_24h": p5.get("rapid_velocity_count_24h", 0),
            "account_network_sprawl_degree": p5.get("account_network_sprawl_degree", 0),
            "risk_reasons": risk_reasons,
            "approach_a_prominent_factors": p5.get("approach_a_prominent_factors", ""),
            "risk_level": risk_level,
            "is_flagged": is_flagged,
        }

    def check_ml_artifacts_status(self) -> Dict[str, Any]:
        checkpoint_ok = C2GAT_MODEL_PT.exists() and C2GAT_MODEL_PT.stat().st_size > 0
        scaler_ok = C2GAT_SCALER_PKL.exists() and C2GAT_SCALER_PKL.stat().st_size > 0
        scores_ok = C2GAT_SCORES_CSV.exists() and len(self.phase6_data) > 0
        return {
            "model_checkpoint_present": checkpoint_ok,
            "scaler_present": scaler_ok,
            "scores_present": scores_ok,
            "scores_loaded_count": len(self.phase6_data),
            "inference_ready": checkpoint_ok and scaler_ok,
        }

    def compute_model_comparison(self) -> Dict[str, Any]:
        if not self.phase5_data or not self.phase6_data:
            return {
                "metrics": {},
                "correlations": {},
                "score_interpretation": {
                    "approach_a": "Equal-weight normalized composite score (0-100). Aggregates 6 graph topological and behavioral signals.",
                    "approach_b": "Rule-based additive point system (0-100). Points allocated for threshold breaches.",
                    "anomaly_score": "C2GAT-inspired unsupervised reconstruction error normalized to [0, 1]. High values indicate temporal and structural outliers.",
                },
            }

        common_ids = set(self.phase5_data.keys()).intersection(self.phase6_data.keys())
        app_a_vals = []
        app_b_vals = []
        anom_vals = []

        for cid in common_ids:
            a = self.phase5_data[cid].get("approach_a_score")
            b = self.phase5_data[cid].get("approach_b_score")
            an = self.phase6_data[cid].get("anomaly_score")
            if a is not None and b is not None and an is not None:
                app_a_vals.append(a)
                app_b_vals.append(b)
                anom_vals.append(an)

        df = pd.DataFrame({
            "approach_a": app_a_vals,
            "approach_b": app_b_vals,
            "anomaly_score": anom_vals,
        })

        metrics = {}
        for col in ["approach_a", "approach_b", "anomaly_score"]:
            metrics[col] = {
                "min": float(round(df[col].min(), 4)),
                "max": float(round(df[col].max(), 4)),
                "mean": float(round(df[col].mean(), 4)),
                "median": float(round(df[col].median(), 4)),
                "p75": float(round(df[col].quantile(0.75), 4)),
                "p90": float(round(df[col].quantile(0.90), 4)),
                "std_dev": float(round(df[col].std(), 4)),
            }

        pearson_ab = float(round(df["approach_a"].corr(df["approach_b"]), 4))
        pearson_b_anom = float(round(df["approach_b"].corr(df["anomaly_score"]), 4))
        pearson_a_anom = float(round(df["approach_a"].corr(df["anomaly_score"]), 4))

        return {
            "metrics": metrics,
            "correlations": {
                "pearson_approach_a_vs_b": pearson_ab,
                "pearson_approach_b_vs_anomaly": pearson_b_anom,
                "pearson_approach_a_vs_anomaly": pearson_a_anom,
            },
            "score_interpretation": {
                "approach_a": "Equal-weight normalized composite score (0-100). Aggregates 6 graph topological and behavioral signals.",
                "approach_b": "Rule-based additive point system (0-100). Points allocated for threshold breaches (high amount, shared device, shared IP, merchant cluster, velocity, sprawl).",
                "anomaly_score": "C2GAT-inspired unsupervised reconstruction error normalized to [0, 1]. Captures temporal and structural anomalous transactions without labels.",
            },
        }
