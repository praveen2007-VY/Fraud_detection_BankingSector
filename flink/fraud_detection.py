"""
fraud_detection.py
==================
Phase 3 — Apache Flink (PyFlink) Pipeline

Architecture:
  Kafka [transactions]
      ↓
  PyFlink (JSON parse + validation)
      ↓
  Kafka [processed_transactions]

Fields consumed (from transactions_clean.csv):
  TransactionID, AccountID, TransactionAmount, TransactionDate,
  TransactionType, Location, DeviceID, IP Address, MerchantID,
  Channel, CustomerAge, CustomerOccupation, TransactionDuration,
  LoginAttempts, AccountBalance, PreviousTransactionDate

Fields added:
  processing_timestamp  — ISO-8601 UTC wall-clock time this record
                          was processed by Flink

Run:
  python flink/fraud_detection.py
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone

import subprocess as _subprocess
import socket as _socket

# ── CRITICAL: Set env vars BEFORE importing pyflink ──────────────────────────
# The Windows hostname contains emoji (U+1F499 💙) which Java's JNI layer
# converts to '??' (two ASCII 0x3f chars). Python sees it as the emoji.
# We use a compiled Java helper to write the hosts file so it contains the
# hostname exactly as Java sees it, ensuring getLocalHost() resolves via our
# custom file.
#
# Fix pipeline:
#   1. Use WriteHostsFile.class to write jvm-hosts (correct hostname encoding)
#   2. -Djdk.net.hosts.file=<path>  → JVM reads our file instead of system DNS
#   3. -Dfile.encoding=UTF-8        → consistent string handling
#   4. FLINK_CONF_DIR → config.yaml → 127.0.0.1 bindings for all Flink ports
#   5. --add-opens → Java 17 JPMS compatibility for PyFlink reflection

_HERE = os.path.dirname(os.path.abspath(__file__))
_CONF_DIR = os.path.join(_HERE, "conf")
_JAVA_EXE = r"C:\Program Files\Eclipse Adoptium\jdk-17.0.20.101-hotspot\bin\java.exe"
_jvm_hosts_path = os.path.join(_CONF_DIR, "jvm-hosts")
os.makedirs(_CONF_DIR, exist_ok=True)

# Step 1: Use WriteHostsFile.class (compiled Java) to write the hosts file.
# This ensures the hostname string matches Java's internal representation exactly.
_write_result = _subprocess.run(
    [_JAVA_EXE, "-cp", _CONF_DIR, "WriteHostsFile", _jvm_hosts_path],
    capture_output=True, text=True, errors="replace",
)
if _write_result.returncode != 0:
    # Fallback: write with Python using '??' (Java's emoji representation)
    import socket as _socket
    _py_hostname = _socket.gethostname()
    # Encode with 'replace' so emoji → '?' then duplicate to '??'
    _content = (
        "127.0.0.1   localhost\n"
        "::1         localhost\n"
        "127.0.0.1   Prvn??\n"
        "127.0.0.1   Prvn?\n"
        "127.0.0.1   PRVN??\n"
        "127.0.0.1   PRVN?\n"
    )
    with open(_jvm_hosts_path, "w", encoding="utf-8") as _f:
        _f.write(_content)

# Step 2: Set env vars (must happen before pyflink import triggers JVM start)
os.environ["FLINK_CONF_DIR"] = _CONF_DIR
_jvm_hosts_jpath = _jvm_hosts_path.replace("\\", "/")
os.environ["_JAVA_OPTIONS"] = (
    "--add-opens java.base/java.util=ALL-UNNAMED "
    "--add-opens java.base/java.lang=ALL-UNNAMED "
    "--add-opens java.base/java.lang.reflect=ALL-UNNAMED "
    "--add-opens java.base/java.io=ALL-UNNAMED "
    f"-Djdk.net.hosts.file={_jvm_hosts_jpath} "
    "-Dfile.encoding=UTF-8 "
    "-Dstdout.encoding=UTF-8 "
    "-Djava.net.preferIPv4Stack=true "
    "-Djava.rmi.server.hostname=127.0.0.1"
)

from pyflink.common import Configuration, WatermarkStrategy
from pyflink.common.serialization import SimpleStringSchema
from pyflink.common.typeinfo import Types
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.connectors.kafka import (
    KafkaOffsetsInitializer,
    KafkaRecordSerializationSchema,
    KafkaSink,
    KafkaSource,
)
from pyflink.datastream.functions import MapFunction

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("fraud_detection")

# ── Config ───────────────────────────────────────────────────────────────────
BROKER           = "localhost:9092"
INPUT_TOPIC      = "transactions"
OUTPUT_TOPIC     = "processed_transactions"
CONSUMER_GROUP   = "flink-fraud-detection"

# Required fields that every valid record must contain
REQUIRED_FIELDS = {
    "TransactionID",
    "AccountID",
    "TransactionAmount",
    "TransactionDate",
    "TransactionType",
    "DeviceID",
    "IP Address",
    "MerchantID",
    "Channel",
}


# ── Processing function ───────────────────────────────────────────────────────
class TransactionProcessor(MapFunction):
    """
    Validates and enriches each transaction record.

    Valid records  → enriched JSON string (forwarded to Kafka sink)
    Invalid records → logged and returned as None (filtered downstream)
    """

    def map(self, raw: str):
        try:
            record = json.loads(raw)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning("[INVALID-JSON] %s | raw=%r", exc, raw[:200])
            return None  # will be filtered out

        # Validate required fields
        missing = REQUIRED_FIELDS - record.keys()
        if missing:
            logger.warning(
                "[MISSING-FIELDS] TransactionID=%s missing=%s",
                record.get("TransactionID", "UNKNOWN"),
                sorted(missing),
            )
            return None

        # Validate TransactionAmount is a number
        try:
            float(record["TransactionAmount"])
        except (TypeError, ValueError):
            logger.warning(
                "[INVALID-AMOUNT] TransactionID=%s amount=%r",
                record.get("TransactionID", "UNKNOWN"),
                record["TransactionAmount"],
            )
            return None

        # Enrich: add processing timestamp
        record["processing_timestamp"] = datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%S.%f"
        ) + "Z"

        logger.info(
            "[PROCESSED] TransactionID=%s AccountID=%s Amount=%s",
            record.get("TransactionID"),
            record.get("AccountID"),
            record.get("TransactionAmount"),
        )

        return json.dumps(record, ensure_ascii=False)


def build_jar_path(filename: str) -> str:
    """Resolve a JAR bundled inside the apache-flink package."""
    import pyflink

    flink_root = os.path.dirname(pyflink.__file__)
    # PyFlink ships connectors under pyflink/lib/ or pyflink/opt/
    for subdir in ("lib", os.path.join("opt", "python")):
        p = os.path.join(flink_root, subdir, filename)
        if os.path.isfile(p):
            return p
    # broad search under the pyflink package directory
    for root, _dirs, files in os.walk(flink_root):
        if filename in files:
            return os.path.join(root, filename)
    raise FileNotFoundError(
        f"Could not locate {filename} inside the pyflink package at {flink_root}"
    )


def find_kafka_connector_jar() -> str:
    """Find the bundled Flink-Kafka connector JAR."""
    import pyflink

    flink_root = os.path.dirname(pyflink.__file__)
    candidates = []
    for root, _dirs, files in os.walk(flink_root):
        for f in files:
            if "kafka" in f.lower() and f.endswith(".jar"):
                candidates.append(os.path.join(root, f))
    if not candidates:
        raise FileNotFoundError(
            f"No kafka connector JAR found under {flink_root}. "
            "Install flink-sql-connector-kafka manually."
        )
    # prefer the SQL connector (includes everything)
    for c in candidates:
        if "sql-connector" in c.lower():
            return c
    return candidates[0]


def main():
    logger.info("=" * 60)
    logger.info("  PHASE 3 — Flink Kafka→Flink→Kafka Pipeline")
    logger.info("=" * 60)
    logger.info("  Input  topic : %s", INPUT_TOPIC)
    logger.info("  Output topic : %s", OUTPUT_TOPIC)
    logger.info("  Broker       : %s", BROKER)

    # ── 0. Work around non-ASCII Windows hostname (e.g. 'Prvn??') ─────────────
    # Flink's MiniCluster calls InetAddress.getLocalHost() which fails when
    # the Windows hostname contains non-ASCII characters. Setting this JVM
    # property before JVM startup forces the use of 127.0.0.1 instead.
    os.environ.setdefault("JAVA_TOOL_OPTIONS",
        "-Djava.net.preferIPv4Stack=true "
        "-Djava.rmi.server.hostname=127.0.0.1"
    )

    # ── 1. Execution environment with explicit localhost binding ──────────────
    config = Configuration()
    # Force MiniCluster to bind to 127.0.0.1 — avoids InetAddress.getLocalHost()
    config.set_string("jobmanager.rpc.address", "127.0.0.1")
    config.set_string("jobmanager.bind-host", "127.0.0.1")
    config.set_string("taskmanager.host", "127.0.0.1")
    config.set_string("taskmanager.bind-host", "0.0.0.0")
    config.set_string("rest.bind-address", "127.0.0.1")
    config.set_string("rest.address", "127.0.0.1")
    config.set_integer("rest.port", 8081)
    config.set_integer("jobmanager.rpc.port", 6123)
    config.set_integer("taskmanager.rpc.port", 0)   # 0 = random free port
    config.set_integer("parallelism.default", 1)
    config.set_boolean("execution.attached", True)
    env = StreamExecutionEnvironment.get_execution_environment(config)
    env.set_parallelism(1)

    # ── 2. Add Kafka connector JAR ────────────────────────────────────────────
    try:
        kafka_jar = find_kafka_connector_jar()
        logger.info("  Kafka JAR    : %s", kafka_jar)
        env.add_jars(f"file:///{kafka_jar.replace(os.sep, '/')}")
    except FileNotFoundError as exc:
        logger.error("[JAR-ERROR] %s", exc)
        logger.error(
            "Hint: run  pip install apache-flink  then retry, or manually "
            "place flink-sql-connector-kafka-*.jar in the flink/lib/ directory."
        )
        sys.exit(1)

    # ── 3. Kafka Source ───────────────────────────────────────────────────────
    source = (
        KafkaSource.builder()
        .set_bootstrap_servers(BROKER)
        .set_topics(INPUT_TOPIC)
        .set_group_id(CONSUMER_GROUP)
        .set_starting_offsets(KafkaOffsetsInitializer.earliest())
        .set_value_only_deserializer(SimpleStringSchema())
        .build()
    )

    # ── 4. Kafka Sink ─────────────────────────────────────────────────────────
    sink = (
        KafkaSink.builder()
        .set_bootstrap_servers(BROKER)
        .set_record_serializer(
            KafkaRecordSerializationSchema.builder()
            .set_topic(OUTPUT_TOPIC)
            .set_value_serialization_schema(SimpleStringSchema())
            .build()
        )
        .build()
    )

    # ── 5. Build pipeline ─────────────────────────────────────────────────────
    stream = env.from_source(
        source,
        WatermarkStrategy.no_watermarks(),
        "Kafka-transactions-source",
        type_info=Types.STRING(),
    )

    processed = (
        stream
        .map(TransactionProcessor(), output_type=Types.STRING())
        .filter(lambda x: x is not None)
    )

    processed.sink_to(sink)

    # ── 6. Execute ────────────────────────────────────────────────────────────
    logger.info("Submitting Flink job …")
    env.execute("fraud-detection-phase3")


if __name__ == "__main__":
    main()
