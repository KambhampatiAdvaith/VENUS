import random
from datetime import datetime, timezone


# Generate 20 nodes named "Node 01" .. "Node 20" with small deterministic
# offsets so telemetry remains varied and deterministic enough for tests.
SUBSTATION_PROFILES = {}
for i in range(1, 21):
    sid = f"Node {str(i).zfill(2)}"  # Node 01 .. Node 20
    # Deterministic offsets for variety
    load_offset = ((i % 5) - 2) * 0.8
    voltage_offset = (((i * 7) % 11) - 5) * 0.08
    temperature_offset = ((i % 4) - 1) * 0.5
    current_offset = (((i * 3) % 7) - 3) * 0.18
    corr = [1.0, 0.6, -0.5, 0.3, -0.4][i % 5]

    SUBSTATION_PROFILES[sid] = {
        "load_offset": load_offset,
        "voltage_offset": voltage_offset,
        "temperature_offset": temperature_offset,
        "current_offset": current_offset,
        "correlation_factor": corr,
    }

SUBSTATION_ORDER = tuple(SUBSTATION_PROFILES.keys())

VOLTAGE_CURVE_POINTS = (
    (40.0, 231.0),
    (60.0, 229.0),
    (80.0, 226.0),
    (95.0, 223.0),
)


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def interpolate_curve(x_value: float, points: tuple[tuple[float, float], ...]) -> float:
    if x_value <= points[0][0]:
        return points[0][1]

    for (left_x, left_y), (right_x, right_y) in zip(points, points[1:]):
        if x_value <= right_x:
            ratio = (x_value - left_x) / (right_x - left_x)
            return left_y + ratio * (right_y - left_y)

    return points[-1][1]


def get_daily_load_factor(hour: float) -> float:
    if hour < 5:
        return 0.72

    if hour < 9:
        return 0.72 + ((hour - 5) / 4) * 0.26

    if hour < 16:
        return 0.98 + ((hour - 9) / 7) * 0.03

    if hour < 20:
        return 1.04 + ((hour - 16) / 4) * 0.11

    if hour < 24:
        return 1.15 - ((hour - 20) / 4) * 0.27

    return 0.88


def calculate_voltage(load: float, voltage_offset: float = 0.0, noise: float = 0.0) -> float:
    base_voltage = interpolate_curve(load, VOLTAGE_CURVE_POINTS)
    # Normal range centered ~229-231; allow noise and offsets
    return clamp(base_voltage + voltage_offset + noise, 210.0, 236.0)


def calculate_temperature(
    load: float,
    baseline_offset: float = 0.0,
    noise: float = 0.0,
) -> float:
    base_temperature = 33.0 + max(load - 35.0, 0.0) * 0.45
    return clamp(base_temperature + baseline_offset + noise, 32.0, 80.0)


def calculate_frequency(load: float, grid_bias: float = 0.0, noise: float = 0.0) -> float:
    base_frequency = 50.05 - max(load - 45.0, 0.0) * 0.0032
    return clamp(base_frequency + grid_bias + noise, 47.0, 51.0)


def calculate_current(load: float, current_offset: float = 0.0, noise: float = 0.0) -> float:
    base_current = 14.5 + load * 0.27
    return clamp(base_current + current_offset + noise, 10.0, 80.0)


def ensure_timestamp(timestamp: datetime | None = None) -> datetime:
    if timestamp is None:
        return datetime.now(timezone.utc)

    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=timezone.utc)

    return timestamp.astimezone(timezone.utc)


def build_grid_context(timestamp: datetime | None = None) -> dict[str, float]:
    current_time = ensure_timestamp(timestamp)
    hour = current_time.hour + (current_time.minute / 60) + (current_time.second / 3600)
    shared_seed = int(current_time.timestamp()) // 900
    shared_rng = random.Random(shared_seed)

    return {
        "hour": hour,
        "daily_load_factor": get_daily_load_factor(hour),
        "regional_variation": shared_rng.uniform(-1.6, 1.6),
        "transfer_signal": shared_rng.uniform(-3.2, 3.2),
        "frequency_bias": shared_rng.uniform(-0.018, 0.018),
        "temperature_bias": shared_rng.uniform(-0.35, 0.35),
    }


def build_substation_telemetry(
    substation: str,
    timestamp: datetime | None = None,
) -> dict[str, float | str]:
    current_time = ensure_timestamp(timestamp)
    context = build_grid_context(current_time)
    profile = SUBSTATION_PROFILES[substation]
    noise_seed = f"{substation}:{int(current_time.timestamp()) // 15}"
    noise_rng = random.Random(noise_seed)

    load = (
        54.0 * context["daily_load_factor"]
        + context["regional_variation"]
        + profile["load_offset"]
        + (context["transfer_signal"] * profile["correlation_factor"])
        + noise_rng.uniform(-1.4, 1.4)
    )
    load = clamp(load, 35.0, 78.0)

    voltage = calculate_voltage(
        load,
        voltage_offset=profile["voltage_offset"],
        noise=noise_rng.uniform(-0.35, 0.35),
    )
    temperature = calculate_temperature(
        load,
        baseline_offset=profile["temperature_offset"] + context["temperature_bias"],
        noise=noise_rng.uniform(-0.45, 0.45),
    )
    frequency = calculate_frequency(
        load,
        grid_bias=context["frequency_bias"],
        noise=noise_rng.uniform(-0.012, 0.012),
    )
    current = calculate_current(
        load,
        current_offset=profile["current_offset"],
        noise=noise_rng.uniform(-0.7, 0.7),
    )

    return {
        "substation": substation,
        "voltage": round(voltage, 2),
        "current": round(current, 2),
        "temperature": round(temperature, 2),
        "load": round(load, 2),
        "frequency": round(frequency, 2),
    }


