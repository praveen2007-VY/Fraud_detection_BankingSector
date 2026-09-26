# Kafka Infrastructure (Phase 1)

This directory and the root [`docker-compose.yml`](../docker-compose.yml) configure the local Apache Kafka messaging backbone for the Fraud Detection System.

---

## Architecture Overview

- **Broker**: Confluent Platform Kafka (`confluentinc/cp-kafka:7.6.1`)
- **Mode**: KRaft (Kafka Raft metadata mode, eliminating ZooKeeper dependency)
- **Host Port**: `9092` (mapped to `localhost:9092` for external applications and Python producers/consumers)
- **Internal Network Port**: `29092` (used for communication between Docker containers on the bridge network)
- **Topics Initializer**: `kafka-init-topics` container automatically provisions the `transactions` topic once the broker becomes healthy.
- **Persistence**: Managed volume `kafka_data` mapped to `/var/lib/kafka/data`.
- **Restart Policy**: `restart: unless-stopped` for safe recovery.

---

## Prerequisites

- **Docker Desktop** installed and running on Windows.
- Ensure the **WSL2 backend** or **Hyper-V** is enabled in Docker Desktop settings.

---

## Operations & Commands

Execute these commands from the project root (`fraud-detection-system/`):

### 1. Start Kafka
Start Kafka in detached mode:
```bash
docker compose up -d
```
*The `kafka` service starts first. Once its healthcheck passes, `kafka-init-topics` runs, ensures the `transactions` topic exists, and exits.*

### 2. Check Service Status & Health
Check the container status:
```bash
docker compose ps
```
Or inspect container health:
```bash
docker inspect --format='{{json .State.Health.Status}}' kafka
```

### 3. View Logs
View Kafka broker logs:
```bash
docker compose logs -f kafka
```
View topic initialization logs:
```bash
docker compose logs kafka-init-topics
```

### 4. Verify the `transactions` Topic
List topics:
```bash
docker compose exec kafka kafka-topics --bootstrap-server localhost:9092 --list
```

Describe the `transactions` topic:
```bash
docker compose exec kafka kafka-topics --bootstrap-server localhost:9092 --describe --topic transactions
```

### 5. Stop Kafka
Stop the containers while preserving topic data in the volume:
```bash
docker compose down
```

To stop containers and wipe the data volume:
```bash
docker compose down -v
```
