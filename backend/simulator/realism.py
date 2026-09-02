import random
from datetime import datetime, timezone


SUBSTATION_IDS = tuple(str(i) for i in range(1, 21))


# Generate deterministic profiles for Substation 1..20
SUBSTATION_PROFILES = {}

for i in range(1, 21):
    sid = str(i)

    load_offset = ((i % 5) - 2) * 0.9
    voltage_offset = (((i * 7) % 11) - 5) * 0.1
    temperature_offset = ((i % 4) - 1) * 0.6
    current_offset = (((i * 3) % 7) - 3) * 0.2

    # Correlation between substations
    correlation_factor = [
        1.0,
        0.6,
        -0.7,
        0.3,
        -0.4,
    ][i % 5]

    SUBSTATION_PROFILES[sid] = {
        "load_offset": load_offset,
        "voltage_offset": voltage_offset,
        "temperature_offset": temperature_offset,
        "current_offset": current_offset,
        "correlation_factor": correlation_factor,
    }


SUBSTATION_ORDER = SUBSTATION_IDS


# ============================================================
# PHYSICAL MODEL
# ============================================================

VOLTAGE_CURVE_POINTS = (
    (40.0, 231.0),
    (60.0, 229.0),
    (80.0, 226.0),
    (95.0, 223.0),
)


def clamp(
    value: float,
    minimum: float,
    maximum: float,
) -> float:
    return max(minimum, min(maximum, value))


def interpolate_curve(
    x_value: float,
    points: tuple[tuple[float, float], ...],
) -> float:

    if x_value <= points[0][0]:
        return points[0][1]

    for (left_x, left_y), (right_x, right_y) in zip(
        points,
        points[1:],
    ):
        if x_value <= right_x:

            ratio = (
                (x_value - left_x)
                / (right_x - left_x)
            )

            return left_y + ratio * (right_y - left_y)

    return points[-1][1]


# ============================================================
# DAILY LOAD PROFILE
# ============================================================

def get_daily_load_factor(hour: float) -> float:

    # Night
    if hour < 5:
        return 0.72

    # Morning increase
    if hour < 9:
        return 0.72 + (
            (hour - 5) / 4
        ) * 0.26

    # Afternoon stable
    if hour < 16:
        return 0.98 + (
            (hour - 9) / 7
        ) * 0.03

    # Evening peak
    if hour < 20:
        return 1.04 + (
            (hour - 16) / 4
        ) * 0.11

    # Night decline
    if hour < 24:
        return 1.15 - (
            (hour - 20) / 4
        ) * 0.27

    return 0.88


# ============================================================
# ELECTRICAL RELATIONSHIPS
# ============================================================

def calculate_voltage(
    load: float,
    voltage_offset: float = 0.0,
    noise: float = 0.0,
) -> float:

    base_voltage = interpolate_curve(
        load,
        VOLTAGE_CURVE_POINTS,
    )

    return clamp(
        base_voltage
        + voltage_offset
        + noise,
        220.0,
        233.0,
    )


def calculate_temperature(
    load: float,
    baseline_offset: float = 0.0,
    noise: float = 0.0,
) -> float:

    base_temperature = (
        33.0
        + max(load - 35.0, 0.0) * 0.45
    )

    return clamp(
        base_temperature
        + baseline_offset
        + noise,
        32.0,
        58.0,
    )


def calculate_frequency(
    load: float,
    grid_bias: float = 0.0,
    noise: float = 0.0,
) -> float:

    base_frequency = (
        50.05
        - max(load - 45.0, 0.0) * 0.0032
    )

    return clamp(
        base_frequency
        + grid_bias
        + noise,
        49.8,
        50.2,
    )


def calculate_current(
    load: float,
    current_offset: float = 0.0,
    noise: float = 0.0,
) -> float:

    base_current = 14.5 + load * 0.27

    return clamp(
        base_current
        + current_offset
        + noise,
        20.0,
        40.0,
    )


