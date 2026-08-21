import unittest
from datetime import datetime, timezone

from simulator.realism import (
    build_normal_grid_telemetry,
    build_overload_grid_telemetry,
    calculate_frequency,
    calculate_temperature,
    calculate_voltage,
    get_daily_load_factor,
    SUBSTATION_ORDER,
)


class SimulatorRealismTests(unittest.TestCase):
    def test_daily_load_curve_peaks_in_evening(self) -> None:
        self.assertLess(get_daily_load_factor(2), get_daily_load_factor(19))

        night = build_normal_grid_telemetry(datetime(2026, 7, 24, 2, 0, tzinfo=timezone.utc))
        evening = build_normal_grid_telemetry(datetime(2026, 7, 24, 19, 0, tzinfo=timezone.utc))

        night_average = sum(reading["load"] for reading in night) / len(night)
        evening_average = sum(reading["load"] for reading in evening) / len(evening)

        self.assertLess(night_average, evening_average)

    def test_voltage_drops_as_load_rises(self) -> None:
        self.assertGreater(calculate_voltage(40), calculate_voltage(60))
        self.assertGreater(calculate_voltage(60), calculate_voltage(80))
        self.assertGreater(calculate_voltage(80), calculate_voltage(95))

    def test_temperature_rises_as_load_rises(self) -> None:
        self.assertLess(calculate_temperature(40), calculate_temperature(60))
        self.assertLess(calculate_temperature(60), calculate_temperature(80))

    def test_normal_frequency_stays_in_expected_band(self) -> None:
        for hour in (2, 8, 14, 19, 22):
            readings = build_normal_grid_telemetry(
                datetime(2026, 7, 24, hour, 0, tzinfo=timezone.utc)
            )

            for reading in readings:
                self.assertGreaterEqual(reading["frequency"], 49.8)
                self.assertLessEqual(reading["frequency"], 50.2)

        self.assertGreaterEqual(calculate_frequency(95), 49.8)
        self.assertLessEqual(calculate_frequency(95), 50.2)

    def test_overload_fault_remains_distinguishable(self) -> None:
        # pick a source node from the generated order (use second node to exercise wrap)
        source = SUBSTATION_ORDER[1]
        readings = build_overload_grid_telemetry(
            source,
            datetime(2026, 7, 24, 19, 0, tzinfo=timezone.utc),
        )
        by_substation = {reading["substation"]: reading for reading in readings}

        # verify the source node is overloaded and frequency falls
        self.assertGreaterEqual(by_substation[source]["load"], 88.0)
        self.assertLessEqual(by_substation[source]["frequency"], 49.7)

        # ensure some relative relationship still holds: source load >= some other node
        other = SUBSTATION_ORDER[0] if SUBSTATION_ORDER[0] != source else SUBSTATION_ORDER[2]
        self.assertGreater(by_substation[source]["load"], by_substation[other]["load"])


if __name__ == "__main__":
    unittest.main()
