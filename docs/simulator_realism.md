# Simulator Realism Enhancement

Week 8 Task 4 improves the telemetry simulator so normal readings better match a
real power distribution segment without changing API contracts, schemas, or
dashboard field names.

## What changed

### Daily load curve

Normal telemetry now follows a lightweight time-of-day demand pattern:

- **Night (00:00-05:00):** lower demand
- **Morning (05:00-09:00):** rising demand
- **Afternoon (09:00-16:00):** stable moderate demand
- **Evening (16:00-20:00):** peak demand
- **Late night (20:00-24:00):** demand declines again

Small controlled noise is still applied so readings continue to change between
simulation cycles.

### Correlated substations

Substations `A`, `B`, and `C` now share a common grid context instead of using
fully independent random values. A shared regional demand signal raises or lowers
multiple substations together, while a transfer signal makes one node increase as
another compensates. This keeps the dashboard demo realistic while remaining
deterministic enough for repeatable validation.

### Voltage vs load

Voltage now decreases as load rises. The simulator targets this approximate
relationship during normal operation:

- 40% load -> about 231 V
- 60% load -> about 229 V
- 80% load -> about 226 V
- 95% load -> about 223 V

Small offsets and noise are added per substation, but readings stay within the
existing expected ranges.

### Temperature vs load

Temperature now ramps up gradually with higher load instead of jumping randomly.
Each substation has a small baseline offset, plus a shared ambient-style bias and
small cycle-to-cycle noise.

### Frequency behavior

Normal frequency remains constrained to **49.8 Hz-50.2 Hz**. Heavier normal load
slightly depresses frequency, but not enough to leave the accepted band. Fault or
overload simulation still produces stronger deviations so anomaly detection and
prediction flows remain distinguishable.

### Fault simulation

The normal telemetry helpers are also used as the baseline for overload/fault
simulation. Fault cycles still force clearly abnormal source-node values for load,
current, voltage, temperature, and frequency so edge anomaly detection and
prediction testing remain meaningful.

## Validation

Use the existing Week 8 validation materials:

- [End-to-End Validation Runbook](week8_validation.md)
- [Functional Testing Checklist](week8_functional_testing.md)
- [Evidence Collection Checklist](week8_evidence_checklist.md)
- [Final Performance Benchmarking](week8_benchmarking.md)
- [Resource Utilization Profile](week8_resource_profile.md)

Suggested checks:

1. Run `POST /telemetry/simulate/normal` at different times and compare load
   trends.
2. Run `POST /telemetry/simulate/fault` and confirm the injected source node is
   still clearly abnormal.
3. Verify voltage falls as load rises and that normal frequency remains inside
   49.8-50.2 Hz.
4. Run `python -m compileall backend simulator tests` from the `backend/`
   directory.
5. Run `python -m unittest discover -s tests -p "test_*.py"` from the
   `backend/` directory.
