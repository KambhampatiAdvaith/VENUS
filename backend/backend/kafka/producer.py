import json
import os
import time

from dotenv import load_dotenv
from kafka import KafkaProducer


load_dotenv()


KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")


class VenusKafkaProducer:
    def __init__(self) -> None:
        self.producer = None
        self.connect()

    def connect(self) -> None:
        while True:
            try:
                self.producer = KafkaProducer(
                    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                    value_serializer=lambda value: json.dumps(value).encode("utf-8"),
                    key_serializer=lambda key: key.encode("utf-8") if key else None,
                    retries=5,
                    acks="all",
                )
                print(f"[KAFKA] Connected to {KAFKA_BOOTSTRAP_SERVERS}")
                break
            except Exception as error:
                print(f"[KAFKA] Connection failed: {error}")
                print("[KAFKA] Retrying in 3 seconds...")
                time.sleep(3)

    def publish(self, topic: str, message: dict, key: str | None = None) -> None:
        try:
            future = self.producer.send(topic, value=message, key=key)
            result = future.get(timeout=10)

            print(
                f"[KAFKA] Published to topic={result.topic}, "
                f"partition={result.partition}, offset={result.offset}"
            )

        except Exception as error:
            print(f"[KAFKA] Failed to publish to {topic}: {error}")

    def close(self) -> None:
        if self.producer:
            self.producer.flush()
            self.producer.close()
            print("[KAFKA] Producer closed")