# ============================================================
# TIME HANDLING
# ============================================================

def ensure_timestamp(
    timestamp: datetime | None = None,
) -> datetime:

    if timestamp is None:
        return datetime.now(timezone.utc)

    if timestamp.tzinfo is None:
        return timestamp.replace(
            tzinfo=timezone.utc
        )

    return timestamp.astimezone(timezone.utc)


# ============================================================
# GRID CONTEXT
# ============================================================

def build_grid_context(
    timestamp: datetime | None = None,
) -> dict[str, float]:

    current_time = ensure_timestamp(timestamp)

    hour = (
        current_time.hour
        + current_time.minute / 60
        + current_time.second / 3600
    )

    # Shared seed creates correlation between substations
    shared_seed = (
        int(current_time.timestamp())
        // 900
    )

    shared_rng = random.Random(shared_seed)

    return {
        "hour": hour,
        "daily_load_factor": get_daily_load_factor(hour),
        "regional_variation": shared_rng.uniform(
            -1.6,
            1.6,
        ),
        "transfer_signal": shared_rng.uniform(
            -3.2,
            3.2,
        ),
        "frequency_bias": shared_rng.uniform(
            -0.018,
            0.018,
        ),
        "temperature_bias": shared_rng.uniform(
            -0.35,
            0.35,
        ),
    }


# ============================================================
# SINGLE SUBSTATION TELEMETRY
# ============================================================

def build_substation_telemetry(
    substation: str,
    timestamp: datetime | None = None,
) -> dict[str, float | str]:

    substation = str(substation)

    if substation not in SUBSTATION_PROFILES:
        raise ValueError(
            f"Invalid substation '{substation}'. "
            f"Valid substations are 1..20."
        )

    current_time = ensure_timestamp(timestamp)

    context = build_grid_context(
        current_time
    )

    profile = SUBSTATION_PROFILES[
        substation
    ]

    noise_seed = (
        f"{substation}:"
        f"{int(current_time.timestamp()) // 15}"
    )

    noise_rng = random.Random(
        noise_seed
    )

    # --------------------------------------------------------
    # Load
    # --------------------------------------------------------

    load = (
        54.0
        * context["daily_load_factor"]
        + context["regional_variation"]
        + profile["load_offset"]
        + (
            context["transfer_signal"]
            * profile["correlation_factor"]
        )
        + noise_rng.uniform(
            -1.4,
            1.4,
        )
    )

    load = clamp(
        load,
        35.0,
        78.0,
    )

    # --------------------------------------------------------
    # Voltage
    # --------------------------------------------------------

    voltage = calculate_voltage(
        load,
        voltage_offset=profile[
            "voltage_offset"
        ],
        noise=noise_rng.uniform(
            -0.35,
            0.35,
        ),
    )

    # --------------------------------------------------------
    # Temperature
    # --------------------------------------------------------

    temperature = calculate_temperature(
        load,
        baseline_offset=(
            profile["temperature_offset"]
            + context["temperature_bias"]
        ),
        noise=noise_rng.uniform(
            -0.45,
            0.45,
        ),
    )

    # --------------------------------------------------------
    # Frequency
    # --------------------------------------------------------

    frequency = calculate_frequency(
        load,
        grid_bias=context[
            "frequency_bias"
        ],
        noise=noise_rng.uniform(
            -0.012,
            0.012,
        ),
    )

    # --------------------------------------------------------
    # Current
    # --------------------------------------------------------

    current = calculate_current(
        load,
        current_offset=profile[
            "current_offset"
        ],
        noise=noise_rng.uniform(
            -0.7,
            0.7,
        ),
    )

    return {
        "substation": substation,
        "voltage": round(voltage, 2),
        "current": round(current, 2),
        "temperature": round(temperature, 2),
        "load": round(load, 2),
        "frequency": round(frequency, 2),
    }


# ============================================================
# COMPLETE 20-NODE GRID
# ============================================================

