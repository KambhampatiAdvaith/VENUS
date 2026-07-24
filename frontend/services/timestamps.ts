export type TimestampFields = {
    database_written_at?: string | null;
    updated_at?: string | null;
    created_at?: string | null;
    timestamp?: string | null;
};


export function getDisplayTimestamp(fields: TimestampFields): string | null {
    return (
        fields.database_written_at
        ?? fields.updated_at
        ?? fields.created_at
        ?? fields.timestamp
        ?? null
    );
}


export function parseDisplayTimestamp(fields: TimestampFields): Date | null {
    const timestamp = getDisplayTimestamp(fields);

    if (!timestamp) {
        return null;
    }

    const date = new Date(timestamp);

    if (Number.isNaN(date.getTime())) {
        return null;
    }

    return date;
}


export function formatDisplayTimestamp(fields: TimestampFields): string {
    const date = parseDisplayTimestamp(fields);

    if (!date) {
        return "N/A";
    }

    return date.toLocaleString();
}


export function formatDisplayTime(fields: TimestampFields): string {
    const date = parseDisplayTimestamp(fields);

    if (!date) {
        return "N/A";
    }

    return date.toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
    });
}
