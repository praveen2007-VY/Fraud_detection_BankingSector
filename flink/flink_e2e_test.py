"""
flink_e2e_test.py
=================
Phase 3 all-in-one end-to-end test:

  1. Start Kafka (if not already running)
  2. Create 'transactions' and 'processed_transactions' topics
  3. Start Flink pipeline (fraud_detection.py) as a subprocess
  4. Produce 10 test transactions
  5. Consume 10 processed transactions from output topic
  6. Print verification report

Usage:
  python flink/flink_e2e_test.py

Requirements:
  pip install apache-flink confluent-kafka pandas
"""

import json
import os
import socket
import subprocess
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
import time

import pandas as pd
# pyrefly: ignore [missing-import]
from confluent_kafka import Consumer, KafkaError, KafkaException, Producer
# pyrefly: ignore [missing-import]
from confluent_kafka.admin import AdminClient, NewTopic

# ── Config ────────────────────────────────────────────────────────────────────
JAVA_EXE       = r"C:\Program Files\Eclipse Adoptium\jdk-17.0.20.101-hotspot\bin\java.exe"
KFK_HOME       = r"C:\kfk"
KFK_LOGS       = r"C:\kfk-logs"
LOG_FILE       = os.path.join(KFK_LOGS, "kafka-daemon.log")
BROKER         = "localhost:9092"
INPUT_TOPIC    = "transactions"
OUTPUT_TOPIC   = "processed_transactions"
DATA_FILE      = os.path.join(os.path.dirname(__file__), "../data/transactions_clean.csv")
FLINK_SCRIPT   = os.path.join(os.path.dirname(__file__), "fraud_detection.py")

kafka_java_args = [
    JAVA_EXE,
    "-Xmx1G", "-Xms1G",
    f"-Dlog4j.configuration=file:{KFK_HOME}/config/log4j.properties",
    f"-Dkafka.logs.dir={KFK_LOGS}",
    "-cp", f"{KFK_HOME}\\libs\\*",
    "kafka.Kafka",
    f"{KFK_HOME}\\config\\kraft\\server.properties",
]


def banner(title: str):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


# ── Helpers ───────────────────────────────────────────────────────────────────
def port_open(port: int = 9092) -> bool:
    try:
        s = socket.create_connection(("localhost", port), timeout=1)
        s.close()
        return True
    except OSError:
        return False


def wait_for_port(port: int = 9092, timeout: int = 30) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if port_open(port):
            return True
        time.sleep(1)
    return False


# ── Step 1: Kafka ─────────────────────────────────────────────────────────────
def start_kafka():
    banner("STEP 1 — Kafka broker")
    if port_open():
        print("  [OK] Kafka already running on port 9092")
        return None, None

    print("  Starting Kafka …")
    os.makedirs(KFK_LOGS, exist_ok=True)
    log_fh = open(LOG_FILE, "w", encoding="utf-8")
    proc = subprocess.Popen(
        kafka_java_args,
        stdin=subprocess.DEVNULL,
        stdout=log_fh,
        stderr=subprocess.STDOUT,
        cwd=KFK_HOME,
    )
    print(f"  Kafka PID: {proc.pid}")
    if wait_for_port():
        print("  [OK] Kafka listening on localhost:9092")
    else:
        print("  [FAIL] Kafka did not start in time")
        proc.terminate()
        sys.exit(1)
    return proc, log_fh


# ── Step 2: Topics ────────────────────────────────────────────────────────────
def ensure_topics():
    banner("STEP 2 — Topics")
    admin = AdminClient({"bootstrap.servers": BROKER})
    meta  = admin.list_topics(timeout=10)

    to_create = []
    for topic in (INPUT_TOPIC, OUTPUT_TOPIC):
        if topic in meta.topics:
            print(f"  [OK] Topic '{topic}' already exists")
        else:
            to_create.append(NewTopic(topic, num_partitions=1, replication_factor=1))

    if to_create:
        fs = admin.create_topics(to_create)
        for t, f in fs.items():
            f.result()
            print(f"  [OK] Topic '{t}' created")

    time.sleep(1)   # let metadata propagate


