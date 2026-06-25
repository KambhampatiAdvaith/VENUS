from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text

from backend.api.database import Base


class Telemetry(Base):
    __tablename__ = "telemetry"

    id = Column(Integer, primary_key=True, index=True)
    substation = Column(String(20), nullable=False)
    voltage = Column(Float, nullable=False)
    current = Column("current", Float, nullable=False)
    temperature = Column(Float, nullable=False)
    load = Column("load", Float, nullable=False)
    frequency = Column(Float, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    edge_anomaly = Column(Boolean, nullable=True, default=False)
    edge_anomaly_score = Column(Float, nullable=True)
    edge_model = Column(String(100), nullable=True)
    edge_processed_at = Column(DateTime(timezone=True), nullable=True)


class Fault(Base):
    __tablename__ = "faults"

    id = Column(Integer, primary_key=True, index=True)
    substation = Column(String(20), nullable=False)
    fault_type = Column(String(100), nullable=False)
    severity = Column(String(50), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    message = Column(Text, nullable=False)
    severity = Column(String(50), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)


class LoadBalancing(Base):
    __tablename__ = "load_balancing"

    id = Column(Integer, primary_key=True, index=True)
    source_node = Column(String(20), nullable=False)
    target_node = Column(String(20), nullable=False)
    load_shifted = Column(Float, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)