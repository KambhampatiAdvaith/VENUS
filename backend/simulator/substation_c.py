import time

from simulator.mqtt_publisher import MQTTPublisher
from simulator.telemetry import generate_telemetry


SUBSTATION_ID = "C"


def main() -> None:
    publisher = MQTTPublisher(client_id="substation-c-simulator")
    publisher.connect()

    print(f"[SIMULATOR] Substation {SUBSTATION_ID} started")

    try:
        while True:
            telemetry = generate_telemetry(SUBSTATION_ID)

            publisher.publish_telemetry(telemetry)

            if telemetry["is_fault"]:
                publisher.publish_fault(telemetry)

            time.sleep(1)

    except KeyboardInterrupt:
        print(f"\n[SIMULATOR] Substation {SUBSTATION_ID} stopped")
        publisher.disconnect()


if __name__ == "__main__":
    main()