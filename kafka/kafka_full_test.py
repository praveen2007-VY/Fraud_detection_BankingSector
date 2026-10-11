"""
kafka_full_test.py
==================
All-in-one: starts Kafka, creates topic, produces 10 messages, consumes them.
Runs entirely within one Python process so Kafka stays alive throughout.
"""
import subprocess, json, time, os, socket, signal, sys
import pandas as pd
# pyrefly: ignore [missing-import]
from confluent_kafka import Producer, Consumer, KafkaError, KafkaException
# pyrefly: ignore [missing-import]
from confluent_kafka.admin import AdminClient, NewTopic

# ── Config ─────────────────────────────────────────────────────────────────────
JAVA_EXE  = r"C:\Program Files\Eclipse Adoptium\jdk-17.0.20.101-hotspot\bin\java.exe"
KFK_HOME  = r"C:\kfk"
KFK_LOGS  = r"C:\kfk-logs"
LOG_FILE  = os.path.join(KFK_LOGS, "kafka-daemon.log")
BROKER    = "localhost:9092"
TOPIC     = "test_transactions"
DATA_FILE = os.path.join(os.path.dirname(__file__), "../data/transactions_clean.csv")

java_args = [
    JAVA_EXE,
    "-Xmx1G", "-Xms1G",
    f"-Dlog4j.configuration=file:{KFK_HOME}/config/log4j.properties",
    f"-Dkafka.logs.dir={KFK_LOGS}",
    "-cp", f"{KFK_HOME}\\libs\\*",
    "kafka.Kafka",
    f"{KFK_HOME}\\config\\kraft\\server.properties",
]

# ── Helpers ────────────────────────────────────────────────────────────────────
def wait_for_port(port=9092, timeout=30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            s = socket.create_connection(("localhost", port), timeout=1)
            s.close()
            return True
        except:
            time.sleep(1)
    return False

# ── Step 1: Start Kafka subprocess ─────────────────────────────────────────────
def start_kafka():
    print("\n" + "="*55)
    print("  STEP 1 — Start Kafka broker")
    print("="*55)
    os.makedirs(KFK_LOGS, exist_ok=True)
    log_fh = open(LOG_FILE, "w", encoding="utf-8")
    proc = subprocess.Popen(
        java_args,
        stdin=subprocess.DEVNULL,
        stdout=log_fh,
        stderr=subprocess.STDOUT,
        cwd=KFK_HOME,
    )
    print(f"  Kafka PID: {proc.pid}")
    print("  Waiting for port 9092...")
    if wait_for_port():
        print("  [OK] Kafka is listening on port 9092")
    else:
        print("  [FAIL] Kafka did not start in time")
        proc.terminate()
        sys.exit(1)
    return proc, log_fh

# ── Step 2: Create topic ────────────────────────────────────────────────────────
def create_topic():
    print("\n" + "="*55)
    print("  STEP 2 — Create topic 'transactions'")
    print("="*55)
    admin = AdminClient({"bootstrap.servers": BROKER})
    meta = admin.list_topics(timeout=10)
    if TOPIC in meta.topics:
        print(f"  [OK] Topic already exists")
        return
    fs = admin.create_topics([NewTopic(TOPIC, num_partitions=1, replication_factor=1)])
    for t, f in fs.items():
        f.result()
        print(f"  [OK] Topic '{t}' created")

# ── Step 3: Produce 10 messages ────────────────────────────────────────────────
produced_count = [0]

def on_delivery(err, msg):
    if err:
        print(f"    [ERR] {err}")
    else:
        produced_count[0] += 1
        print(f"    [OK] offset={msg.offset()} key={msg.key().decode()}")

def produce_messages(n=10):
    print("\n" + "="*55)
    print(f"  STEP 3 — Produce {n} messages")
    print("="*55)
    df = pd.read_csv(DATA_FILE)
    p  = Producer({"bootstrap.servers": BROKER})
    for i, (_, row) in enumerate(df.head(n).iterrows()):
        record = row.to_dict()
        p.produce(TOPIC,
                  key=str(record.get("TransactionID", i)),
                  value=json.dumps(record, default=str),
                  callback=on_delivery)
        p.poll(0)
    p.flush(timeout=15)
    print(f"  Produced: {produced_count[0]}/{n} confirmed")

# ── Step 4: Consume & verify ───────────────────────────────────────────────────
def consume_messages(n=10):
    print("\n" + "="*55)
    print(f"  STEP 4 — Consume & verify {n} messages")
    print("="*55)
    c = Consumer({
        "bootstrap.servers": BROKER,
        "group.id": "e2e_verify",
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
    })
    c.subscribe([TOPIC])
    received = 0
    deadline = time.time() + 30
    while received < n and time.time() < deadline:
        msg = c.poll(timeout=2.0)
        if msg is None:
            continue
        if msg.error():
            if msg.error().code() == KafkaError._PARTITION_EOF:
                continue
            raise KafkaException(msg.error())
        received += 1
        d = json.loads(msg.value().decode("utf-8"))
        print(f"\n  Message {received}/{n}:")
        print(f"    TransactionID    : {d.get('TransactionID')}")
        print(f"    AccountID        : {d.get('AccountID')}")
        print(f"    TransactionAmount: {d.get('TransactionAmount')}")
        print(f"    TransactionDate  : {d.get('TransactionDate')}")
    c.close()
    return received

# ── Main ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "="*55)
    print("  FRAUD DETECTION — KAFKA PHASE 2 E2E TEST")
    print("="*55)

    kafka_proc, log_fh = start_kafka()
    try:
        create_topic()
        produce_messages(10)
        received = consume_messages(10)
    finally:
        print("\n  Stopping Kafka broker...")
        kafka_proc.terminate()
        kafka_proc.wait(timeout=10)
        log_fh.close()
        print("  Kafka stopped.")

    print("\n" + "="*55)
    print("  PHASE 2 RESULTS")
    print("="*55)
    print(f"  Kafka installation : OK (C:\\kfk)")
    print(f"  KRaft mode         : OK (no ZooKeeper)")
    print(f"  Broker             : localhost:9092")
    print(f"  Topic              : {TOPIC}")
    print(f"  Messages produced  : {produced_count[0]}/10")
    print(f"  Messages consumed  : {received}/10")
    status = "PASS" if produced_count[0] == 10 and received == 10 else "FAIL"
    print(f"  Status             : {status}")
    print("="*55)
