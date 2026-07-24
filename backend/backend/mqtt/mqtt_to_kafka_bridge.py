import json
import os
import signal
import sys
import time

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

from backend.kafka.producer import VenusKafkaProducer
from backend.utils.logging import BackoffState, get_logger


load_dotenv()


MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))

MQTT_TELEMETRY_TOPIC = os.getenv("MQTT_TELEMETRY_TOPIC", "venus/telemetry")
MQTT_FAULT_TOPIC = os.getenv("MQTT_FAULT_TOPIC", "venus/faults")

KAFKA_TELEMETRY_TOPIC = os.getenv("KAFKA_TELEMETRY_TOPIC", "venus.telemetry")
KAFKA_FAULT_TOPIC = os.getenv("KAFKA_FAULT_TOPIC", "venus.faults")

logger = get_logger("backend.mqtt.bridge")


class MQTTToKafkaBridge:
    def __init__(self) -> None:
        self.kafka_producer = VenusKafkaProducer()
        self._stopping = False
        self._reconnect_backoff = BackoffState(
            initial_delay=1.0,
            max_delay=15.0,
            factor=2.0,
            jitter=0.5,
        )

        self.client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id="venus-mqtt-to-kafka-bridge",
        )

        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect

    def on_connect(self, client, userdata, flags, reason_code, properties=None) -> None:
        if reason_code == 0:
            self._reconnect_backoff.reset()
            logger.info("Connected to MQTT broker %s:%s", MQTT_HOST, MQTT_PORT)

            telemetry_subscription = f"{MQTT_TELEMETRY_TOPIC}/#"
            fault_subscription = f"{MQTT_FAULT_TOPIC}/#"

            client.subscribe(telemetry_subscription)
            client.subscribe(fault_subscription)

            logger.info("Subscribed to %s", telemetry_subscription)
            logger.info("Subscribed to %s", fault_subscription)

        else:
            logger.warning("MQTT connection failed with reason_code=%s", reason_code)

    def on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties=None) -> None:
        if self._stopping:
            logger.info("Disconnected from MQTT broker.")
            return

        logger.warning("Disconnected from MQTT broker with reason_code=%s", reason_code)

    def on_message(self, client, userdata, message) -> None:
        try:
            mqtt_topic = message.topic
            payload = message.payload.decode("utf-8")
            data = json.loads(payload)

            substation = data.get("substation", "unknown")

            if mqtt_topic.startswith(MQTT_TELEMETRY_TOPIC):
                kafka_topic = KAFKA_TELEMETRY_TOPIC
                event_type = "telemetry"

            elif mqtt_topic.startswith(MQTT_FAULT_TOPIC):
                kafka_topic = KAFKA_FAULT_TOPIC
                event_type = "fault"

            else:
                logger.warning("Ignored unknown MQTT topic=%s", mqtt_topic)
                return

            enriched_message = {
                "event_type": event_type,
                "source": "mqtt",
                "mqtt_topic": mqtt_topic,
                "data": data,
            }

            self.kafka_producer.publish(
                topic=kafka_topic,
                message=enriched_message,
                key=substation,
            )

            logger.debug("Bridged MQTT topic=%s to Kafka topic=%s", mqtt_topic, kafka_topic)

        except json.JSONDecodeError:
            logger.warning("Invalid JSON received from MQTT topic=%s", message.topic)

        except Exception:
            logger.exception("Failed to process MQTT message from topic=%s.", message.topic)

    def start(self) -> None:
        while True:
            try:
                logger.info("Connecting MQTT bridge to %s:%s", MQTT_HOST, MQTT_PORT)
                self.client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
                self.client.loop_forever()

                if self._stopping:
                    break

                delay = self._reconnect_backoff.next_delay()
                logger.warning(
                    "MQTT loop ended unexpectedly. Reconnecting in %.1f seconds.",
                    delay,
                )
                time.sleep(delay)
            except Exception:
                if self._stopping:
                    break

                delay = self._reconnect_backoff.next_delay()
                logger.exception(
                    "MQTT bridge connection error. Retrying in %.1f seconds.",
                    delay,
                )
                time.sleep(delay)

    def stop(self) -> None:
        self._stopping = True
        logger.info("Shutting down MQTT to Kafka bridge.")
        self.client.disconnect()
        self.kafka_producer.close()


bridge = MQTTToKafkaBridge()


def shutdown_handler(signum, frame) -> None:
    bridge.stop()
    sys.exit(0)


signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)


if __name__ == "__main__":
    logger.info("Starting MQTT to Kafka bridge.")
    bridge.start()