import json
import os

from dotenv import load_dotenv
from kafka import KafkaProducer

from backend.utils.logging import get_logger, retry_with_backoff


load_dotenv()


KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

logger = get_logger("backend.kafka.producer")


class VenusKafkaProducer:
    def __init__(self) -> None:
        self.producer = None
        self.connect()

    def connect(self) -> None:
        self.producer = retry_with_backoff(
            lambda: KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda value: json.dumps(value).encode("utf-8"),
                key_serializer=lambda key: key.encode("utf-8") if key else None,
                retries=5,
                acks="all",
            ),
            logger=logger,
            operation_name="Kafka producer connection",
            initial_delay=1.0,
            max_delay=15.0,
            factor=2.0,
            jitter=0.5,
        )
        logger.info("Connected to Kafka bootstrap_servers=%s", KAFKA_BOOTSTRAP_SERVERS)

    def publish(self, topic: str, message: dict, key: str | None = None) -> None:
        try:
            if self.producer is None:
                self.connect()

            future = self.producer.send(topic, value=message, key=key)
            result = future.get(timeout=10)

            logger.debug(
                "Published to topic=%s partition=%s offset=%s",
                result.topic,
                result.partition,
                result.offset,
            )

        except Exception:
            logger.exception("Failed to publish message to topic=%s.", topic)
            self._reset_connection()

    def _reset_connection(self) -> None:
        if self.producer is not None:
            try:
                self.producer.close()
            except Exception:
                logger.warning("Failed to close Kafka producer during reconnect.")

        self.producer = None
        self.connect()

    def close(self) -> None:
        if self.producer:
            self.producer.flush()
            self.producer.close()
            logger.info("Producer closed.")