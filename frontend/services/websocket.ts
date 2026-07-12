const WS_URL =
    process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws/live";

export type LiveEvent = {
    event: "telemetry" | "prediction" | "fault" | "load_balancing" | string;
    data: Record<string, unknown>;
};

type EventHandler = (event: LiveEvent) => void;


/**
 * Lightweight WebSocket client with automatic reconnection.
 *
 * Usage:
 *   const ws = createWebSocketClient(handler);
 *   ws.connect();
 *   // later:
 *   ws.disconnect();
 */
export function createWebSocketClient(onEvent: EventHandler) {
    let socket: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let stopped = false;

    const RECONNECT_DELAY_MS = 3000;

    function connect() {
        if (stopped) return;

        try {
            socket = new WebSocket(WS_URL);
        } catch {
            scheduleReconnect();
            return;
        }

        socket.onmessage = (event) => {
            try {
                const parsed: LiveEvent = JSON.parse(event.data as string);
                onEvent(parsed);
            } catch {
                // ignore malformed frames
            }
        };

        socket.onclose = () => {
            socket = null;
            scheduleReconnect();
        };

        socket.onerror = () => {
            socket?.close();
        };
    }

    function scheduleReconnect() {
        if (stopped) return;
        if (reconnectTimer !== null) return;

        reconnectTimer = setTimeout(() => {
            reconnectTimer = null;
            connect();
        }, RECONNECT_DELAY_MS);
    }

    function disconnect() {
        stopped = true;

        if (reconnectTimer !== null) {
            clearTimeout(reconnectTimer);
            reconnectTimer = null;
        }

        if (socket) {
            socket.close();
            socket = null;
        }
    }

    return { connect, disconnect };
}
