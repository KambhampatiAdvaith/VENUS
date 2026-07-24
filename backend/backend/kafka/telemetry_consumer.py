import json
import os
import time
from datetime import UTC, datetime
from typing import Any, Callable

from dotenv import load_dotenv
from kafka import KafkaConsumer

from backend.database.writer import insert_telemetry
from backend.edge.edge_anomaly_detector import edge_detector
from backend.utils.logging import BackoffState, get_logger, retry_with_backoff


load_dotenv()


KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TELEMETRY_TOPIC = os.getenv("KAFKA_TELEMETRY_TOPIC", "venus.telemetry")

logger = get_logger("backend.kafka.telemetry_consumer")


def create_consumer() -> KafkaConsumer:
    consumer = retry_with_backoff(
        lambda: KafkaConsumer(
            KAFKA_TELEMETRY_TOPIC,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            group_id="venus-telemetry-db-writer",
            auto_offset_reset="latest",
            enable_auto_commit=True,
            value_deserializer=lambda value: json.loads(value.decode("utf-8")),

            # Prevent kafka-python-ng from trying broker-version auto-detection,
            # which can fail on Windows/Python 3.12 with:
            # UnrecognizedBrokerVersion / Invalid file descriptor.
            api_version=(3, 6, 0),
            request_timeout_ms=30000,
            session_timeout_ms=10000,
            heartbeat_interval_ms=3000,
            consumer_timeout_ms=1000,
        ),
        logger=logger,
        operation_name=f"Telemetry consumer connection to {KAFKA_TELEMETRY_TOPIC}",
        initial_delay=1.0,
        max_delay=15.0,
        factor=2.0,
        jitter=0.5,
    )
    logger.info(
        "Telemetry consumer connected to topic=%s on bootstrap_servers=%s",
        KAFKA_TELEMETRY_TOPIC,
        KAFKA_BOOTSTRAP_SERVERS,
    )
    return consumer


def normalize_telemetry_payload(data: dict[str, Any]) -> dict[str, Any]:
    """
    Ensures telemetry messages always contain edge-anomaly fields.

    Week 6 MQTT simulator messages should already contain these fields from
    simulator/mqtt_publisher.py. If an older/raw telemetry message arrives,
    this function runs the edge detector as a fallback so the database/API
    does not show null edge fields during demos.
    """
    normalized = dict(data)

    missing_edge_fields = (
        normalized.get("edge_anomaly_score") is None
        or normalized.get("edge_model") is None
        or normalized.get("edge_processed_at") is None
    )

    if missing_edge_fields:
        normalized = edge_detector.analyze(normalized)

    return {
        **normalized,
        "edge_anomaly": normalized.get("edge_anomaly", False),
        "edge_anomaly_score": normalized.get("edge_anomaly_score"),
        "edge_model": normalized.get("edge_model"),
        "edge_processed_at": normalized.get("edge_processed_at"),
    }


def process_telemetry_message(
    kafka_message: dict[str, Any],
    on_telemetry_inserted: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any] | None:
    kafka_received_at = datetime.now(UTC)

    data = kafka_message.get("data", kafka_message)
    data = normalize_telemetry_payload(data)
    data["kafka_received_at"] = kafka_received_at

    inserted = insert_telemetry(data)

    if inserted is not None and on_telemetry_inserted is not None:
        on_telemetry_inserted(inserted)

    return inserted


def start_telemetry_consumer(
    on_telemetry_inserted: Callable[[dict[str, Any]], None] | None = None,
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
            logger.info("Waiting for telemetry messages.")

            for message in consumer:
                try:
                    kafka_message = message.value

                    data = process_telemetry_message(
                        kafka_message,
                        on_telemetry_inserted,
                    )

                    if data is None:
                        continue

                    logger.debug(
                        "Telemetry processed | substation=%s | edge_anomaly=%s | edge_score=%s | offset=%s",
                        data.get("substation"),
                        data.get("edge_anomaly"),
                        data.get("edge_anomaly_score"),
                        message.offset,
                    )

                except Exception:
                    logger.exception("Failed to process telemetry message.")

        except KeyboardInterrupt:
            logger.info("Telemetry consumer stopped by user.")
            break

        except Exception:
            delay = restart_backoff.next_delay()
            logger.exception(
                "Telemetry consumer crashed. Restarting in %.1f seconds.",
                delay,
            )
            time.sleep(delay)

        finally:
            if consumer is not None:
                try:
                    consumer.close()
                except Exception:
                    logger.warning("Failed to close telemetry consumer cleanly.")


if __name__ == "__main__":
    start_telemetry_consumer()