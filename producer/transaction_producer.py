import pandas as pd
import json
import time
from confluent_kafka import Producer
import os

KAFKA_BROKER = 'localhost:9092'
KAFKA_TOPIC = 'transactions'
DATA_FILE = os.path.join(os.path.dirname(__file__), '../data/transactions_clean.csv')

def receipt(err, msg):
    if err is not None:
        print(f"Failed to deliver message: {err}")
    else:
        print(f"Produced message to topic {msg.topic()} partition [{msg.partition()}] @ offset {msg.offset()}")

def main():
    print(f"Loading data from {DATA_FILE}...")
    df = pd.read_csv(DATA_FILE)
    
    print(f"Initializing Kafka Producer at {KAFKA_BROKER}...")
    producer = Producer({'bootstrap.servers': KAFKA_BROKER})
    
    print(f"Starting to produce messages to topic '{KAFKA_TOPIC}'...")
    count = 0
    for index, row in df.iterrows():
        # Convert row to dictionary
        record = row.to_dict()
        
        # Convert record to JSON string
        record_json = json.dumps(record, default=str)
        
        # Produce message
        producer.produce(
            KAFKA_TOPIC, 
            key=str(record.get('TransactionID', index)), 
            value=record_json, 
            callback=receipt
        )
        
        # Poll to handle delivery reports
        producer.poll(0)
        
        count += 1
        time.sleep(0.1) # Simulate real-time streaming with a small delay
        
        if count % 10 == 0:
            producer.flush()
            print(f"--- Flushed {count} messages ---")
            
        if count >= 10:
            print("Stopping after 10 messages as requested for testing.")
            break
            
    producer.flush()
    print(f"Finished producing {count} messages.")

if __name__ == '__main__':
    main()
