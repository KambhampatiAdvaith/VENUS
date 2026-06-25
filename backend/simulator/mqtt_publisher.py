import json
import os
import time
from typing import Any

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

from backend.edge.edge_anomaly_detector import edge_detector


load_dotenv()


class MQTTPublisher:
    def __init__(self, client_id: str | None = None):
        self.host = os.getenv("MQTT_HOST", "localhost")
        self.port = int(os.getenv("MQTT_PORT", "1883"))

        self.telemetry_topic_base = os.getenv(
            "MQTT_TELEMETRY_TOPIC",
            "venus/telemetry",
        )
        self.fault_topic_base = os.getenv(
            "MQTT_FAULT_TOPIC",
            "venus/faults",
        )

        self.connected = False

        self.client = mqtt.Client(
            client_id=client_id or f"venus-simulator-{os.getpid()}",
            protocol=mqtt.MQTTv311,
        )

        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect

        self.connect()

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            print(f"[MQTT] Connected to broker at {self.host}:{self.port}")
        else:
            self.connected = False
            print(f"[MQTT] Connection failed with code {rc}")

    def _on_disconnect(self, client, userdata, rc):
        self.connected = False
        if rc != 0:
            print("[MQTT] Unexpected disconnect. Will reconnect automatically.")

    def connect(self):
        try:
            self.client.reconnect_delay_set(min_delay=1, max_delay=10)
            self.client.connect(self.host, self.port, keepalive=60)
            self.client.loop_start()

            for _ in range(20):
                if self.connected:
                    return
                time.sleep(0.1)

        except Exception as error:
            self.connected = False
            print(f"[MQTT] Connection error: {error}")

    def ensure_connected(self) -> bool:
        if self.connected:
            return True

        try:
            print("[MQTT] Reconnecting...")
            self.client.reconnect()

            for _ in range(20):
                if self.connected:
                    return True
                time.sleep(0.1)

        except Exception as error:
            print(f"[MQTT] Reconnect failed: {error}")

        return self.connected

    def add_edge_anomaly_fields(self, telemetry: dict[str, Any]) -> dict[str, Any]:
        return edge_detector.analyze(telemetry)

    def _resolve_substation_and_payload(
        self,
        substation_or_telemetry: str | dict[str, Any],
        telemetry: dict[str, Any] | None = None,
    ) -> tuple[str, dict[str, Any]]:
        if telemetry is None:
            payload = substation_or_telemetry

            if not isinstance(payload, dict):
                raise ValueError("Telemetry payload must be a dictionary.")

            substation = str(payload.get("substation", "unknown"))
            return substation, payload

        substation = str(substation_or_telemetry)
        return substation, telemetry

    def publish_telemetry(
        self,
        substation_or_telemetry: str | dict[str, Any],
        telemetry: dict[str, Any] | None = None,
    ) -> bool:
        substation, telemetry_payload = self._resolve_substation_and_payload(
            substation_or_telemetry,
            telemetry,
        )

        telemetry_payload = self.add_edge_anomaly_fields(telemetry_payload)

        topic = f"{self.telemetry_topic_base}/{substation}"
        payload = json.dumps(telemetry_payload)

        if not self.ensure_connected():
            print(f"[MQTT] Failed to publish telemetry to {topic}: not connected")
            return False

        try:
            result = self.client.publish(topic, payload, qos=1)
            result.wait_for_publish(timeout=5)

            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(f"[MQTT] Published telemetry to {topic}: {payload}")
                return True

            print(
                f"[MQTT] Failed to publish telemetry to {topic}: "
                f"mqtt_rc={result.rc}"
            )
            return False

        except Exception as error:
            print(f"[MQTT] Failed to publish telemetry to {topic}: {error}")
            self.connected = False
            return False

    def publish_fault(
        self,
        substation_or_fault: str | dict[str, Any],
        fault: dict[str, Any] | None = None,
    ) -> bool:
        if fault is None:
            fault_payload = substation_or_fault

            if not isinstance(fault_payload, dict):
                raise ValueError("Fault payload must be a dictionary.")

            substation = str(fault_payload.get("substation", "unknown"))
        else:
            substation = str(substation_or_fault)
            fault_payload = fault

        if "telemetry" in fault_payload and isinstance(fault_payload["telemetry"], dict):
            fault_payload["telemetry"] = self.add_edge_anomaly_fields(
                fault_payload["telemetry"]
            )

        topic = f"{self.fault_topic_base}/{substation}"
        payload = json.dumps(fault_payload)

        if not self.ensure_connected():
            print(f"[MQTT] Failed to publish fault to {topic}: not connected")
            return False

        try:
            result = self.client.publish(topic, payload, qos=1)
            result.wait_for_publish(timeout=5)

            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(f"[MQTT] Published fault to {topic}: {payload}")
                return True

            print(
                f"[MQTT] Failed to publish fault to {topic}: "
                f"mqtt_rc={result.rc}"
            )
            return False

        except Exception as error:
            print(f"[MQTT] Failed to publish fault to {topic}: {error}")
            self.connected = False
            return False

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()
        self.connected = False