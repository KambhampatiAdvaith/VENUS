from typing import Tuple

import pandas as pd

from backend.api.database import get_engine


FEATURE_COLUMNS = [
    "voltage",
    "current",
    "temperature",
    "load",
    "frequency",
]

FAULT_LABELS = [
    "normal",
    "temperature_spike",
    "voltage_drop",
    "load_surge",
    "frequency_deviation",
]


def normalize_numeric_columns(dataframe: pd.DataFrame) -> pd.DataFrame:
    dataframe = dataframe.copy()

    for column in FEATURE_COLUMNS:
        dataframe[column] = pd.to_numeric(dataframe[column], errors="coerce")

    dataframe = dataframe.dropna(subset=FEATURE_COLUMNS)

    return dataframe


def generate_fault_label(row) -> str:
    temperature = row["temperature"]
    voltage = row["voltage"]
    load = row["load"]
    frequency = row["frequency"]

    if temperature >= 90:
        return "temperature_spike"

    if voltage <= 210:
        return "voltage_drop"

    if load >= 80:
        return "load_surge"

    if frequency < 49.5 or frequency > 50.5:
        return "frequency_deviation"

    return "normal"


def load_telemetry_data(limit: int = 5000) -> pd.DataFrame:
    engine = get_engine()

    query = f"""
        SELECT
            id,
            substation,
            voltage,
            current,
            temperature,
            load,
            frequency,
            timestamp
        FROM telemetry
        ORDER BY timestamp DESC
        LIMIT {limit}
    """

    dataframe = pd.read_sql(query, engine)
    dataframe = normalize_numeric_columns(dataframe)

    return dataframe


def prepare_training_dataset(limit: int = 5000) -> pd.DataFrame:
    dataframe = load_telemetry_data(limit=limit)

    if dataframe.empty:
        raise ValueError("No telemetry data found. Start simulator/consumers first.")

    dataframe["label"] = dataframe.apply(generate_fault_label, axis=1)

    dataframe = add_synthetic_boundary_examples_if_needed(dataframe)

    return dataframe


def add_synthetic_boundary_examples_if_needed(dataframe: pd.DataFrame) -> pd.DataFrame:
    existing_labels = set(dataframe["label"].unique())
    missing_labels = [label for label in FAULT_LABELS if label not in existing_labels]

    if not missing_labels:
        return dataframe

    synthetic_rows = []

    base_row = {
        "id": -1,
        "substation": "SYNTHETIC",
        "voltage": 230.0,
        "current": 15.0,
        "temperature": 65.0,
        "load": 55.0,
        "frequency": 50.0,
        "timestamp": pd.Timestamp.utcnow(),
        "label": "normal",
    }

    synthetic_examples = {
        "normal": {
            **base_row,
            "label": "normal",
        },
        "temperature_spike": {
            **base_row,
            "temperature": 96.0,
            "label": "temperature_spike",
        },
        "voltage_drop": {
            **base_row,
            "voltage": 198.0,
            "label": "voltage_drop",
        },
        "load_surge": {
            **base_row,
            "load": 92.0,
            "label": "load_surge",
        },
        "frequency_deviation": {
            **base_row,
            "frequency": 48.8,
            "label": "frequency_deviation",
        },
    }

    for label in missing_labels:
        synthetic_rows.append(synthetic_examples[label])

    synthetic_dataframe = pd.DataFrame(synthetic_rows)

    return pd.concat([dataframe, synthetic_dataframe], ignore_index=True)


def build_feature_matrix(dataframe: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
    dataframe = normalize_numeric_columns(dataframe)

    x_values = dataframe[FEATURE_COLUMNS]
    y_values = dataframe["label"]

    return x_values, y_values


def load_latest_telemetry_per_substation() -> pd.DataFrame:
    engine = get_engine()

    query = """
        SELECT DISTINCT ON (substation)
            id,
            substation,
            voltage,
            current,
            temperature,
            load,
            frequency,
            timestamp
        FROM telemetry
        ORDER BY substation, timestamp DESC
    """

    dataframe = pd.read_sql(query, engine)
    dataframe = normalize_numeric_columns(dataframe)

    return dataframe