def build_normal_grid_telemetry(timestamp: datetime | None = None) -> list[dict[str, float | str]]:
    """
    Build normal telemetry for all substations. Inject occasional faults for
    Node 01 and Node 02 (~12% probability) and rare anomalies for Node 03..20
    (~2% probability).
    """
    current_time = ensure_timestamp(timestamp)
    readings = [
        build_substation_telemetry(substation, current_time)
        for substation in SUBSTATION_ORDER
    ]

    # Apply probabilistic faults/anomalies using a stable RNG per cycle
    cycle_rng = random.Random(int(current_time.timestamp()) // 15)

    def inject_heavy_fault(reading: dict[str, float | str], rng: random.Random) -> None:
        # Heavy fault ranges per spec
        reading["load"] = round(rng.uniform(85.0, 92.0), 2)
        reading["voltage"] = round(rng.uniform(210.0, 215.0), 2)
        reading["temperature"] = round(rng.uniform(70.0, 75.0), 2)
        reading["frequency"] = round(rng.uniform(49.3, 49.5), 2)
        reading["current"] = round(calculate_current(float(reading["load"])), 2)

    def inject_minor_anomaly(reading: dict[str, float | str], rng: random.Random) -> None:
        # Small deviations but keep within mostly normal bounds
        choice = rng.choice(["load", "voltage", "temperature", "frequency"])
        if choice == "load":
            reading["load"] = round(clamp(float(reading["load"]) + rng.uniform(5.0, 12.0), 35.0, 90.0), 2)
            reading["current"] = round(calculate_current(float(reading["load"])), 2)
        elif choice == "voltage":
            reading["voltage"] = round(clamp(float(reading["voltage"]) + rng.uniform(-6.0, 6.0), 220.0, 236.0), 2)
        elif choice == "temperature":
            reading["temperature"] = round(clamp(float(reading["temperature"]) + rng.uniform(6.0, 12.0), 32.0, 80.0), 2)
        else:
            reading["frequency"] = round(clamp(float(reading["frequency"]) + rng.uniform(-0.4, 0.4), 47.0, 51.0), 2)

    for reading in readings:
        sub = str(reading["substation"])
        node_rng = random.Random(f"{sub}:{int(current_time.timestamp()) // 15}")
        if sub in ("Node 01", "Node 02"):
            if node_rng.random() < 0.12:
                inject_heavy_fault(reading, node_rng)
        else:
            if node_rng.random() < 0.02:
                inject_minor_anomaly(reading, node_rng)

    return readings


def build_overload_grid_telemetry(
    source_node: str,
    timestamp: datetime | None = None,
) -> list[dict[str, float | str]]:
    current_time = ensure_timestamp(timestamp)
    readings = build_normal_grid_telemetry(current_time)

    # Support node selection: pick the next node in SUBSTATION_ORDER (wrap-around).
    try:
        idx = SUBSTATION_ORDER.index(source_node)
        support_node = SUBSTATION_ORDER[(idx + 1) % len(SUBSTATION_ORDER)]
    except ValueError:
        # fallback to first node if source_node not found
        support_node = SUBSTATION_ORDER[0]

    for reading in readings:
        substation = str(reading["substation"])

        if substation == source_node:
            reading["load"] = round(clamp(float(reading["load"]) + 26.0, 88.0, 98.0), 2)
            reading["current"] = round(clamp(float(reading["current"]) + 18.0, 45.0, 56.0), 2)
            reading["temperature"] = round(clamp(float(reading["temperature"]) + 28.0, 72.0, 86.0), 2)
            reading["voltage"] = round(clamp(float(reading["voltage"]) - 17.0, 205.0, 216.0), 2)
            reading["frequency"] = round(clamp(float(reading["frequency"]) - 0.55, 49.2, 49.7), 2)
        elif substation == support_node:
            adjusted_load = clamp(float(reading["load"]) + 7.5, 48.0, 72.0)
            reading["load"] = round(adjusted_load, 2)
            reading["current"] = round(calculate_current(adjusted_load, current_offset=0.9), 2)
            reading["temperature"] = round(calculate_temperature(adjusted_load, baseline_offset=1.5), 2)
            reading["voltage"] = round(calculate_voltage(adjusted_load, voltage_offset=-0.3), 2)
            reading["frequency"] = round(calculate_frequency(adjusted_load, grid_bias=-0.03), 2)
        else:
            adjusted_load = clamp(float(reading["load"]) - 9.0, 30.0, 58.0)
            reading["load"] = round(adjusted_load, 2)
            reading["current"] = round(calculate_current(adjusted_load, current_offset=-0.4), 2)
            reading["temperature"] = round(calculate_temperature(adjusted_load, baseline_offset=-0.4), 2)
            reading["voltage"] = round(calculate_voltage(adjusted_load, voltage_offset=0.4), 2)
            reading["frequency"] = round(calculate_frequency(adjusted_load, grid_bias=0.02), 2)

    return readings
