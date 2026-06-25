from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text

from backend.api.database import get_engine


OVERLOAD_THRESHOLD = 85.0
TARGET_MAX_LOAD = 70.0
DESIRED_SOURCE_LOAD = 75.0
MAX_LOAD_SHIFT = 15.0
MIN_LOAD_SHIFT = 5.0


def normalize_node_name(node: str) -> str:
    if not node:
        return "unknown"

    return str(node).replace("Substation", "").strip()


def calculate_risk_score(load: float, temperature: float | None = None) -> float:
    """
    Simple Week 5 risk formula.

    Load has highest importance because this engine is focused on
    autonomous load balancing.

    Returns value between 0.0 and 1.0.
    """
    load_score = min(max(load / 100.0, 0.0), 1.0)

    temperature_score = 0.0
    if temperature is not None:
        temperature_score = min(max((temperature - 25.0) / 75.0, 0.0), 1.0)

    risk_score = (0.75 * load_score) + (0.25 * temperature_score)

    return round(risk_score, 4)


def get_latest_node_states() -> list[dict[str, Any]]:
    """
    Reads the latest telemetry record for each substation.
    """
    engine = get_engine()

    query = """
        SELECT DISTINCT ON (substation)
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

    with engine.begin() as connection:
        rows = connection.execute(text(query)).mappings().all()

    nodes = []
    for row in rows:
        node = dict(row)
        node["substation"] = normalize_node_name(node["substation"])
        nodes.append(node)

    return nodes


def get_latest_prediction_risk_by_node() -> dict[str, dict[str, Any]]:
    """
    Reads latest AI prediction per substation.

    This helps the balancer avoid sending load to a node that is already
    predicted as risky.
    """
    engine = get_engine()

    query = """
        SELECT DISTINCT ON (substation)
            substation,
            predicted_fault,
            probability,
            anomaly,
            anomaly_score,
            timestamp
        FROM predictions
        ORDER BY substation, timestamp DESC
    """

    try:
        with engine.begin() as connection:
            rows = connection.execute(text(query)).mappings().all()
    except Exception:
        return {}

    prediction_map = {}

    for row in rows:
        item = dict(row)
        node = normalize_node_name(item["substation"])
        prediction_map[node] = item

    return prediction_map


def is_node_safe_target(
    node: dict[str, Any],
    prediction_map: dict[str, dict[str, Any]],
) -> bool:
    node_name = normalize_node_name(node["substation"])
    load = float(node["load"])

    if load > TARGET_MAX_LOAD:
        return False

    prediction = prediction_map.get(node_name)

    if not prediction:
        return True

    predicted_fault = prediction.get("predicted_fault")
    anomaly = bool(prediction.get("anomaly"))
    probability = float(prediction.get("probability") or 0)

    if anomaly:
        return False

    if predicted_fault and predicted_fault != "normal" and probability >= 0.5:
        return False

    return True


def find_overloaded_source(nodes: list[dict[str, Any]]) -> dict[str, Any] | None:
    overloaded_nodes = [
        node for node in nodes if float(node["load"]) >= OVERLOAD_THRESHOLD
    ]

    if not overloaded_nodes:
        return None

    return max(overloaded_nodes, key=lambda node: float(node["load"]))


def find_highest_load_source(nodes: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not nodes:
        return None

    return max(nodes, key=lambda node: float(node["load"]))


def find_best_target(
    nodes: list[dict[str, Any]],
    source_node: str,
    prediction_map: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    candidates = []

    for node in nodes:
        node_name = normalize_node_name(node["substation"])

        if node_name == source_node:
            continue

        if is_node_safe_target(node, prediction_map):
            candidates.append(node)

    if not candidates:
        return None

    return min(candidates, key=lambda node: float(node["load"]))


def find_lowest_load_target(
    nodes: list[dict[str, Any]],
    source_node: str,
) -> dict[str, Any] | None:
    candidates = [
        node
        for node in nodes
        if normalize_node_name(node["substation"]) != source_node
    ]

    if not candidates:
        return None

    return min(candidates, key=lambda node: float(node["load"]))


def calculate_load_shift(
    source_load: float,
    target_load: float,
) -> float:
    source_excess = source_load - DESIRED_SOURCE_LOAD
    target_capacity = TARGET_MAX_LOAD - target_load

    shift = min(
        MAX_LOAD_SHIFT,
        source_excess,
        target_capacity,
    )

    if shift < MIN_LOAD_SHIFT:
        return 0.0

    return round(shift, 2)


def calculate_recommendation_shift(
    source_load: float,
    target_load: float,
) -> float:
    load_gap = source_load - target_load
    target_capacity = max(TARGET_MAX_LOAD - target_load, 0.0)

    if load_gap <= 0 or target_capacity <= 0:
        return 0.0

    shift = min(MAX_LOAD_SHIFT, load_gap / 2, target_capacity)

    return round(max(shift, 0.0), 2)


def serialize_action(action: dict[str, Any]) -> dict[str, Any]:
    if isinstance(action.get("created_at"), datetime):
        action["created_at"] = action["created_at"].isoformat()

    return action


def store_balancing_action(
    source_node: str,
    target_node: str,
    load_shifted: float,
    trigger_reason: str,
    action_status: str,
    source_load_before: float,
    source_load_after: float,
    target_load_before: float,
    target_load_after: float,
    risk_before: float,
    risk_after: float,
    effectiveness: str,
    execution_mode: str,
    decision_notes: str,
) -> dict[str, Any]:
    engine = get_engine()

    query = """
        INSERT INTO load_balancing_actions (
            source_node,
            target_node,
            load_shifted,
            trigger_reason,
            action_status,
            source_load_before,
            source_load_after,
            target_load_before,
            target_load_after,
            risk_before,
            risk_after,
            effectiveness,
            execution_mode,
            decision_notes,
            created_at
        )
        VALUES (
            :source_node,
            :target_node,
            :load_shifted,
            :trigger_reason,
            :action_status,
            :source_load_before,
            :source_load_after,
            :target_load_before,
            :target_load_after,
            :risk_before,
            :risk_after,
            :effectiveness,
            :execution_mode,
            :decision_notes,
            :created_at
        )
        RETURNING
            id,
            source_node,
            target_node,
            load_shifted,
            trigger_reason,
            action_status,
            source_load_before,
            source_load_after,
            target_load_before,
            target_load_after,
            risk_before,
            risk_after,
            effectiveness,
            execution_mode,
            decision_notes,
            created_at
    """

    params = {
        "source_node": source_node,
        "target_node": target_node,
        "load_shifted": load_shifted,
        "trigger_reason": trigger_reason,
        "action_status": action_status,
        "source_load_before": source_load_before,
        "source_load_after": source_load_after,
        "target_load_before": target_load_before,
        "target_load_after": target_load_after,
        "risk_before": risk_before,
        "risk_after": risk_after,
        "effectiveness": effectiveness,
        "execution_mode": execution_mode,
        "decision_notes": decision_notes,
        "created_at": datetime.now(UTC),
    }

    with engine.begin() as connection:
        row = connection.execute(text(query), params).mappings().first()

    return serialize_action(dict(row))


def create_pending_recommendation() -> dict[str, Any]:
    nodes = get_latest_node_states()

    if len(nodes) < 2:
        return {
            "status": "no_action",
            "message": "At least two telemetry records are required to create a recommendation.",
            "action": None,
        }

    source = find_highest_load_source(nodes)

    if not source:
        return {
            "status": "no_action",
            "message": "No telemetry records available.",
            "action": None,
        }

    source_node = normalize_node_name(source["substation"])
    target = find_lowest_load_target(nodes, source_node)

    if not target:
        return {
            "status": "no_action",
            "message": "No target node was available for a recommendation.",
            "action": None,
        }

    source_load_before = float(source["load"])
    target_load_before = float(target["load"])
    load_shifted = calculate_recommendation_shift(
        source_load=source_load_before,
        target_load=target_load_before,
    )

    if load_shifted <= 0:
        return {
            "status": "no_action",
            "message": "Latest telemetry snapshot did not expose enough capacity to recommend a load shift.",
            "action": None,
        }

    source_temperature = (
        float(source["temperature"]) if source.get("temperature") is not None else None
    )
    source_load_after = round(source_load_before - load_shifted, 2)
    target_load_after = round(target_load_before + load_shifted, 2)
    risk_before = calculate_risk_score(source_load_before, source_temperature)
    risk_after = calculate_risk_score(source_load_after, source_temperature)
    target_node = normalize_node_name(target["substation"])

    action = store_balancing_action(
        source_node=source_node,
        target_node=target_node,
        load_shifted=load_shifted,
        trigger_reason=(
            f"Latest telemetry snapshot identified Substation {source_node} as the "
            f"highest-load node at {source_load_before}% and Substation {target_node} "
            f"as the lowest-load node at {target_load_before}%."
        ),
        action_status="pending",
        source_load_before=source_load_before,
        source_load_after=source_load_after,
        target_load_before=target_load_before,
        target_load_after=target_load_after,
        risk_before=risk_before,
        risk_after=risk_after,
        effectiveness="pending",
        execution_mode="approval",
        decision_notes=(
            "Created from the latest telemetry snapshot for operator review "
            "without invoking the autonomous optimizer execution path."
        ),
    )

    return {
        "status": "success",
        "message": "Load balancing recommendation created from the latest telemetry snapshot.",
        "action": action,
    }


def execute_load_balancing(
    execution_mode: str = "automatic",
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    Main Week 5 load balancing engine.

    Workflow:
    1. Read latest node telemetry.
    2. Detect overloaded source node.
    3. Find healthiest target node.
    4. Calculate safe simulated load shift.
    5. Store action with before/after impact.

    Supported execution modes:
    - automatic: immediately stores action as executed.
    - manual: immediately stores action as executed through API trigger.
    - approval: stores action as pending until operator approves/rejects.
    """
    nodes = get_latest_node_states()

    if not nodes:
        return {
            "status": "no_action",
            "reason": "No telemetry records available.",
            "action": None,
        }

    prediction_map = get_latest_prediction_risk_by_node()

    source = find_overloaded_source(nodes)

    if not source:
        return {
            "status": "no_action",
            "reason": f"No node load exceeded overload threshold of {OVERLOAD_THRESHOLD}%.",
            "action": None,
        }

    source_node = normalize_node_name(source["substation"])
    source_load_before = float(source["load"])
    source_temperature = (
        float(source["temperature"]) if source.get("temperature") is not None else None
    )

    target = find_best_target(nodes, source_node, prediction_map)

    if not target:
        return {
            "status": "no_action",
            "reason": "No safe target node found for redistribution.",
            "source_node": source_node,
            "source_load": source_load_before,
            "action": None,
        }

    target_node = normalize_node_name(target["substation"])
    target_load_before = float(target["load"])
    target_temperature = (
        float(target["temperature"]) if target.get("temperature") is not None else None
    )

    load_shifted = calculate_load_shift(
        source_load=source_load_before,
        target_load=target_load_before,
    )

    if load_shifted <= 0:
        return {
            "status": "no_action",
            "reason": "Calculated load shift was below minimum safe shift threshold.",
            "source_node": source_node,
            "target_node": target_node,
            "action": None,
        }

    source_load_after = round(source_load_before - load_shifted, 2)
    target_load_after = round(target_load_before + load_shifted, 2)

    risk_before = calculate_risk_score(source_load_before, source_temperature)
    risk_after = calculate_risk_score(source_load_after, source_temperature)

    effectiveness = "successful" if risk_after < risk_before else "ineffective"

    trigger_reason = (
        f"Substation {source_node} load reached {source_load_before}%, "
        f"exceeding threshold of {OVERLOAD_THRESHOLD}%."
    )

    decision_notes = (
        f"Decision engine selected Substation {target_node} because it had "
        f"available capacity below {TARGET_MAX_LOAD}% load. "
        f"Simulated load shift reduced Substation {source_node} from "
        f"{source_load_before}% to {source_load_after}%."
    )

    action_preview = {
        "source_node": source_node,
        "target_node": target_node,
        "load_shifted": load_shifted,
        "trigger_reason": trigger_reason,
        "action_status": "dry_run" if dry_run else "executed",
        "source_load_before": source_load_before,
        "source_load_after": source_load_after,
        "target_load_before": target_load_before,
        "target_load_after": target_load_after,
        "risk_before": risk_before,
        "risk_after": risk_after,
        "effectiveness": effectiveness,
        "execution_mode": execution_mode,
        "decision_notes": decision_notes,
    }

    if dry_run:
        return {
            "status": "dry_run",
            "reason": "Load balancing decision calculated but not stored.",
            "action": action_preview,
        }

    requires_approval = execution_mode == "approval"

    action_status = "pending" if requires_approval else "executed"
    response_status = "pending_approval" if requires_approval else "executed"

    response_reason = (
        "Load balancing recommendation created and is awaiting operator approval."
        if requires_approval
        else "Autonomous load balancing action completed."
    )

    stored_effectiveness = "pending" if requires_approval else effectiveness

    action = store_balancing_action(
        source_node=source_node,
        target_node=target_node,
        load_shifted=load_shifted,
        trigger_reason=trigger_reason,
        action_status=action_status,
        source_load_before=source_load_before,
        source_load_after=source_load_after,
        target_load_before=target_load_before,
        target_load_after=target_load_after,
        risk_before=risk_before,
        risk_after=risk_after,
        effectiveness=stored_effectiveness,
        execution_mode=execution_mode,
        decision_notes=decision_notes,
    )

    return {
        "status": response_status,
        "reason": response_reason,
        "action": action,
    }


if __name__ == "__main__":
    result = execute_load_balancing(execution_mode="manual")
    print(result)