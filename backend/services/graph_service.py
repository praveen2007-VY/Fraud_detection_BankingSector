import logging
from typing import Dict, Any, List, Optional
from neo4j import GraphDatabase, Driver
from backend.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
from backend.schemas.fraud import GraphNode, GraphEdge, AccountGraphResponse

logger = logging.getLogger("graph_service")


class GraphService:
    _instance: Optional["GraphService"] = None

    def __init__(self):
        self.driver: Optional[Driver] = None
        self._init_driver()

    @classmethod
    def get_instance(cls) -> "GraphService":
        if cls._instance is None:
            cls._instance = GraphService()
        return cls._instance

    def _init_driver(self):
        try:
            self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
            logger.info("Initialized Neo4j driver for %s", NEO4J_URI)
        except Exception as e:
            logger.warning("Could not initialize Neo4j driver: %s", e)
            self.driver = None

    def verify_connectivity(self) -> bool:
        if self.driver is None:
            self._init_driver()
        if self.driver is None:
            return False
        try:
            self.driver.verify_connectivity()
            return True
        except Exception as e:
            logger.warning("Neo4j connectivity check failed: %s", e)
            return False

    def close(self):
        if self.driver is not None:
            try:
                self.driver.close()
                logger.info("Closed Neo4j driver connection.")
            except Exception as e:
                logger.error("Error closing Neo4j driver: %s", e)

    def ingest_transaction(self, record: Dict[str, Any]) -> bool:
        """
        Materialize a live transaction and its entity nodes (Account, Device, IP, Merchant)
        and topology relationships in Neo4j.
        """
        if not self.verify_connectivity():
            logger.warning("Neo4j driver not connected; skipping transaction ingestion.")
            return False

        tx_id = str(record.get("TransactionID") or record.get("transaction_id", "")).strip()
        acct_id = str(record.get("AccountID") or record.get("account_id", "")).strip()
        if not tx_id or not acct_id:
            return False

        dev_id = str(record.get("DeviceID") or record.get("device_id", "")).strip()
        ip_addr = str(record.get("IP Address") or record.get("ip_address", "")).strip()
        merch_id = str(record.get("MerchantID") or record.get("merchant_id", "")).strip()

        try:
            amount = float(record.get("TransactionAmount") or record.get("transaction_amount", 0.0))
        except (ValueError, TypeError):
            amount = 0.0

        try:
            cust_age = int(record["CustomerAge"]) if "CustomerAge" in record and record["CustomerAge"] is not None else None
        except (ValueError, TypeError):
            cust_age = None

        try:
            duration = int(record["TransactionDuration"]) if "TransactionDuration" in record and record["TransactionDuration"] is not None else None
        except (ValueError, TypeError):
            duration = None

        try:
            login_att = int(record["LoginAttempts"]) if "LoginAttempts" in record and record["LoginAttempts"] is not None else None
        except (ValueError, TypeError):
            login_att = None

        try:
            acct_bal = float(record["AccountBalance"]) if "AccountBalance" in record and record["AccountBalance"] is not None else None
        except (ValueError, TypeError):
            acct_bal = None

        params = {
            "transaction_id": tx_id,
            "account_id": acct_id,
            "device_id": dev_id,
            "ip_address": ip_addr,
            "merchant_id": merch_id,
            "transaction_amount": amount,
            "transaction_date": str(record.get("TransactionDate") or record.get("transaction_date", "")),
            "transaction_type": str(record.get("TransactionType") or record.get("transaction_type", "")),
            "channel": str(record.get("Channel") or record.get("channel", "")),
            "location": str(record.get("Location") or record.get("location", "")),
            "customer_occupation": str(record.get("CustomerOccupation") or record.get("customer_occupation", "")),
            "customer_age": cust_age,
            "transaction_duration": duration,
            "login_attempts": login_att,
            "account_balance": acct_bal,
            "previous_transaction_date": str(record.get("PreviousTransactionDate") or record.get("previous_transaction_date", "")),
            "processing_timestamp": str(record.get("processing_timestamp", "")),
        }

        ingest_cypher = """
        MERGE (a:Account {account_id: $account_id})
        ON CREATE SET 
            a.customer_occupation = $customer_occupation,
            a.customer_age = $customer_age

        MERGE (d:Device {device_id: $device_id})
        MERGE (i:IP {ip_address: $ip_address})
        MERGE (m:Merchant {merchant_id: $merchant_id})

        MERGE (t:Transaction {transaction_id: $transaction_id})
        ON CREATE SET 
            t.transaction_amount = $transaction_amount,
            t.transaction_date = $transaction_date,
            t.transaction_type = $transaction_type,
            t.channel = $channel,
            t.location = $location,
            t.transaction_duration = $transaction_duration,
            t.login_attempts = $login_attempts,
            t.account_balance = $account_balance,
            t.customer_age = $customer_age,
            t.customer_occupation = $customer_occupation,
            t.previous_transaction_date = $previous_transaction_date,
            t.processing_timestamp = $processing_timestamp

        MERGE (a)-[:PERFORMED]->(t)
        MERGE (t)-[:USED_DEVICE]->(d)
        MERGE (t)-[:ORIGINATED_FROM]->(i)
        MERGE (t)-[:PAID_TO]->(m)
        MERGE (a)-[:ACCESSED_VIA]->(d)
        MERGE (a)-[:CONNECTED_FROM]->(i)
        """

        try:
            with self.driver.session() as session:
                session.run(ingest_cypher, params)
            logger.info("Successfully ingested transaction %s into Neo4j graph topology", tx_id)
            return True
        except Exception as e:
            logger.error("Failed to ingest transaction %s into Neo4j: %s", tx_id, e)
            return False

    def get_account_subgraph(self, account_id: str, limit_tx: int = 15) -> AccountGraphResponse:
        """
        Retrieves a bounded subgraph around an Account node:
        Account -> Transactions -> Device, IP, Merchant.
        """
        acct_id = str(account_id).strip()
        nodes_dict: Dict[str, GraphNode] = {}
        edges_list: List[GraphEdge] = []

        if not self.verify_connectivity():
            logger.warning("Neo4j is not connected when querying account subgraph for %s", acct_id)
            return AccountGraphResponse(account_id=acct_id, nodes=[], edges=[])

        # Cypher query with traversal bounds and parameters
        cypher = """
        MATCH (a:Account {account_id: $account_id})
        OPTIONAL MATCH (a)-[:PERFORMED]->(t:Transaction)
        WITH a, t ORDER BY t.transaction_date DESC LIMIT $limit_tx
        OPTIONAL MATCH (t)-[:USED_DEVICE]->(d:Device)
        OPTIONAL MATCH (t)-[:ORIGINATED_FROM]->(i:IP)
        OPTIONAL MATCH (t)-[:PAID_TO]->(m:Merchant)
        RETURN a,
               collect(DISTINCT t) AS transactions,
               collect(DISTINCT d) AS devices,
               collect(DISTINCT i) AS ips,
               collect(DISTINCT m) AS merchants
        """

        try:
            with self.driver.session() as session:
                result = session.run(cypher, {"account_id": acct_id, "limit_tx": limit_tx})
                record = result.single()

                if not record or not record.get("a"):
                    return AccountGraphResponse(account_id=acct_id, nodes=[], edges=[])

                a_node = record["a"]
                nodes_dict[acct_id] = GraphNode(
                    id=acct_id,
                    label=f"Account: {acct_id}",
                    type="Account",
                    properties=dict(a_node),
                )

                for t in record["transactions"]:
                    if t:
                        t_id = t["transaction_id"]
                        nodes_dict[t_id] = GraphNode(
                            id=t_id,
                            label=f"Tx: {t_id} (${float(t.get('transaction_amount', 0)):.2f})",
                            type="Transaction",
                            properties=dict(t),
                        )
                        edges_list.append(GraphEdge(
                            id=f"e_{acct_id}_{t_id}",
                            source=acct_id,
                            target=t_id,
                            label="PERFORMED",
                            type="PERFORMED",
                        ))

                for d in record["devices"]:
                    if d:
                        d_id = d["device_id"]
                        if d_id not in nodes_dict:
                            nodes_dict[d_id] = GraphNode(
                                id=d_id,
                                label=f"Device: {d_id}",
                                type="Device",
                                properties=dict(d),
                            )

                for i in record["ips"]:
                    if i:
                        ip_addr = i["ip_address"]
                        if ip_addr not in nodes_dict:
                            nodes_dict[ip_addr] = GraphNode(
                                id=ip_addr,
                                label=f"IP: {ip_addr}",
                                type="IP",
                                properties=dict(i),
                            )

                for m in record["merchants"]:
                    if m:
                        m_id = m["merchant_id"]
                        if m_id not in nodes_dict:
                            nodes_dict[m_id] = GraphNode(
                                id=m_id,
                                label=f"Merchant: {m_id}",
                                type="Merchant",
                                properties=dict(m),
                            )

            # Query the secondary transaction entity connections
            edge_cypher = """
            MATCH (a:Account {account_id: $account_id})-[:PERFORMED]->(t:Transaction)
            WITH t LIMIT $limit_tx
            OPTIONAL MATCH (t)-[:USED_DEVICE]->(d:Device)
            OPTIONAL MATCH (t)-[:ORIGINATED_FROM]->(i:IP)
            OPTIONAL MATCH (t)-[:PAID_TO]->(m:Merchant)
            RETURN t.transaction_id AS tx_id,
                   d.device_id AS dev_id,
                   i.ip_address AS ip_addr,
                   m.merchant_id AS merch_id
            """
            with self.driver.session() as session:
                edges_res = session.run(edge_cypher, {"account_id": acct_id, "limit_tx": limit_tx})
                for row in edges_res:
                    tx_id = row.get("tx_id")
                    dev_id = row.get("dev_id")
                    ip_addr = row.get("ip_addr")
                    merch_id = row.get("merch_id")

                    if tx_id and dev_id and dev_id in nodes_dict:
                        edges_list.append(GraphEdge(
                            id=f"e_{tx_id}_{dev_id}",
                            source=tx_id,
                            target=dev_id,
                            label="USED_DEVICE",
                            type="USED_DEVICE",
                        ))
                    if tx_id and ip_addr and ip_addr in nodes_dict:
                        edges_list.append(GraphEdge(
                            id=f"e_{tx_id}_{ip_addr}",
                            source=tx_id,
                            target=ip_addr,
                            label="ORIGINATED_FROM",
                            type="ORIGINATED_FROM",
                        ))
                    if tx_id and merch_id and merch_id in nodes_dict:
                        edges_list.append(GraphEdge(
                            id=f"e_{tx_id}_{merch_id}",
                            source=tx_id,
                            target=merch_id,
                            label="PAID_TO",
                            type="PAID_TO",
                        ))

            return AccountGraphResponse(
                account_id=acct_id,
                nodes=list(nodes_dict.values()),
                edges=edges_list,
            )
        except Exception as e:
            logger.error("Error executing Neo4j query for account %s: %s", acct_id, e)
            return AccountGraphResponse(account_id=acct_id, nodes=[], edges=[])
