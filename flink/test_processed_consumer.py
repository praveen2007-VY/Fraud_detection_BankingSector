"""
test_processed_consumer.py
==========================
Phase 3 verification consumer.

Reads from Kafka topic 'processed_transactions' and prints:
  TransactionID, AccountID, TransactionAmount,
  TransactionDate, processing_timestamp

Usage:
  python flink/test_processed_consumer.py

Expects:
  - Kafka running on localhost:9092
  - Flink pipeline (fraud_detection.py) running in another terminal
  - 10 test transactions already produced to 'transactions' topic
"""

import json
import sys
import time

from confluent_kafka import Consumer, KafkaError, KafkaException

# ── Config ────────────────────────────────────────────────────────────────────
BROKER           = "localhost:9092"
OUTPUT_TOPIC     = "processed_transactions"
CONSUMER_GROUP   = "phase3-verify"
EXPECTED_COUNT   = 10
POLL_TIMEOUT_S   = 2.0
TOTAL_WAIT_S     = 60          # give Flink up to 60 s to process all messages


def banner(title: str):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def main():
    banner("PHASE 3 — processed_transactions consumer")
    print(f"  Topic         : {OUTPUT_TOPIC}")
    print(f"  Broker        : {BROKER}")
    print(f"  Expecting     : {EXPECTED_COUNT} records")
    print(f"  Wait timeout  : {TOTAL_WAIT_S}s\n")

    consumer = Consumer(
        {
            "bootstrap.servers": BROKER,
            "group.id": CONSUMER_GROUP,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        }
    )
    consumer.subscribe([OUTPUT_TOPIC])

    received   = 0
    errors     = 0
    records    = []
    deadline   = time.time() + TOTAL_WAIT_S

    try:
        while received < EXPECTED_COUNT and time.time() < deadline:
            msg = consumer.poll(timeout=POLL_TIMEOUT_S)

            if msg is None:
                remaining = int(deadline - time.time())
                print(f"  … waiting for messages ({remaining}s remaining, got {received}/{EXPECTED_COUNT})")
                continue

            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    print(f"  [EOF] Reached end of partition")
                    continue
                raise KafkaException(msg.error())

            try:
                data = json.loads(msg.value().decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                print(f"  [PARSE-ERROR] {exc}")
                errors += 1
                continue

            received += 1
            records.append(data)

            print(f"\n  ── Record {received}/{EXPECTED_COUNT} ──────────────────────")
            print(f"     TransactionID        : {data.get('TransactionID', 'N/A')}")
            print(f"     AccountID            : {data.get('AccountID', 'N/A')}")
            print(f"     TransactionAmount    : {data.get('TransactionAmount', 'N/A')}")
            print(f"     TransactionDate      : {data.get('TransactionDate', 'N/A')}")
            print(f"     TransactionType      : {data.get('TransactionType', 'N/A')}")
            print(f"     MerchantID           : {data.get('MerchantID', 'N/A')}")
            print(f"     Channel              : {data.get('Channel', 'N/A')}")
            print(f"     processing_timestamp : {data.get('processing_timestamp', 'MISSING ← ERROR')}")

    finally:
        consumer.close()

    # ── Summary ───────────────────────────────────────────────────────────────
    banner("PHASE 3 RESULTS")
    print(f"  Broker              : {BROKER}")
    print(f"  Output topic        : {OUTPUT_TOPIC}")
    print(f"  Records received    : {received}/{EXPECTED_COUNT}")
    print(f"  Parse errors        : {errors}")

    if records:
        sample = records[0]
        print(f"\n  Example processed JSON (first record):")
        print(f"  " + json.dumps(sample, indent=4).replace("\n", "\n  "))

    if received == EXPECTED_COUNT and errors == 0:
        print(f"\n  Status              : PASS ✓")
        sys.exit(0)
    elif received == 0:
        print(f"\n  Status              : FAIL ✗ (no records received)")
        print("  Possible causes:")
        print("    • Flink pipeline not running — start fraud_detection.py first")
        print("    • 'processed_transactions' topic not yet created")
        print("    • Kafka not running on localhost:9092")
        sys.exit(1)
    else:
        print(f"\n  Status              : PARTIAL ({received}/{EXPECTED_COUNT})")
        sys.exit(2)


if __name__ == "__main__":
    main()
