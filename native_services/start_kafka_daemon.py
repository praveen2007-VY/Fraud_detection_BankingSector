"""
start_kafka_daemon.py
Starts Kafka as a TRULY detached Windows process — survives parent shell exit.
Run once: python native_services/start_kafka_daemon.py
"""
import subprocess
import os
import sys
import time
import socket

JAVA_HOME = r"C:\Program Files\Eclipse Adoptium\jdk-17.0.20.101-hotspot"
JAVA_EXE  = os.path.join(JAVA_HOME, "bin", "java.exe")
KFK_HOME  = r"C:\kfk"
KFK_LOGS  = r"C:\kfk-logs"
KFK_DATA  = r"C:\kfk-data"
LOG_FILE  = os.path.join(KFK_LOGS, "kafka-daemon.log")

# Windows process creation flags
DETACHED_PROCESS          = 0x00000008
CREATE_NEW_PROCESS_GROUP  = 0x00000200
CREATE_NO_WINDOW          = 0x08000000
CREATE_BREAKAWAY_FROM_JOB = 0x01000000  # Escape agent Job Object containment

def is_port_open(port=9092, timeout=2):
    try:
        s = socket.create_connection(("localhost", port), timeout=timeout)
        s.close()
        return True
    except:
        return False

def start_kafka():
    os.makedirs(KFK_LOGS, exist_ok=True)

    java_args = [
        JAVA_EXE,
        "-Xmx1G", "-Xms1G",
        f"-Dlog4j.configuration=file:{KFK_HOME}/config/log4j.properties",
        f"-Dkafka.logs.dir={KFK_LOGS}",
        "-cp", f"{KFK_HOME}\\libs\\*",
        "kafka.Kafka",
        f"{KFK_HOME}\\config\\kraft\\server.properties",
    ]

    print(f"Starting Kafka daemon...")
    print(f"  Log: {LOG_FILE}")

    log_fh = open(LOG_FILE, "w", encoding="utf-8")
    flags = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW
    try:
        proc = subprocess.Popen(
            java_args,
            stdin=subprocess.DEVNULL,
            stdout=log_fh,
            stderr=subprocess.STDOUT,
            creationflags=flags | CREATE_BREAKAWAY_FROM_JOB,
            close_fds=True,
            cwd=KFK_HOME,
        )
    except PermissionError:
        proc = subprocess.Popen(
            java_args,
            stdin=subprocess.DEVNULL,
            stdout=log_fh,
            stderr=subprocess.STDOUT,
            creationflags=flags,
            close_fds=True,
            cwd=KFK_HOME,
        )

    print(f"  Kafka PID: {proc.pid}")
    print("  Waiting up to 30s for port 9092...")

    for i in range(30):
        time.sleep(1)
        if is_port_open():
            print(f"  [OK] Port 9092 is open after {i+1}s!")
            # Write PID file for future reference
            with open(os.path.join(KFK_LOGS, "kafka.pid"), "w") as f:
                f.write(str(proc.pid))
            return proc.pid

    print("  [WARN] Port 9092 not open after 30s. Check log:")
    print(f"  {LOG_FILE}")
    return proc.pid

if __name__ == "__main__":
    if is_port_open():
        print("[OK] Kafka already running on port 9092.")
        sys.exit(0)
    pid = start_kafka()
    print(f"\nKafka daemon started (PID {pid}).")
    print(f"Stop it with: Stop-Process -Id {pid} -Force")
