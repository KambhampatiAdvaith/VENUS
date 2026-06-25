import json
import os
import time

from dotenv import load_dotenv
from kafka import KafkaConsumer

from backend.database.writer import insert_fault


load_dotenv()


KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_FAULT_TOPIC = os.getenv("KAFKA_FAULT_TOPIC", "venus.faults")


def create_consumer() -> KafkaConsumer:
    while True:
        try:
            consumer = KafkaConsumer(
                KAFKA_FAULT_TOPIC,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                group_id="venus-fault-db-writer",
                auto_offset_reset="latest",
                enable_auto_commit=True,
                value_deserializer=lambda value: json.loads(value.decode("utf-8")),
            )

            print(f"[KAFKA] Fault consumer connected to {KAFKA_FAULT_TOPIC}")
            return consumer

        except Exception as error:
            print(f"[KAFKA] Fault consumer connection failed: {error}")
            print("[KAFKA] Retrying in 3 seconds...")
            time.sleep(3)


def normalize_fault_data(kafka_message: dict) -> dict:
    data = kafka_message.get("data", kafka_message)

    if "telemetry" in data:
        return {
            "substation": data["substation"],
            "fault_type": data["fault_type"],
            "severity": data.get("severity", "high"),
            "timestamp": data["timestamp"],
        }

    return {
        "substation": data["substation"],
        "fault_type": data["fault_type"],
        "severity": data.get("severity", "high"),
        "timestamp": data["timestamp"],
    }


def start_fault_consumer() -> None:
    consumer = create_consumer()

    print("[CONSUMER] Waiting for fault messages...")

    for message in consumer:
        try:
            fault_data = normalize_fault_data(message.value)

            insert_fault(fault_data)

            print(
                f"[CONSUMER] Fault processed | "
                f"substation={fault_data.get('substation')} | "
                f"fault_type={fault_data.get('fault_type')} | "
                f"offset={message.offset}"
            )

        except Exception as error:
            print(f"[CONSUMER] Failed to process fault message: {error}")


if __name__ == "__main__":
    start_fault_consumer()