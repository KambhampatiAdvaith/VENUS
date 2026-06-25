import os
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Query
from sqlalchemy import create_engine, text

from backend.optimization.load_balancer import execute_load_balancing


router = APIRouter()


def get_database_url() -> str:
    return os.getenv(
        "DATABASE_URL",
        "postgresql://venus:venus@localhost:5432/venus_db",
    )


def get_engine():
    return create_engine(get_database_url())


def serialize_action(action: dict[str, Any]) -> dict[str, Any]:
    if isinstance(action.get("created_at"), datetime):
        action["created_at"] = action["created_at"].isoformat()

    return action


def calculate_percentage_change(before: float, after: float) -> float:
    if before == 0:
        return 0.0

    return round(((before - after) / before) * 100, 2)


def build_impact_report(action: dict[str, Any]) -> dict[str, Any]:
    source_load_before = float(action["source_load_before"])
    source_load_after = float(action["source_load_after"])
    target_load_before = float(action["target_load_before"])
    target_load_after = float(action["target_load_after"])
    risk_before = float(action["risk_before"])
    risk_after = float(action["risk_after"])

    source_load_reduction = round(source_load_before - source_load_after, 2)
    target_load_increase = round(target_load_after - target_load_before, 2)
    risk_reduction = round(risk_before - risk_after, 4)

    source_load_reduction_percent = calculate_percentage_change(
        source_load_before,
        source_load_after,
    )

    risk_reduction_percent = calculate_percentage_change(
        risk_before,
        risk_after,
    )

    feedback_status = "successful"

    if action["action_status"] == "pending":
        feedback_status = "pending"

    elif action["action_status"] == "rejected":
        feedback_status = "rejected"

    elif source_load_after >= source_load_before:
        feedback_status = "ineffective"

    elif risk_after >= risk_before:
        feedback_status = "ineffective"

    return {
        "action_id": action["id"],
        "source_node": action["source_node"],
        "target_node": action["target_node"],
        "load_shifted": action["load_shifted"],
        "action_status": action["action_status"],
        "execution_mode": action["execution_mode"],
        "effectiveness": action["effectiveness"],
        "feedback_status": feedback_status,
        "trigger_reason": action["trigger_reason"],
        "decision_notes": action["decision_notes"],
        "before": {
            "source_load": source_load_before,
            "target_load": target_load_before,
            "risk_score": risk_before,
        },
        "after": {
            "source_load": source_load_after,
            "target_load": target_load_after,
            "risk_score": risk_after,
        },
        "impact": {
            "source_load_reduction": source_load_reduction,
            "source_load_reduction_percent": source_load_reduction_percent,
            "target_load_increase": target_load_increase,
            "risk_reduction": risk_reduction,
            "risk_reduction_percent": risk_reduction_percent,
        },
        "created_at": action["created_at"],
    }


def get_operator_workflow_label(execution_mode: str, action_status: str) -> str:
    if execution_mode == "approval" and action_status == "pending":
        return "Supervised mode: pending operator approval"

    if execution_mode == "approval" and action_status == "executed":
        return "Supervised mode: approved and executed"

    if execution_mode == "approval" and action_status == "rejected":
        return "Supervised mode: rejected by operator"

    if execution_mode == "manual":
        return "Manual mode: executed through API trigger"

    if execution_mode == "automatic":
        return "Automatic mode: executed by decision engine"

    return "Unknown workflow"


