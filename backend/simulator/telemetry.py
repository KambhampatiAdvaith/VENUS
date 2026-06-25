import random
from datetime import datetime, timezone


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


def generate_normal_telemetry(substation: str) -> dict:
    """
    Generate normal telemetry for one substation.
    """

    return {
        "substation": substation,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "voltage": round(random.uniform(*NORMAL_RANGES["voltage"]), 2),
        "current": round(random.uniform(*NORMAL_RANGES["current"]), 2),
        "temperature": round(random.uniform(*NORMAL_RANGES["temperature"]), 2),
        "load": round(random.uniform(*NORMAL_RANGES["load"]), 2),
        "frequency": round(random.uniform(*NORMAL_RANGES["frequency"]), 2),
        "is_fault": False,
        "fault_type": None,
    }


def inject_fault(telemetry: dict, fault_probability: float = 0.15) -> dict:
    """
    Randomly inject a fault into telemetry.

    Fault probability of 0.15 means there is a 15% chance
    that any generated telemetry message contains a fault.
    """

    should_inject_fault = random.random() < fault_probability

    if not should_inject_fault:
        return telemetry

    fault_type = random.choice(FAULT_TYPES)

    telemetry["is_fault"] = True
    telemetry["fault_type"] = fault_type

    if fault_type == "temperature_spike":
        telemetry["temperature"] = round(random.uniform(95, 120), 2)

    elif fault_type == "voltage_drop":
        telemetry["voltage"] = round(random.uniform(160, 200), 2)

    elif fault_type == "load_surge":
        telemetry["load"] = round(random.uniform(85, 105), 2)
        telemetry["current"] = round(random.uniform(45, 65), 2)

    elif fault_type == "frequency_deviation":
        telemetry["frequency"] = round(random.choice([
            random.uniform(47.5, 49.0),
            random.uniform(51.0, 52.5),
        ]), 2)

    return telemetry


def generate_telemetry(substation: str, fault_probability: float = 0.15) -> dict:
    telemetry = generate_normal_telemetry(substation)
    telemetry = inject_fault(telemetry, fault_probability)
    return telemetry