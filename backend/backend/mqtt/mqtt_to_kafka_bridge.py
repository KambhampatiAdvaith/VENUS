import json
import os
import signal
import sys
import time

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

from backend.kafka.producer import VenusKafkaProducer


load_dotenv()


MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))

MQTT_TELEMETRY_TOPIC = os.getenv("MQTT_TELEMETRY_TOPIC", "venus/telemetry")
MQTT_FAULT_TOPIC = os.getenv("MQTT_FAULT_TOPIC", "venus/faults")

KAFKA_TELEMETRY_TOPIC = os.getenv("KAFKA_TELEMETRY_TOPIC", "venus.telemetry")
KAFKA_FAULT_TOPIC = os.getenv("KAFKA_FAULT_TOPIC", "venus.faults")


class MQTTToKafkaBridge:
    def __init__(self) -> None:
        self.kafka_producer = VenusKafkaProducer()

        self.client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id="venus-mqtt-to-kafka-bridge",
        )

        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect

    def on_connect(self, client, userdata, flags, reason_code, properties=None) -> None:
        if reason_code == 0:
            print(f"[MQTT] Connected to {MQTT_HOST}:{MQTT_PORT}")

            telemetry_subscription = f"{MQTT_TELEMETRY_TOPIC}/#"
            fault_subscription = f"{MQTT_FAULT_TOPIC}/#"

            client.subscribe(telemetry_subscription)
            client.subscribe(fault_subscription)

            print(f"[MQTT] Subscribed to {telemetry_subscription}")
            print(f"[MQTT] Subscribed to {fault_subscription}")

        else:
            print(f"[MQTT] Connection failed with reason code: {reason_code}")

    def on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties=None) -> None:
        print(f"[MQTT] Disconnected. Reason code: {reason_code}")

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
                print(f"[BRIDGE] Ignored unknown topic: {mqtt_topic}")
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

            print(f"[BRIDGE] MQTT {mqtt_topic} → Kafka {kafka_topic}")

        except json.JSONDecodeError:
            print(f"[ERROR] Invalid JSON received from MQTT topic {message.topic}")

        except Exception as error:
            print(f"[ERROR] Failed to process MQTT message: {error}")

    def start(self) -> None:
        while True:
            try:
                self.client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
                self.client.loop_forever()
            except Exception as error:
                print(f"[MQTT] Bridge connection error: {error}")
                print("[MQTT] Retrying in 3 seconds...")
                time.sleep(3)

    def stop(self) -> None:
        print("\n[BRIDGE] Shutting down MQTT to Kafka bridge...")
        self.client.disconnect()
        self.kafka_producer.close()


bridge = MQTTToKafkaBridge()


def shutdown_handler(signum, frame) -> None:
    bridge.stop()
    sys.exit(0)


signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)


if __name__ == "__main__":
    print("[V.E.N.U.S.] Starting MQTT to Kafka Bridge...")
    bridge.start()