def build_decision_log_entry(action: dict[str, Any]) -> dict[str, Any]:
    risk_before = float(action["risk_before"])
    risk_after = float(action["risk_after"])
    source_load_before = float(action["source_load_before"])
    source_load_after = float(action["source_load_after"])

    risk_change = round(risk_before - risk_after, 4)
    load_change = round(source_load_before - source_load_after, 2)

    if action["action_status"] == "pending":
        result_observed = "Awaiting operator approval before execution."

    elif action["action_status"] == "rejected":
        result_observed = "Recommendation rejected by operator. No action executed."

    elif action["effectiveness"] == "successful":
        result_observed = (
            f"Successful. Source load reduced by {load_change}% "
            f"and risk reduced by {risk_change}."
        )

    else:
        result_observed = (
            f"Ineffective. Source load change: {load_change}%, "
            f"risk change: {risk_change}."
        )

    return {
        "decision_id": action["id"],
        "timestamp": action["created_at"],
        "prediction_trigger": action["trigger_reason"],
        "decision_taken": (
            f"Shift {action['load_shifted']}% simulated load from "
            f"Substation {action['source_node']} to Substation {action['target_node']}."
        ),
        "action_status": action["action_status"],
        "execution_mode": action["execution_mode"],
        "operator_workflow": get_operator_workflow_label(
            action["execution_mode"],
            action["action_status"],
        ),
        "result_observed": result_observed,
        "effectiveness": action["effectiveness"],
        "before": {
            "source_node": action["source_node"],
            "target_node": action["target_node"],
            "source_load": source_load_before,
            "target_load": float(action["target_load_before"]),
            "risk_score": risk_before,
        },
        "after": {
            "source_node": action["source_node"],
            "target_node": action["target_node"],
            "source_load": source_load_after,
            "target_load": float(action["target_load_after"]),
            "risk_score": risk_after,
        },
        "audit_notes": action["decision_notes"],
    }


def get_recent_actions(limit: int) -> list[dict[str, Any]]:
    engine = get_engine()

    query = """
        SELECT
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
        FROM load_balancing_actions
        ORDER BY created_at DESC
        LIMIT :limit
    """

    with engine.begin() as connection:
        rows = connection.execute(text(query), {"limit": limit}).mappings().all()

    return [serialize_action(dict(row)) for row in rows]


def get_executed_actions(limit: int) -> list[dict[str, Any]]:
    engine = get_engine()

    query = """
        SELECT
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
        FROM load_balancing_actions
        WHERE action_status = 'executed'
        ORDER BY created_at DESC
        LIMIT :limit
    """

    with engine.begin() as connection:
        rows = connection.execute(text(query), {"limit": limit}).mappings().all()

    return [serialize_action(dict(row)) for row in rows]


@router.get("/load-balancing")
def get_load_balancing_actions(
    limit: int = Query(default=50, ge=1, le=500),
):
    """
    Returns recent load balancing action history.
    """
    return get_recent_actions(limit)


@router.get("/load-balancing/latest")
def get_latest_load_balancing_action():
    """
    Returns the most recent load balancing action.
    """
    actions = get_recent_actions(1)

    if not actions:
        return {
            "status": "empty",
            "message": "No load balancing actions found.",
            "action": None,
        }

    return {
        "status": "success",
        "action": actions[0],
    }


@router.post("/load-balancing/execute")
def execute_load_balancing_action(
    execution_mode: str = Query(default="manual"),
    dry_run: bool = Query(default=False),
):
    """
    Manually triggers the load balancing engine.

    Query params:
    - execution_mode=manual or automatic
    - dry_run=true to preview decision without storing it
    """
    result = execute_load_balancing(
        execution_mode=execution_mode,
        dry_run=dry_run,
    )

    return result


@router.post("/load-balancing/recommend")
def create_load_balancing_recommendation():
    """
    Creates a pending load balancing recommendation.

    This supports supervised approval mode:
    Prediction/Overload -> Recommendation -> Pending Approval.
    """
    result = execute_load_balancing(
        execution_mode="approval",
        dry_run=False,
    )

    return result


@router.get("/load-balancing/pending")
def get_pending_load_balancing_actions(
    limit: int = Query(default=20, ge=1, le=100),
):
    """
    Returns pending load balancing recommendations awaiting approval.
    """
    engine = get_engine()

    query = """
        SELECT
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
        FROM load_balancing_actions
        WHERE action_status = 'pending'
        ORDER BY created_at DESC
        LIMIT :limit
    """

    with engine.begin() as connection:
        rows = connection.execute(text(query), {"limit": limit}).mappings().all()

    return {
        "status": "success",
        "count": len(rows),
        "actions": [serialize_action(dict(row)) for row in rows],
    }


