"""
End-to-end Kafka verification:
  1. Create 'transactions' topic via AdminClient
  2. Produce 10 messages from transactions_clean.csv
  3. Consume and verify all 10 messages
"""
import json
import time
import os
import pandas as pd
# pyrefly: ignore [missing-import]
from confluent_kafka import Producer, Consumer, KafkaError, KafkaException
# pyrefly: ignore [missing-import]
from confluent_kafka.admin import AdminClient, NewTopic

BROKER = 'localhost:9092'
TOPIC  = 'transactions'
DATA_FILE = os.path.join(os.path.dirname(__file__), '../data/transactions_clean.csv')

# ── 1. Create topic ────────────────────────────────────────────────────────────
def create_topic():
    print("\n===== STEP 1: Create topic =====")
    admin = AdminClient({'bootstrap.servers': BROKER})
    meta  = admin.list_topics(timeout=10)
    if TOPIC in meta.topics:
        print(f"[OK] Topic '{TOPIC}' already exists.")
        return
    fs = admin.create_topics([NewTopic(TOPIC, num_partitions=1, replication_factor=1)])
    for topic, f in fs.items():
        try:
            f.result()
            print(f"[OK] Topic '{TOPIC}' created.")
        except Exception as e:
            print(f"[ERROR] Failed to create topic: {e}")
            raise

# ── 2. Produce 10 messages ─────────────────────────────────────────────────────
produced = []

def on_delivery(err, msg):
    if err:
        print(f"  [FAIL] Delivery error: {err}")
    else:
        produced.append(msg.offset())
        print(f"  [OK] offset={msg.offset()} key={msg.key().decode()}")

def produce_messages(n=10):
    print(f"\n===== STEP 2: Produce {n} messages =====")
    df = pd.read_csv(DATA_FILE)
    p  = Producer({'bootstrap.servers': BROKER})
    for i, (_, row) in enumerate(df.head(n).iterrows()):
        record = row.to_dict()
        p.produce(TOPIC,
                  key=str(record.get('TransactionID', i)),
                  value=json.dumps(record, default=str),
                  callback=on_delivery)
        p.poll(0)
    p.flush(timeout=10)
    print(f"Produced: {len(produced)} messages confirmed.")

# ── 3. Consume & verify ────────────────────────────────────────────────────────
def consume_messages(n=10):
    print(f"\n===== STEP 3: Consume & verify {n} messages =====")
    c = Consumer({
        'bootstrap.servers': BROKER,
        'group.id': 'e2e_verify_group',
        'auto.offset.reset': 'earliest',
        'enable.auto.commit': False,
    })
    c.subscribe([TOPIC])

    received = 0
    deadline = time.time() + 30  # 30s timeout
    while received < n and time.time() < deadline:
        msg = c.poll(timeout=2.0)
        if msg is None:
            continue
        if msg.error():
            if msg.error().code() == KafkaError._PARTITION_EOF:
                continue
            raise KafkaException(msg.error())

        received += 1
        data = json.loads(msg.value().decode('utf-8'))
        print(f"\n  Message {received}/{n}")
        print(f"    TransactionID    : {data.get('TransactionID')}")
        print(f"    AccountID        : {data.get('AccountID')}")
        print(f"    TransactionAmount: {data.get('TransactionAmount')}")
        print(f"    TransactionDate  : {data.get('TransactionDate')}")

    c.close()
    return received

# ── Main ───────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("=" * 55)
    print("  FRAUD DETECTION - KAFKA END-TO-END VERIFICATION")
    print("=" * 55)
    print(f"  Broker : {BROKER}")
    print(f"  Topic  : {TOPIC}")
    print(f"  Data   : {DATA_FILE}")

    create_topic()
    produce_messages(10)
    received = consume_messages(10)

    print("\n" + "=" * 55)
    print("  RESULTS")
    print("=" * 55)
    print(f"  Messages produced : {len(produced)}")
    print(f"  Messages consumed : {received}")
    status = "PASS" if len(produced) == 10 and received == 10 else "FAIL"
    print(f"  Status            : {status}")
    print("=" * 55)
