import json
from confluent_kafka import Consumer, KafkaError, KafkaException

def test_consumer():
    conf = {
        'bootstrap.servers': 'localhost:9092',
        'group.id': 'test_verification_group',
        'auto.offset.reset': 'earliest'
    }
    
    consumer = Consumer(conf)
    topic = 'transactions'
    consumer.subscribe([topic])
    
    print(f"Starting consumer, listening to topic '{topic}'...")
    print("Waiting for messages...")
    
    messages_processed = 0
    max_messages = 10
    
    try:
        while messages_processed < max_messages:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
                
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    print(f"Reached end of partition {msg.topic()} [{msg.partition()}] at offset {msg.offset()}")
                else:
                    raise KafkaException(msg.error())
            else:
                messages_processed += 1
                try:
                    # Deserialize JSON
                    val = msg.value().decode('utf-8')
                    data = json.loads(val)
                    
                    # Print required fields
                    print("-" * 40)
                    print(f"Message {messages_processed}/{max_messages}")
                    print(f"TransactionID    : {data.get('TransactionID')}")
                    print(f"AccountID        : {data.get('AccountID')}")
                    print(f"TransactionAmount: {data.get('TransactionAmount')}")
                    print(f"TransactionDate  : {data.get('TransactionDate')}")
                except Exception as e:
                    print(f"Error processing message: {e}")
                    print(f"Raw message: {msg.value()}")

    except KeyboardInterrupt:
        print("Aborted by user.")
    finally:
        consumer.close()
        print(f"Consumer closed. Processed {messages_processed} messages.")

if __name__ == '__main__':
    test_consumer()
