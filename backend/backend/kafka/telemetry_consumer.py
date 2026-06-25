import json
import os
import time
from typing import Any

from dotenv import load_dotenv
from kafka import KafkaConsumer

from backend.database.writer import insert_telemetry
from backend.edge.edge_anomaly_detector import edge_detector


load_dotenv()


KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TELEMETRY_TOPIC = os.getenv("KAFKA_TELEMETRY_TOPIC", "venus.telemetry")


def create_consumer() -> KafkaConsumer:
    while True:
        try:
            consumer = KafkaConsumer(
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
            )

            print(f"[KAFKA] Telemetry consumer connected to {KAFKA_TELEMETRY_TOPIC}")
            return consumer

        except Exception as error:
            print(f"[KAFKA] Telemetry consumer connection failed: {error}")
            print("[KAFKA] Retrying in 3 seconds...")
            time.sleep(3)


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


def start_telemetry_consumer() -> None:
    while True:
        consumer = None

        try:
            consumer = create_consumer()

            print("[CONSUMER] Waiting for telemetry messages...")

            for message in consumer:
                try:
                    kafka_message = message.value

                    data = kafka_message.get("data", kafka_message)
                    data = normalize_telemetry_payload(data)

                    insert_telemetry(data)

                    print(
                        f"[CONSUMER] Telemetry processed | "
                        f"substation={data.get('substation')} | "
                        f"edge_anomaly={data.get('edge_anomaly')} | "
                        f"edge_score={data.get('edge_anomaly_score')} | "
                        f"offset={message.offset}"
                    )

                except Exception as error:
                    print(f"[CONSUMER] Failed to process telemetry message: {error}")

        except KeyboardInterrupt:
            print("[KAFKA] Telemetry consumer stopped by user.")
            break

        except Exception as error:
            print(f"[KAFKA] Telemetry consumer crashed: {error}")
            print("[KAFKA] Restarting consumer in 3 seconds...")
            time.sleep(3)

        finally:
            if consumer is not None:
                try:
                    consumer.close()
                except Exception:
                    pass


if __name__ == "__main__":
    start_telemetry_consumer()