def build_normal_grid_telemetry(
    timestamp: datetime | None = None,
) -> list[dict[str, float | str]]:

    current_time = ensure_timestamp(
        timestamp
    )

    return [
        build_substation_telemetry(
            substation,
            current_time,
        )
        for substation in SUBSTATION_ORDER
    ]


# ============================================================
# OVERLOAD SCENARIO
# ============================================================

def build_overload_grid_telemetry(
    source_node: str,
    timestamp: datetime | None = None,
) -> list[dict[str, float | str]]:

    source_node = str(source_node)

    if source_node not in SUBSTATION_IDS:
        raise ValueError(
            f"Invalid source node '{source_node}'. "
            f"Valid substations are 1..20."
        )

    current_time = ensure_timestamp(
        timestamp
    )

    readings = build_normal_grid_telemetry(
        current_time
    )

    # Choose next substation as support node
    idx = SUBSTATION_ORDER.index(
        source_node
    )

    support_node = SUBSTATION_ORDER[
        (idx + 1)
        % len(SUBSTATION_ORDER)
    ]

    for reading in readings:

        substation = str(
            reading["substation"]
        )

        # ----------------------------------------------------
        # OVERLOADED NODE
        # ----------------------------------------------------

        if substation == source_node:

            reading["load"] = round(
                clamp(
                    float(reading["load"])
                    + 26.0,
                    88.0,
                    98.0,
                ),
                2,
            )

            reading["current"] = round(
                clamp(
                    float(reading["current"])
                    + 18.0,
                    45.0,
                    56.0,
                ),
                2,
            )

            reading["temperature"] = round(
                clamp(
                    float(
                        reading["temperature"]
                    )
                    + 28.0,
                    72.0,
                    86.0,
                ),
                2,
            )

            reading["voltage"] = round(
                clamp(
                    float(
                        reading["voltage"]
                    )
                    - 17.0,
                    205.0,
                    216.0,
                ),
                2,
            )

            reading["frequency"] = round(
                clamp(
                    float(
                        reading["frequency"]
                    )
                    - 0.55,
                    49.2,
                    49.7,
                ),
                2,
            )

        # ----------------------------------------------------
        # SUPPORT NODE
        # ----------------------------------------------------

        elif substation == support_node:

            adjusted_load = clamp(
                float(reading["load"])
                + 7.5,
                48.0,
                72.0,
            )

            reading["load"] = round(
                adjusted_load,
                2,
            )

            reading["current"] = round(
                calculate_current(
                    adjusted_load,
                    current_offset=0.9,
                ),
                2,
            )

            reading["temperature"] = round(
                calculate_temperature(
                    adjusted_load,
                    baseline_offset=1.5,
                ),
                2,
            )

            reading["voltage"] = round(
                calculate_voltage(
                    adjusted_load,
                    voltage_offset=-0.3,
                ),
                2,
            )

            reading["frequency"] = round(
                calculate_frequency(
                    adjusted_load,
                    grid_bias=-0.03,
                ),
                2,
            )

        # ----------------------------------------------------
        # OTHER NODES
        # ----------------------------------------------------

        else:

            adjusted_load = clamp(
                float(reading["load"])
                - 9.0,
                30.0,
                58.0,
            )

            reading["load"] = round(
                adjusted_load,
                2,
            )

            reading["current"] = round(
                calculate_current(
                    adjusted_load,
                    current_offset=-0.4,
                ),
                2,
            )

            reading["temperature"] = round(
                calculate_temperature(
                    adjusted_load,
                    baseline_offset=-0.4,
                ),
                2,
            )

            reading["voltage"] = round(
                calculate_voltage(
                    adjusted_load,
                    voltage_offset=0.4,
                ),
                2,
            )

            reading["frequency"] = round(
                calculate_frequency(
                    adjusted_load,
                    grid_bias=0.02,
                ),
                2,
            )

    return readings
