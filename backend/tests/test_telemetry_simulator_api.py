import unittest
from unittest.mock import AsyncMock, patch

from backend.api import telemetry_simulator


INSERTED_ROWS = [
    {"substation": "A", "edge_anomaly": False},
    {"substation": "B", "edge_anomaly": True},
    {"substation": "C"},
]


class TelemetrySimulatorApiTests(unittest.IsolatedAsyncioTestCase):
    async def test_simulate_single_cycle_broadcasts_telemetry_event(self) -> None:
        with (
            patch.object(
                telemetry_simulator,
                "generate_telemetry_cycle",
                return_value=("normal", [{"substation": "A"}]),
            ),
            patch.object(
                telemetry_simulator,
                "insert_telemetry",
                return_value=INSERTED_ROWS,
            ),
            patch.object(
                telemetry_simulator.manager,
                "broadcast",
                new=AsyncMock(),
            ) as broadcast_mock,
        ):
            response = await telemetry_simulator.simulate_single_telemetry_cycle()

        self.assertEqual(response["status"], "success")
        self.assertEqual(response["scenario"], "normal")
        self.assertEqual(response["count"], len(INSERTED_ROWS))
        self.assertEqual(response["readings"], INSERTED_ROWS)
        broadcast_mock.assert_awaited_once_with(
            "telemetry",
            {
                "scenario": "normal",
                "count": len(INSERTED_ROWS),
                "edge_anomaly_count": 1,
            },
        )

    async def test_manual_scenarios_broadcast_telemetry_event(self) -> None:
        cases = [
            (
                telemetry_simulator.simulate_normal_telemetry,
                "normal",
            ),
            (
                telemetry_simulator.simulate_overload_b_telemetry,
                "overload_b",
            ),
            (
                telemetry_simulator.simulate_overload_c_telemetry,
                "overload_c",
            ),
            (
                telemetry_simulator.simulate_fault_telemetry,
                "fault",
            ),
        ]

        for handler, scenario in cases:
            with self.subTest(scenario=scenario):
                with (
                    patch.object(
                        telemetry_simulator,
                        "build_normal_telemetry",
                        return_value=[{"substation": "A"}],
                    ),
                    patch.object(
                        telemetry_simulator,
                        "build_overload_telemetry",
                        return_value=[{"substation": "B"}],
                    ),
                    patch.object(
                        telemetry_simulator,
                        "insert_telemetry",
                        return_value=INSERTED_ROWS,
                    ),
                    patch.object(
                        telemetry_simulator.random,
                        "choice",
                        return_value="B",
                    ),
                    patch.object(
                        telemetry_simulator.manager,
                        "broadcast",
                        new=AsyncMock(),
                    ) as broadcast_mock,
                ):
                    response = await handler()

                self.assertEqual(response["status"], "success")
                self.assertEqual(response["scenario"], scenario)
                self.assertEqual(response["count"], len(INSERTED_ROWS))
                self.assertEqual(response["readings"], INSERTED_ROWS)
                broadcast_mock.assert_awaited_once_with(
                    "telemetry",
                    {
                        "scenario": scenario,
                        "count": len(INSERTED_ROWS),
                        "edge_anomaly_count": 1,
                    },
                )


if __name__ == "__main__":
    unittest.main()
