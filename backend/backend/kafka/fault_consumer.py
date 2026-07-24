import json
import os
import time
from typing import Callable

from dotenv import load_dotenv
from kafka import KafkaConsumer

from backend.database.writer import insert_fault
from backend.utils.logging import BackoffState, get_logger, retry_with_backoff


load_dotenv()


KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_FAULT_TOPIC = os.getenv("KAFKA_FAULT_TOPIC", "venus.faults")

logger = get_logger("backend.kafka.fault_consumer")


def create_consumer() -> KafkaConsumer:
    consumer = retry_with_backoff(
        lambda: KafkaConsumer(
            KAFKA_FAULT_TOPIC,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            group_id="venus-fault-db-writer",
            auto_offset_reset="latest",
            enable_auto_commit=True,
            value_deserializer=lambda value: json.loads(value.decode("utf-8")),
            api_version=(3, 6, 0),
            request_timeout_ms=30000,
            session_timeout_ms=10000,
            heartbeat_interval_ms=3000,
            consumer_timeout_ms=1000,
        ),
        logger=logger,
        operation_name=f"Fault consumer connection to {KAFKA_FAULT_TOPIC}",
        initial_delay=1.0,
        max_delay=15.0,
        factor=2.0,
        jitter=0.5,
    )
    logger.info(
        "Fault consumer connected to topic=%s on bootstrap_servers=%s",
        KAFKA_FAULT_TOPIC,
        KAFKA_BOOTSTRAP_SERVERS,
    )
    return consumer


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
    restart_backoff = BackoffState(
        initial_delay=1.0,
        max_delay=15.0,
        factor=2.0,
        jitter=0.5,
    )

    while True:
        consumer = None

        try:
            consumer = create_consumer()
            restart_backoff.reset()
            logger.info("Waiting for fault messages.")

            for message in consumer:
                try:
                    fault_data = process_fault_message(
                        message.value,
                        on_fault_inserted,
                    )

                    if fault_data is None:
                        continue

                    logger.debug(
                        "Fault processed | substation=%s | fault_type=%s | offset=%s",
                        fault_data.get("substation"),
                        fault_data.get("fault_type"),
                        message.offset,
                    )

                except Exception:
                    logger.exception("Failed to process fault message.")

        except KeyboardInterrupt:
            logger.info("Fault consumer stopped by user.")
            break

        except Exception:
            delay = restart_backoff.next_delay()
            logger.exception(
                "Fault consumer crashed. Restarting in %.1f seconds.",
                delay,
            )
            time.sleep(delay)

        finally:
            if consumer is not None:
                try:
                    consumer.close()
                except Exception:
                    logger.warning("Failed to close fault consumer cleanly.")


if __name__ == "__main__":
    start_fault_consumer()