@router.post("/load-balancing/approve/{action_id}")
def approve_load_balancing_action(action_id: int):
    """
    Approves and executes a pending load balancing recommendation.
    """
    engine = get_engine()

    select_query = """
        SELECT
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
        FROM load_balancing_actions
        WHERE id = :action_id
        LIMIT 1
    """

    update_query = """
        UPDATE load_balancing_actions
        SET
            action_status = 'executed',
            effectiveness = CASE
                WHEN risk_after < risk_before THEN 'successful'
                ELSE 'ineffective'
            END,
            decision_notes = decision_notes || ' Operator approved and executed this recommendation.'
        WHERE id = :action_id
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

    with engine.begin() as connection:
        existing = connection.execute(
            text(select_query),
            {"action_id": action_id},
        ).mappings().first()

        if not existing:
            return {
                "status": "not_found",
                "message": f"No load balancing action found with id {action_id}.",
                "action": None,
            }

        existing_action = dict(existing)

        if existing_action["action_status"] != "pending":
            return {
                "status": "invalid_state",
                "message": (
                    f"Action {action_id} cannot be approved because its current "
                    f"status is {existing_action['action_status']}."
                ),
                "action": serialize_action(existing_action),
            }

        updated = connection.execute(
            text(update_query),
            {"action_id": action_id},
        ).mappings().first()

    return {
        "status": "approved",
        "message": f"Load balancing action {action_id} approved and executed.",
        "action": serialize_action(dict(updated)),
    }


@router.post("/load-balancing/reject/{action_id}")
def reject_load_balancing_action(action_id: int):
    """
    Rejects a pending load balancing recommendation.
    """
    engine = get_engine()

    select_query = """
        SELECT
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
        FROM load_balancing_actions
        WHERE id = :action_id
        LIMIT 1
    """

    update_query = """
        UPDATE load_balancing_actions
        SET
            action_status = 'rejected',
            effectiveness = 'rejected',
            decision_notes = decision_notes || ' Operator rejected this recommendation.'
        WHERE id = :action_id
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

    with engine.begin() as connection:
        existing = connection.execute(
            text(select_query),
            {"action_id": action_id},
        ).mappings().first()

        if not existing:
            return {
                "status": "not_found",
                "message": f"No load balancing action found with id {action_id}.",
                "action": None,
            }

        existing_action = dict(existing)

        if existing_action["action_status"] != "pending":
            return {
                "status": "invalid_state",
                "message": (
                    f"Action {action_id} cannot be rejected because its current "
                    f"status is {existing_action['action_status']}."
                ),
                "action": serialize_action(existing_action),
            }

        updated = connection.execute(
            text(update_query),
            {"action_id": action_id},
        ).mappings().first()

    return {
        "status": "rejected",
        "message": f"Load balancing action {action_id} rejected.",
        "action": serialize_action(dict(updated)),
    }


@router.get("/load-balancing/impact/latest")
def get_latest_load_balancing_impact():
    """
    Returns the closed-loop impact report for the latest balancing action.
    """
    actions = get_recent_actions(1)

    if not actions:
        return {
            "status": "empty",
            "message": "No load balancing actions found.",
            "impact": None,
        }

    return {
        "status": "success",
        "impact": build_impact_report(actions[0]),
    }


@router.get("/load-balancing/impact")
def get_load_balancing_impact_history(
    limit: int = Query(default=20, ge=1, le=200),
):
    """
    Returns closed-loop impact reports for recent balancing actions.
    """
    actions = get_recent_actions(limit)

    return {
        "status": "success",
        "count": len(actions),
        "impacts": [build_impact_report(action) for action in actions],
    }


