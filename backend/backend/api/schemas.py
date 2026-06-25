from datetime import datetime

from pydantic import BaseModel


class TelemetryRecord(BaseModel):
    id: int
    substation: str
    voltage: float
    current: float
    temperature: float
    load: float
    frequency: float
    timestamp: datetime

    edge_anomaly: bool | None = None
    edge_anomaly_score: float | None = None
    edge_model: str | None = None
    edge_processed_at: datetime | None = None


class TelemetryResponse(TelemetryRecord):
    pass


class FaultRecord(BaseModel):
    id: int
    substation: str
    fault_type: str
    severity: str | None = None
    timestamp: datetime


class FaultResponse(FaultRecord):
    pass


class DashboardMetricsResponse(BaseModel):
    total_nodes: int
    active_faults: int
    avg_load: float
    system_health: str


class DashboardMetrics(DashboardMetricsResponse):
    pass


class NodeStatusResponse(BaseModel):
    node: str
    status: str
    load: float | None = None
    voltage: float | None = None
    temperature: float | None = None
    frequency: float | None = None
    last_updated: datetime | None = None


class NodeStatus(NodeStatusResponse):
    pass


class PredictionRecord(BaseModel):
    id: int
    substation: str
    predicted_fault: str
    probability: float
    anomaly: bool
    anomaly_score: float
    timestamp: datetime


class PredictionResponse(PredictionRecord):
    pass


class PredictionMetricsResponse(BaseModel):
    predicted_faults: int
    risk_score: float
    system_risk_level: str


class PredictionMetrics(PredictionMetricsResponse):
    pass