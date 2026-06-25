const STALE_TELEMETRY_MS = 2 * 60 * 1000;


export type TelemetryFreshness = {
    lastTelemetryUpdate: string;
    dataAge: string;
    isStale: boolean;
};


export function getTelemetryFreshness(
    timestamp: string | null | undefined,
    now = new Date(),
): TelemetryFreshness {
    if (!timestamp) {
        return {
            lastTelemetryUpdate: "N/A",
            dataAge: "No telemetry data",
            isStale: true,
        };
    }

    const telemetryTime = new Date(timestamp);
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
