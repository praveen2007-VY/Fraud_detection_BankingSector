@echo off
SET JAVA_HOME=C:\Program Files\Eclipse Adoptium\jdk-17.0.20.101-hotspot
SET PATH=%JAVA_HOME%\bin;%PATH%
SET KAFKA_HEAP_OPTS=-Xmx1G -Xms1G
echo Starting Kafka KRaft broker...
C:\kfk\bin\windows\kafka-server-start.bat C:\kfk\config\kraft\server.properties
