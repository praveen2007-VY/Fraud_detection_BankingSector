import logging
from typing import Dict, Any, List, Optional
import pandas as pd

from backend.config import CLEAN_TRANSACTIONS_CSV
from backend.services.scoring_service import ScoringService
from backend.schemas.fraud import (
    TransactionSummary,
    TransactionListResponse,
    TransactionDetailResponse,
    StatsResponse,
    AlertItem,
    AlertListResponse,
    RiskDistributionResponse,
)

logger = logging.getLogger("transaction_service")


class TransactionService:
    _instance: Optional["TransactionService"] = None

    def __init__(self):
        self.transactions: List[Dict[str, Any]] = []
        self.tx_by_id: Dict[str, Dict[str, Any]] = {}
        self.scoring_service = ScoringService.get_instance()
        self.load_transactions()

    @classmethod
    def get_instance(cls) -> "TransactionService":
        if cls._instance is None:
            cls._instance = TransactionService()
        return cls._instance

    def load_transactions(self):
        if not CLEAN_TRANSACTIONS_CSV.exists():
            logger.warning("Clean transactions CSV not found at %s", CLEAN_TRANSACTIONS_CSV)
            return

        try:
            df = pd.read_csv(CLEAN_TRANSACTIONS_CSV, dtype={
                "TransactionID": str,
                "AccountID": str,
                "DeviceID": str,
                "IP Address": str,
                "MerchantID": str,
            })
            
            for _, row in df.iterrows():
                tx_id = str(row["TransactionID"]).strip()
                scores = self.scoring_service.get_scores_for_transaction(tx_id)

                tx_item = {
                    "transaction_id": tx_id,
                    "account_id": str(row["AccountID"]).strip(),
                    "transaction_amount": float(row["TransactionAmount"]),
                    "transaction_date": str(row["TransactionDate"]),
                    "transaction_type": str(row.get("TransactionType", "")),
                    "channel": str(row.get("Channel", "")),
                    "location": str(row.get("Location", "")),
                    "device_id": str(row.get("DeviceID", "")),
                    "ip_address": str(row.get("IP Address", "")),
                    "merchant_id": str(row.get("MerchantID", "")),
                    "customer_age": int(row["CustomerAge"]) if pd.notna(row.get("CustomerAge")) else None,
                    "customer_occupation": str(row.get("CustomerOccupation", "")),
                    "transaction_duration": int(row["TransactionDuration"]) if pd.notna(row.get("TransactionDuration")) else None,
                    "login_attempts": int(row["LoginAttempts"]) if pd.notna(row.get("LoginAttempts")) else None,
                    "account_balance": float(row["AccountBalance"]) if pd.notna(row.get("AccountBalance")) else None,
                    "previous_transaction_date": str(row.get("PreviousTransactionDate", "")),
                    **scores,
                }
                self.transactions.append(tx_item)
                self.tx_by_id[tx_id] = tx_item

            logger.info("Loaded and enriched %d transactions.", len(self.transactions))
        except Exception as e:
            logger.error("Error loading transactions from CSV: %s", e)

    def add_or_update_live_transaction(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Adds or updates a live transaction coming from Kafka."""
        tx_id = str(record.get("TransactionID") or record.get("transaction_id", "")).strip()
        if not tx_id:
            return record

        scores = self.scoring_service.get_scores_for_transaction(tx_id)
        tx_item = {
            "transaction_id": tx_id,
            "account_id": str(record.get("AccountID") or record.get("account_id", "")).strip(),
            "transaction_amount": float(record.get("TransactionAmount") or record.get("transaction_amount", 0.0)),
            "transaction_date": str(record.get("TransactionDate") or record.get("transaction_date", "")),
            "transaction_type": str(record.get("TransactionType") or record.get("transaction_type", "")),
            "channel": str(record.get("Channel") or record.get("channel", "")),
            "location": str(record.get("Location") or record.get("location", "")),
            "device_id": str(record.get("DeviceID") or record.get("device_id", "")),
            "ip_address": str(record.get("IP Address") or record.get("ip_address", "")),
            "merchant_id": str(record.get("MerchantID") or record.get("merchant_id", "")),
            "processing_timestamp": str(record.get("processing_timestamp", "")),
            **scores,
        }

        if tx_id in self.tx_by_id:
            # Update existing
            for idx, existing in enumerate(self.transactions):
                if existing["transaction_id"] == tx_id:
                    self.transactions[idx] = tx_item
                    break
        else:
            # Prepend live new transaction
            self.transactions.insert(0, tx_item)

        self.tx_by_id[tx_id] = tx_item
        return tx_item

    def get_transactions(
        self,
        limit: int = 20,
        offset: int = 0,
        search: Optional[str] = None,
        risk_level: Optional[str] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        flagged_only: bool = False,
        sort_by: str = "timestamp",
        order: str = "desc",
    ) -> TransactionListResponse:
        filtered = self.transactions

        # Search filter
        if search:
            s = search.lower().strip()
            filtered = [
                tx for tx in filtered
                if s in tx["transaction_id"].lower()
                or s in tx["account_id"].lower()
                or s in tx.get("device_id", "").lower()
                or s in tx.get("ip_address", "").lower()
                or s in tx.get("merchant_id", "").lower()
            ]

        # Risk level filter
        if risk_level:
            rl = risk_level.lower().strip()
            filtered = [tx for tx in filtered if tx.get("risk_level", "").lower() == rl]

        # Amount range filter
        if min_amount is not None:
            filtered = [tx for tx in filtered if tx["transaction_amount"] >= min_amount]
        if max_amount is not None:
            filtered = [tx for tx in filtered if tx["transaction_amount"] <= max_amount]

        # Flagged filter
        if flagged_only:
            filtered = [tx for tx in filtered if tx.get("is_flagged", False)]

        # Sorting
        reverse = (order.lower() == "desc")
        if sort_by == "timestamp":
            filtered = sorted(filtered, key=lambda x: str(x.get("transaction_date", "")), reverse=reverse)
        elif sort_by == "amount":
            filtered = sorted(filtered, key=lambda x: float(x.get("transaction_amount", 0.0)), reverse=reverse)
        elif sort_by == "risk_score":
            filtered = sorted(filtered, key=lambda x: float(x.get("approach_b_score") or 0.0), reverse=reverse)
        elif sort_by == "anomaly_score":
            filtered = sorted(filtered, key=lambda x: float(x.get("anomaly_score") or 0.0), reverse=reverse)

        total = len(filtered)
        paginated = filtered[offset : offset + limit]

        items = [TransactionSummary(**item) for item in paginated]
        return TransactionListResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )

    def get_transaction_by_id(self, transaction_id: str) -> Optional[TransactionDetailResponse]:
        tx = self.tx_by_id.get(str(transaction_id).strip())
        if not tx:
            return None

        summary = TransactionSummary(**tx)
        graph_features = {
            "shared_device_accounts": tx.get("shared_device_accounts", 0),
            "shared_ip_accounts": tx.get("shared_ip_accounts", 0),
            "merchant_cluster_accounts": tx.get("merchant_cluster_accounts", 0),
            "rapid_velocity_count_24h": tx.get("rapid_velocity_count_24h", 0),
            "account_network_sprawl_degree": tx.get("account_network_sprawl_degree", 0),
        }

        reasons = [r.strip() for r in tx.get("risk_reasons", "").split(";") if r.strip()]
        prominent = [p.strip() for p in tx.get("approach_a_prominent_factors", "").split(",") if p.strip()]

        explainability = {
            "risk_reasons": reasons,
            "prominent_factors": prominent,
            "approach_a_score": tx.get("approach_a_score"),
            "approach_b_score": tx.get("approach_b_score"),
            "anomaly_score": tx.get("anomaly_score"),
            "anomaly_score_raw": tx.get("anomaly_score_raw"),
            "c2gat_embedding_norm": tx.get("c2gat_embedding_norm"),
        }

        related_entities = {
            "account_id": tx.get("account_id"),
            "device_id": tx.get("device_id"),
            "ip_address": tx.get("ip_address"),
            "merchant_id": tx.get("merchant_id"),
            "location": tx.get("location"),
            "channel": tx.get("channel"),
        }

        return TransactionDetailResponse(
            transaction=summary,
            graph_features=graph_features,
            explainability=explainability,
            related_entities=related_entities,
        )

    def get_stats(self) -> StatsResponse:
        total = len(self.transactions)
        total_volume = sum(tx["transaction_amount"] for tx in self.transactions)
        
        low_count = sum(1 for tx in self.transactions if tx.get("risk_level") == "low")
        med_count = sum(1 for tx in self.transactions if tx.get("risk_level") == "medium")
        high_count = sum(1 for tx in self.transactions if tx.get("risk_level") == "high")
        crit_count = sum(1 for tx in self.transactions if tx.get("risk_level") == "critical")
        
        flagged = sum(1 for tx in self.transactions if tx.get("is_flagged", False))
        flagged_pct = (flagged / total * 100.0) if total > 0 else 0.0

        unique_accounts = len({tx["account_id"] for tx in self.transactions})
        high_risk_accounts = len({
            tx["account_id"] for tx in self.transactions
            if tx.get("risk_level") in ("high", "critical")
        })

        return StatsResponse(
            total_transactions=total,
            total_volume=round(total_volume, 2),
            currency="USD",
            low_risk_count=low_count,
            medium_risk_count=med_count,
            high_risk_count=high_count,
            critical_risk_count=crit_count,
            flagged_count=flagged,
            flagged_percentage=round(flagged_pct, 2),
            unique_accounts=unique_accounts,
            high_risk_accounts=high_risk_accounts,
            graph_scoring_available=self.scoring_service.is_phase5_loaded,
            ml_scoring_available=self.scoring_service.is_phase6_loaded,
        )

    def get_alerts(self, limit: int = 50, severity: Optional[str] = None) -> AlertListResponse:
        alert_items = []

        for tx in self.transactions:
            if not tx.get("is_flagged", False):
                continue

            app_b = tx.get("approach_b_score") or 0.0
            anom = tx.get("anomaly_score") or 0.0

            # Determine detection source
            is_rule = app_b >= 50.0
            is_ml = anom >= 0.5
            if is_rule and is_ml:
                source = "both"
            elif is_rule:
                source = "graph_rules"
            else:
                source = "ml_anomaly"

            # Severity
            sev = tx.get("risk_level", "medium")
            if sev == "low":
                sev = "medium"

            if severity and sev != severity.lower():
                continue

            raw_reasons = tx.get("risk_reasons", "")
            reasons = [r.strip() for r in raw_reasons.split(";") if r.strip()]
            if not reasons:
                reasons = ["Elevated behavioral or anomaly score breach"]

            alert_items.append(
                AlertItem(
                    alert_id=f"ALT-{tx['transaction_id']}",
                    transaction_id=tx["transaction_id"],
                    account_id=tx["account_id"],
                    transaction_amount=tx["transaction_amount"],
                    transaction_date=tx["transaction_date"],
                    severity=sev,
                    detection_source=source,
                    approach_b_score=tx.get("approach_b_score"),
                    anomaly_score=tx.get("anomaly_score"),
                    reasons=reasons,
                )
            )

        alert_items.sort(key=lambda x: str(x.transaction_date), reverse=True)
        return AlertListResponse(
            items=alert_items[:limit],
            total=len(alert_items),
        )

    def get_risk_distribution(self) -> RiskDistributionResponse:
        total = len(self.transactions)

        # Approach A distribution
        app_a_bands = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        app_b_bands = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        anom_bands = {"low": 0, "medium": 0, "high": 0, "critical": 0}

        for tx in self.transactions:
            a = tx.get("approach_a_score")
            b = tx.get("approach_b_score")
            an = tx.get("anomaly_score")

            if a is not None:
                if a < 30.0:
                    app_a_bands["low"] += 1
                elif a < 50.0:
                    app_a_bands["medium"] += 1
                elif a < 70.0:
                    app_a_bands["high"] += 1
                else:
                    app_a_bands["critical"] += 1

            if b is not None:
                if b < 30.0:
                    app_b_bands["low"] += 1
                elif b < 50.0:
                    app_b_bands["medium"] += 1
                elif b < 70.0:
                    app_b_bands["high"] += 1
                else:
                    app_b_bands["critical"] += 1

            if an is not None:
                # Anomaly is [0, 1] normalized
                if an < 0.2:
                    anom_bands["low"] += 1
                elif an < 0.5:
                    anom_bands["medium"] += 1
                elif an < 0.8:
                    anom_bands["high"] += 1
                else:
                    anom_bands["critical"] += 1

        return RiskDistributionResponse(
            approach_a=app_a_bands,
            approach_b=app_b_bands,
            anomaly=anom_bands,
            total=total,
        )
