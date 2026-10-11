"""
transaction_producer.py
=======================
Streams clean transaction records from transactions_clean.csv to Kafka.

Features:
- Configurable --offset and --limit (defaults to publishing all 2,512 rows)
- Configurable --delay between records
- Delivery report callbacks with confirmation accounting
- Clean single-pass execution without endless loop
"""

import argparse
import json
import logging
import os
import sys
import time
from typing import Optional

import pandas as pd
# pyrefly: ignore [missing-import]
from confluent_kafka import Producer

# Ensure workspace root is in sys.path
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

try:
    from config.config import KAFKA_BROKER, KAFKA_INPUT_TOPIC
except ImportError:
    KAFKA_BROKER = "localhost:9092"
    KAFKA_INPUT_TOPIC = "transactions"

DATA_FILE = os.path.join(_ROOT, "data", "transactions_clean.csv")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("transaction_producer")


def run_producer(
    broker: str = KAFKA_BROKER,
    topic: str = KAFKA_INPUT_TOPIC,
    data_file: str = DATA_FILE,
    offset: int = 0,
    limit: Optional[int] = None,
    delay: float = 0.001,
) -> int:
    """
    Publish clean transaction records to Kafka.
    Returns the total number of successfully confirmed messages.
    """
    logger.info("Loading data from: %s", data_file)
    if not os.path.exists(data_file):
        raise FileNotFoundError(f"Data file not found: {data_file}")

    df = pd.read_csv(data_file)
    total_available = len(df)
    logger.info("Total rows in dataset: %d", total_available)

    # Apply offset and limit
    if offset > 0:
        df = df.iloc[offset:]
    if limit is not None and limit > 0:
        df = df.iloc[:limit]

    records_to_send = len(df)
    logger.info(
        "Publishing %d records (offset=%d, limit=%s) to topic '%s' on %s ...",
        records_to_send,
        offset,
        limit if limit is not None else "ALL",
        topic,
        broker,
    )

    producer = Producer({
        "bootstrap.servers": broker,
        "linger.ms": 5,
        "queue.buffering.max.messages": 100000,
    })

    confirmed = [0]
    errors = [0]

    def delivery_report(err, msg):
        if err is not None:
            logger.error("Failed to deliver message: %s", err)
            errors[0] += 1
        else:
            confirmed[0] += 1

    start_time = time.time()
    for idx, (_, row) in enumerate(df.iterrows()):
        record = row.to_dict()
        tx_id = str(record.get("TransactionID", f"TX_{idx}"))
        payload = json.dumps(record, default=str)

        producer.produce(
            topic,
            key=tx_id,
            value=payload,
            callback=delivery_report,
        )

        producer.poll(0)
        if delay > 0:
            time.sleep(delay)

        if (idx + 1) % 500 == 0:
            producer.flush(5.0)
            logger.info("Produced & flushed %d / %d records...", idx + 1, records_to_send)

    producer.flush(15.0)
    elapsed = time.time() - start_time
    logger.info(
        "Finished: %d / %d confirmed in %.2fs (errors: %d)",
        confirmed[0],
        records_to_send,
        elapsed,
        errors[0],
    )

    if errors[0] > 0:
        raise RuntimeError(f"Encountered {errors[0]} delivery errors while publishing.")

    return confirmed[0]


def main():
    parser = argparse.ArgumentParser(description="Clean Kafka Transaction Producer")
    parser.add_argument("--broker", default=KAFKA_BROKER, help="Kafka broker address")
    parser.add_argument("--topic", default=KAFKA_INPUT_TOPIC, help="Target Kafka topic")
    parser.add_argument("--data-file", default=DATA_FILE, help="Path to clean CSV")
    parser.add_argument("--offset", type=int, default=0, help="Row offset to start producing from")
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of records to produce (None = all)")
    parser.add_argument("--delay", type=float, default=0.001, help="Delay in seconds between records (default 0.001s)")

    args = parser.parse_args()
    count = run_producer(
        broker=args.broker,
        topic=args.topic,
        data_file=args.data_file,
        offset=args.offset,
        limit=args.limit,
        delay=args.delay,
    )
    print(f"\n[OK] Successfully published {count} transaction records.")


if __name__ == "__main__":
    main()
