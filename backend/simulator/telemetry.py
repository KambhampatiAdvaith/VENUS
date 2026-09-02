import random
from datetime import datetime, timezone

from simulator.realism import (
    SUBSTATION_IDS,
    build_substation_telemetry,
)


NORMAL_RANGES = {
    "voltage": (220, 240),
    "current": (25, 40),
    "temperature": (55, 75),
    "load": (40, 70),
    "frequency": (49.8, 50.2),
}


FAULT_TYPES = [
    "temperature_spike",
    "voltage_drop",
    "load_surge",
    "frequency_deviation",
]


def validate_substation(
    substation: str,
) -> str:

    substation = str(substation)

    if substation not in SUBSTATION_IDS:
        raise ValueError(
            f"Invalid substation '{substation}'. "
            "Expected Substation 1..20."
        )

    return substation


def generate_normal_telemetry(
    substation: str,
) -> dict:

    substation = validate_substation(
        substation
    )

    timestamp = datetime.now(
        timezone.utc
    )

    telemetry = build_substation_telemetry(
        substation,
        timestamp,
    )

    return {
        **telemetry,
        "timestamp": timestamp.isoformat(),
        "is_fault": False,
        "fault_type": None,
    }


def inject_fault(
    telemetry: dict,
    fault_probability: float = 0.15,
) -> dict:

    should_inject_fault = (
        random.random()
        < fault_probability
    )

    if not should_inject_fault:
        return telemetry

    fault_type = random.choice(
        FAULT_TYPES
    )

    telemetry["is_fault"] = True
    telemetry["fault_type"] = fault_type

    if fault_type == "temperature_spike":

        telemetry["temperature"] = round(
            random.uniform(
                95,
                120,
            ),
            2,
        )

    elif fault_type == "voltage_drop":

        telemetry["voltage"] = round(
            random.uniform(
                160,
                200,
            ),
            2,
        )

    elif fault_type == "load_surge":

        telemetry["load"] = round(
            random.uniform(
                85,
                105,
            ),
            2,
        )

        telemetry["current"] = round(
            random.uniform(
                45,
                65,
            ),
            2,
        )

    elif fault_type == "frequency_deviation":

        telemetry["frequency"] = round(
            random.choice(
                [
                    random.uniform(
                        47.5,
                        49.0,
                    ),
                    random.uniform(
                        51.0,
                        52.5,
                    ),
                ]
            ),
            2,
        )

    return telemetry


def generate_telemetry(
    substation: str,
    fault_probability: float = 0.15,
) -> dict:

    substation = validate_substation(
        substation
    )

    telemetry = generate_normal_telemetry(
        substation
    )

    return inject_fault(
        telemetry,
        fault_probability,
    )
