import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.api.database import Base
from backend.api.fault_window import (
    DEFAULT_ACTIVE_FAULT_WINDOW_MINUTES,
    count_active_faults,
    get_active_fault_counts_by_substation,
    get_active_fault_cutoff,
    get_active_fault_window_minutes,
)
from backend.api.models import Fault, Telemetry
from backend.api.routes.dashboard import get_dashboard_metrics
from backend.api.routes.nodes import get_node_status


class ActiveFaultWindowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.session = self.SessionLocal()
        self.now = datetime.now(timezone.utc)

    def tearDown(self) -> None:
        self.session.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def add_fault(self, *, substation: str, minutes_ago: int) -> None:
        self.session.add(
            Fault(
                substation=substation,
                fault_type="overload",
                severity="high",
                timestamp=self.now - timedelta(minutes=minutes_ago),
            )
        )
        self.session.commit()

    def add_telemetry(self, *, substation: str, load: float) -> None:
        timestamp = self.now - timedelta(minutes=1)
        self.session.add(
            Telemetry(
                substation=substation,
                voltage=230.0,
                current=10.0,
                temperature=42.0,
                load=load,
                frequency=50.0,
                timestamp=timestamp,
                generated_at=timestamp,
                kafka_received_at=timestamp,
                database_written_at=timestamp,
            )
        )
        self.session.commit()

    def test_invalid_fault_window_env_falls_back_to_default(self) -> None:
        with patch.dict(os.environ, {"ACTIVE_FAULT_WINDOW_MINUTES": "invalid"}):
            self.assertEqual(
                get_active_fault_window_minutes(),
                DEFAULT_ACTIVE_FAULT_WINDOW_MINUTES,
            )

        with patch.dict(os.environ, {"ACTIVE_FAULT_WINDOW_MINUTES": ""}):
            self.assertEqual(
                get_active_fault_window_minutes(),
                DEFAULT_ACTIVE_FAULT_WINDOW_MINUTES,
            )

    def test_historical_fault_older_than_window_does_not_keep_node_in_fault(self) -> None:
        self.add_fault(substation="A", minutes_ago=30)

        with patch.dict(os.environ, {"ACTIVE_FAULT_WINDOW_MINUTES": "10"}):
            active_fault_counts = get_active_fault_counts_by_substation(
                self.session,
                now=self.now,
            )

        status = get_node_status(
            temperature=42.0,
            voltage=230.0,
            frequency=50.0,
            load=52.0,
            fault_count=active_fault_counts.get("A", 0),
        )

        self.assertEqual(active_fault_counts.get("A", 0), 0)
        self.assertEqual(status, "healthy")

    def test_recent_fault_inside_window_sets_node_to_fault(self) -> None:
        self.add_fault(substation="B", minutes_ago=5)

        with patch.dict(os.environ, {"ACTIVE_FAULT_WINDOW_MINUTES": "10"}):
            active_fault_counts = get_active_fault_counts_by_substation(
                self.session,
                now=self.now,
            )

        status = get_node_status(
            temperature=42.0,
            voltage=230.0,
            frequency=50.0,
            load=52.0,
            fault_count=active_fault_counts.get("B", 0),
        )

        self.assertEqual(active_fault_counts.get("B"), 1)
        self.assertEqual(status, "fault")

    def test_dashboard_active_fault_count_excludes_old_faults(self) -> None:
        self.add_fault(substation="A", minutes_ago=25)
        self.add_telemetry(substation="A", load=48.0)
        self.add_telemetry(substation="B", load=52.0)

        with patch.dict(os.environ, {"ACTIVE_FAULT_WINDOW_MINUTES": "10"}):
            metrics = get_dashboard_metrics(self.session)

        self.assertEqual(metrics["total_nodes"], 2)
        self.assertEqual(metrics["active_faults"], 0)
        self.assertEqual(metrics["system_health"], "healthy")

    def test_dashboard_active_fault_count_includes_recent_faults(self) -> None:
        self.add_fault(substation="A", minutes_ago=3)
        self.add_fault(substation="B", minutes_ago=7)
        self.add_telemetry(substation="A", load=48.0)
        self.add_telemetry(substation="B", load=52.0)
        self.add_telemetry(substation="C", load=46.0)

        with patch.dict(os.environ, {"ACTIVE_FAULT_WINDOW_MINUTES": "10"}):
            metrics = get_dashboard_metrics(self.session)

        self.assertEqual(metrics["total_nodes"], 3)
        self.assertEqual(metrics["active_faults"], 2)
        self.assertEqual(metrics["system_health"], "warning")

    def test_active_fault_cutoff_uses_configured_window(self) -> None:
        with patch.dict(os.environ, {"ACTIVE_FAULT_WINDOW_MINUTES": "15"}):
            cutoff = get_active_fault_cutoff(self.now)

        self.assertEqual(cutoff, self.now - timedelta(minutes=15))
        self.assertEqual(count_active_faults(self.session, now=self.now), 0)


if __name__ == "__main__":
    unittest.main()
