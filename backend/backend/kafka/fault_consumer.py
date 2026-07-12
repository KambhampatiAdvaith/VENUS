import json
import os
import time
from typing import Callable

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


def process_fault_message(
    kafka_message: dict,
    on_fault_inserted: Callable[[dict], None] | None = None,
) -> dict | None:
    fault_data = normalize_fault_data(kafka_message)
    inserted_fault = insert_fault(fault_data)

    if inserted_fault is not None and on_fault_inserted is not None:
        on_fault_inserted(inserted_fault)

    return inserted_fault


def start_fault_consumer(
    on_fault_inserted: Callable[[dict], None] | None = None,
) -> None:
    while True:
        consumer = None

        try:
            consumer = create_consumer()

            print("[CONSUMER] Waiting for fault messages...")

            for message in consumer:
                try:
                    fault_data = process_fault_message(
                        message.value,
                        on_fault_inserted,
                    )

                    if fault_data is None:
                        continue

                    print(
                        f"[CONSUMER] Fault processed | "
                        f"substation={fault_data.get('substation')} | "
                        f"fault_type={fault_data.get('fault_type')} | "
                        f"offset={message.offset}"
                    )

                except Exception as error:
                    print(f"[CONSUMER] Failed to process fault message: {error}")

        except KeyboardInterrupt:
            print("[KAFKA] Fault consumer stopped by user.")
            break

        except Exception as error:
            print(f"[KAFKA] Fault consumer crashed: {error}")
            print("[KAFKA] Restarting consumer in 3 seconds...")
            time.sleep(3)

        finally:
            if consumer is not None:
                try:
                    consumer.close()
                except Exception:
                    pass


if __name__ == "__main__":
    start_fault_consumer()