const LOCAL_WS_URL = "ws://localhost:8000/ws/live";
let hasWarnedAboutMissingWebSocketConfig = false;


function resolveWebSocketUrl(): string | null {
    const configuredUrl = process.env.NEXT_PUBLIC_WS_URL?.trim();

    if (configuredUrl) {
        return configuredUrl;
    }

    const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();

    if (apiBaseUrl) {
        try {
            const parsedApiBaseUrl = new URL(apiBaseUrl);
            const protocol =
                parsedApiBaseUrl.protocol === "https:" ? "wss:" : "ws:";

            return `${protocol}//${parsedApiBaseUrl.host}/ws/live`;
        } catch {
            return null;
        }
    }

    if (typeof window !== "undefined") {
        const isLocalHost =
            window.location.hostname === "localhost" ||
            window.location.hostname === "127.0.0.1";

        if (isLocalHost) {
            return LOCAL_WS_URL;
        }
    }

    if (!hasWarnedAboutMissingWebSocketConfig) {
        console.warn(
            "WebSocket URL is not configured. Set NEXT_PUBLIC_WS_URL or NEXT_PUBLIC_API_BASE_URL for deployed environments.",
        );
        hasWarnedAboutMissingWebSocketConfig = true;
    }

    return null;
}

export type LiveEvent = {
    event: "telemetry" | "prediction" | "fault" | "load_balancing" | string;
    data: Record<string, unknown>;
};

type EventHandler = (event: LiveEvent) => void;
type ConnectionStatusHandler = () => void;

type WebSocketClientOptions = {
    onOpen?: ConnectionStatusHandler;
    onClose?: ConnectionStatusHandler;
};


/**
 * Lightweight WebSocket client with automatic reconnection.
 *
 * Usage:
 *   const ws = createWebSocketClient(handler);
 *   ws.connect();
 *   // later:
 *   ws.disconnect();
 */
export function createWebSocketClient(
    onEvent: EventHandler,
    options: WebSocketClientOptions = {},
) {
    let socket: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let stopped = false;

    const RECONNECT_DELAY_MS = 3000;

    function connect() {
        if (stopped) return;

        const wsUrl = resolveWebSocketUrl();

        if (!wsUrl) {
            return;
        }

        try {
            socket = new WebSocket(wsUrl);
        } catch {
            scheduleReconnect();
            return;
        }

        socket.onopen = () => {
            options.onOpen?.();
        };

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
            options.onClose?.();
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
