import os
import time

from simulator.mqtt_publisher import MQTTPublisher
from simulator.telemetry import generate_telemetry


def main() -> None:

    substation_id = os.getenv(
        "SUBSTATION_ID"
    )

    if not substation_id:
        raise RuntimeError(
            "SUBSTATION_ID environment variable "
            "must be set."
        )

    substation_id = str(
        substation_id
    )

    if not substation_id.isdigit():

        raise ValueError(
            "SUBSTATION_ID must be "
            "a number between 1 and 20."
        )

    numeric_id = int(
        substation_id
    )

    if numeric_id < 1 or numeric_id > 20:

        raise ValueError(
            "SUBSTATION_ID must be "
            "between 1 and 20."
        )

    publisher = MQTTPublisher(
        client_id=(
            f"substation-{substation_id}-simulator"
        )
    )

    publisher.connect()

    print(
        f"[SIMULATOR] "
        f"Substation {substation_id} started"
    )

    try:

        while True:

            telemetry = generate_telemetry(
                substation_id
            )

            publisher.publish_telemetry(
                telemetry
            )

            if telemetry["is_fault"]:

                publisher.publish_fault(
                    telemetry
                )

            time.sleep(
                float(
                    os.getenv(
                        "SIMULATOR_INTERVAL",
                        "1",
                    )
                )
            )

    except KeyboardInterrupt:

        print(
            f"\n[SIMULATOR] "
            f"Substation {substation_id} stopped"
        )

    finally:

        publisher.disconnect()


if __name__ == "__main__":
    main()
