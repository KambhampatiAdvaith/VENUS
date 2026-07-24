import { getDisplayTimestamp } from "./timestamps";


const STALE_TELEMETRY_MS = 2 * 60 * 1000;


export type TelemetryFreshness = {
    lastTelemetryUpdate: string;
    dataAge: string;
    isStale: boolean;
};


/**
 * Computes freshness from the best available timestamp.
 *
 * Week 7: prefers `database_written_at` (ingestion time) over the payload
 * `timestamp` so that timezone-shifted simulator timestamps do not make live
 * inserts appear stale. Falls back to `timestamp` when the ingestion field is
 * absent (older records, pre-migration rows).
 */
export function getTelemetryFreshness(
    timestamp: string | null | undefined,
    now = new Date(),
    databaseWrittenAt?: string | null,
): TelemetryFreshness {
    const effectiveTimestamp = getDisplayTimestamp({
        database_written_at: databaseWrittenAt,
        timestamp,
    });

    if (!effectiveTimestamp) {
        return {
            lastTelemetryUpdate: "N/A",
            dataAge: "No telemetry data",
            isStale: true,
        };
    }

    const telemetryTime = new Date(effectiveTimestamp);
    const ageMs = now.getTime() - telemetryTime.getTime();

    if (!Number.isFinite(ageMs)) {
        return {
            lastTelemetryUpdate: "Invalid timestamp",
            dataAge: "Unknown",
            isStale: true,
        };
    }

    const ageSeconds = Math.max(0, Math.floor(ageMs / 1000));
    const ageMinutes = Math.floor(ageSeconds / 60);
    const remainingSeconds = ageSeconds % 60;

    return {
        lastTelemetryUpdate: telemetryTime.toLocaleString(),
        dataAge: ageMinutes > 0
            ? `${ageMinutes}m ${remainingSeconds}s`
            : `${remainingSeconds}s`,
        isStale: ageMs > STALE_TELEMETRY_MS,
    };
}