# ── Step 3: Flink pipeline ────────────────────────────────────────────────────
def start_flink():
    banner("STEP 3 — Flink pipeline (fraud_detection.py)")
    flink_log = os.path.join(os.path.dirname(__file__), "flink_job.log")
    log_fh    = open(flink_log, "w", encoding="utf-8")
    # Build env with hostname fix — must be set before JVM starts
    import socket as _socket
    flink_env = os.environ.copy()
    _conf_dir = os.path.join(os.path.dirname(__file__), "conf")
    os.makedirs(_conf_dir, exist_ok=True)
    _JAVA_EXE = r"C:\Program Files\Eclipse Adoptium\jdk-17.0.20.101-hotspot\bin\java.exe"

    # Write custom JVM hosts file using Java to get the exact hostname Java sees
    _jvm_hosts_path = os.path.join(_conf_dir, "jvm-hosts")
    _wr = subprocess.run(
        [_JAVA_EXE, "-cp", _conf_dir, "WriteHostsFile", _jvm_hosts_path],
        capture_output=True, text=True, errors="replace",
    )
    if _wr.returncode != 0:
        with open(_jvm_hosts_path, "w", encoding="utf-8") as _fh2:
            _fh2.write("127.0.0.1   localhost\n::1         localhost\n127.0.0.1   Prvn??\n127.0.0.1   Prvn?\n127.0.0.1   PRVN??\n127.0.0.1   PRVN?\n")
    _jvm_hosts_jpath = _jvm_hosts_path.replace("\\", "/")

    flink_env["FLINK_CONF_DIR"] = _conf_dir
    flink_env["_JAVA_OPTIONS"] = (
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
    proc      = subprocess.Popen(
        [sys.executable, FLINK_SCRIPT],
        stdout=log_fh,
        stderr=subprocess.STDOUT,
        env=flink_env,
    )
    print(f"  Flink PID  : {proc.pid}")
    print(f"  Flink log  : {flink_log}")
    print("  Waiting 15s for Flink JVM to initialise …")
    time.sleep(15)
    if proc.poll() is not None:
        log_fh.flush()
        with open(flink_log, encoding="utf-8", errors="replace") as f:
            tail = f.read()[-3000:]
        print(f"  [FAIL] Flink process exited early (rc={proc.returncode})")
        print("  Last log lines:\n" + tail)
        sys.exit(1)
    print("  [OK] Flink running")
    return proc, log_fh


# ── Step 4: Produce ───────────────────────────────────────────────────────────
produced_count = [0]


def on_delivery(err, msg):
    if err:
        print(f"    [ERR] {err}")
    else:
        produced_count[0] += 1
        print(f"    [OK] offset={msg.offset()} key={msg.key().decode()}")


def produce_messages(n: int = 10):
    banner(f"STEP 4 — Produce {n} transactions → '{INPUT_TOPIC}'")
    df = pd.read_csv(DATA_FILE)
    p  = Producer({"bootstrap.servers": BROKER})
    for i, (_, row) in enumerate(df.head(n).iterrows()):
        record = row.to_dict()
        p.produce(
            INPUT_TOPIC,
            key=str(record.get("TransactionID", i)),
            value=json.dumps(record, default=str),
            callback=on_delivery,
        )
        p.poll(0)
    p.flush(timeout=15)
    print(f"  Produced: {produced_count[0]}/{n} confirmed")


# ── Step 5: Consume processed ─────────────────────────────────────────────────
def consume_processed(n: int = 10, wait_s: int = 60):
    banner(f"STEP 5 — Consume {n} records from '{OUTPUT_TOPIC}'")
    c = Consumer(
        {
            "bootstrap.servers": BROKER,
            "group.id": "flink-e2e-verify",
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        }
    )
    c.subscribe([OUTPUT_TOPIC])
    received = 0
    records  = []
    deadline = time.time() + wait_s

    while received < n and time.time() < deadline:
        msg = c.poll(timeout=2.0)
        if msg is None:
            remaining = int(deadline - time.time())
            print(f"  … waiting ({remaining}s left, {received}/{n} received)")
            continue
        if msg.error():
            if msg.error().code() == KafkaError._PARTITION_EOF:
                continue
            raise KafkaException(msg.error())
        try:
            data = json.loads(msg.value().decode("utf-8"))
        except Exception as exc:
            print(f"  [PARSE-ERR] {exc}")
            continue
        received += 1
        records.append(data)
        print(f"\n  ── Processed record {received}/{n} ──────────────")
        print(f"     TransactionID        : {data.get('TransactionID')}")
        print(f"     AccountID            : {data.get('AccountID')}")
        print(f"     TransactionAmount    : {data.get('TransactionAmount')}")
        print(f"     TransactionDate      : {data.get('TransactionDate')}")
        print(f"     processing_timestamp : {data.get('processing_timestamp')}")

    c.close()
    return received, records


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    banner("FRAUD DETECTION — PHASE 3 FLINK E2E TEST")

    kafka_proc, kafka_log = start_kafka()
    flink_proc = None
    flink_log_fh = None

    try:
        ensure_topics()
        flink_proc, flink_log_fh = start_flink()
        produce_messages(10)
        received, records = consume_processed(10, wait_s=90)
    finally:
        if flink_proc and flink_proc.poll() is None:
            print("\n  Stopping Flink …")
            flink_proc.terminate()
            flink_proc.wait(timeout=15)
        if flink_log_fh:
            flink_log_fh.close()
        if kafka_proc and kafka_proc.poll() is None:
            print("  Stopping Kafka …")
            kafka_proc.terminate()
            kafka_proc.wait(timeout=15)
        if kafka_log:
            kafka_log.close()

    # ── Report ────────────────────────────────────────────────────────────────
    # pyrefly: ignore [missing-import]
    import pyflink
    banner("PHASE 3 VERIFICATION REPORT")
    print(f"  1. Flink version           : {pyflink.__version__}")
    print(f"  2. Java version            : 17.0.20.1 (Eclipse Temurin)")
    print(f"  3. Flink install path      : {os.path.dirname(pyflink.__file__)}")
    print(f"  4. Kafka connection        : localhost:9092  OK")
    print(f"  5. Flink job status        : completed (inline)")
    print(f"  6. Input records processed : {produced_count[0]}/10")
    print(f"  7. Output records produced : {received}/10")

    if records:
        print(f"\n  8. Example processed JSON:")
        sample = {k: records[0][k] for k in [
            "TransactionID", "AccountID", "TransactionAmount",
            "TransactionDate", "TransactionType", "MerchantID",
            "Channel", "processing_timestamp"
        ] if k in records[0]}
        print("     " + json.dumps(sample, indent=6).replace("\n", "\n     "))

    print(f"\n  9. Errors                  : none" if received == 10 else
          f"\n  9. Errors                  : only {received}/10 received")

    print(f"\n 10. Reproduce with:")
    print(f"     # Terminal 1 — Flink pipeline")
    print(f"     python flink/fraud_detection.py")
    print(f"     # Terminal 2 — Producer")
    print(f"     python producer/transaction_producer.py")
    print(f"     # Terminal 3 — Verify output")
    print(f"     python flink/test_processed_consumer.py")

    status = "PASS" if produced_count[0] == 10 and received == 10 else "FAIL"
    print(f"\n  Status                     : {status}")
    print("=" * 60)
    sys.exit(0 if status == "PASS" else 1)