@router.get("/load-balancing/impact/summary")
def get_load_balancing_impact_summary(
    limit: int = Query(default=20, ge=1, le=200),
):
    """
    Returns aggregate closed-loop metrics for dashboard cards.

    Only executed actions are counted.
    Pending and rejected recommendations are excluded from effectiveness metrics.
    """
    actions = get_executed_actions(limit)

    if not actions:
        return {
            "status": "empty",
            "total_actions": 0,
            "successful_actions": 0,
            "success_rate": 0,
            "average_load_reduction": 0,
            "average_risk_reduction": 0,
        }

    total_actions = len(actions)

    successful_actions = len(
        [
            action
            for action in actions
            if action["effectiveness"] == "successful"
        ]
    )

    total_load_reduction = sum(
        float(action["source_load_before"]) - float(action["source_load_after"])
        for action in actions
    )

    total_risk_reduction = sum(
        float(action["risk_before"]) - float(action["risk_after"])
        for action in actions
    )

    success_rate = round((successful_actions / total_actions) * 100, 2)
    average_load_reduction = round(total_load_reduction / total_actions, 2)
    average_risk_reduction = round(total_risk_reduction / total_actions, 4)

    return {
        "status": "success",
        "total_actions": total_actions,
        "successful_actions": successful_actions,
        "success_rate": success_rate,
        "average_load_reduction": average_load_reduction,
        "average_risk_reduction": average_risk_reduction,
    }


@router.get("/load-balancing/decision-log")
def get_load_balancing_decision_log(
    limit: int = Query(default=50, ge=1, le=500),
):
    """
    Returns the complete operational decision log.

    This is the formal audit trail:
    Prediction Trigger -> Decision Taken -> Action Status -> Result Observed.
    """
    actions = get_recent_actions(limit)

    return {
        "status": "success",
        "count": len(actions),
        "decision_log": [build_decision_log_entry(action) for action in actions],
    }


@router.get("/load-balancing/decision-log/latest")
def get_latest_load_balancing_decision_log():
    """
    Returns the latest operational decision log entry.
    """
    actions = get_recent_actions(1)

    if not actions:
        return {
            "status": "empty",
            "message": "No decision log entries found.",
            "decision_log": None,
        }

    return {
        "status": "success",
        "decision_log": build_decision_log_entry(actions[0]),
    }


@router.get("/load-balancing/decision-log/summary")
def get_load_balancing_decision_log_summary(
    limit: int = Query(default=100, ge=1, le=1000),
):
    """
    Returns aggregate audit trail statistics.
    """
    actions = get_recent_actions(limit)

    if not actions:
        return {
            "status": "empty",
            "total_decisions": 0,
            "executed_decisions": 0,
            "pending_decisions": 0,
            "rejected_decisions": 0,
            "automatic_decisions": 0,
            "manual_decisions": 0,
            "approval_mode_decisions": 0,
        }

    total_decisions = len(actions)

    executed_decisions = len(
        [action for action in actions if action["action_status"] == "executed"]
    )

    pending_decisions = len(
        [action for action in actions if action["action_status"] == "pending"]
    )

    rejected_decisions = len(
        [action for action in actions if action["action_status"] == "rejected"]
    )

    automatic_decisions = len(
        [action for action in actions if action["execution_mode"] == "automatic"]
    )

    manual_decisions = len(
        [action for action in actions if action["execution_mode"] == "manual"]
    )

    approval_mode_decisions = len(
        [action for action in actions if action["execution_mode"] == "approval"]
    )

    return {
        "status": "success",
        "total_decisions": total_decisions,
        "executed_decisions": executed_decisions,
        "pending_decisions": pending_decisions,
        "rejected_decisions": rejected_decisions,
        "automatic_decisions": automatic_decisions,
        "manual_decisions": manual_decisions,
        "approval_mode_decisions": approval_mode_decisions,
    }