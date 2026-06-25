const API_BASE_URL = "http://localhost:8000";

export type TelemetryRecord = {
    id: number;
    substation: string;
    voltage: number;
    current: number;
    temperature: number;
    load: number;
    frequency: number;
    timestamp: string;
    edge_anomaly?: boolean;
    edge_anomaly_score?: number | null;
    edge_model?: string | null;
    edge_processed_at?: string | null;
};


export type FaultRecord = {
    id: number;
    substation: string;
    fault_type: string;
    severity: string;
    timestamp: string;
};


export type DashboardMetrics = {
    total_nodes: number;
    active_faults: number;
    avg_load: number;
    system_health: string;
};


export type NodeStatus = {
    node: string;
    status: string;
    load: number | null;
    voltage: number | null;
    temperature: number | null;
    frequency: number | null;
    last_updated: string | null;
};


export type PredictionRecord = {
    id: number;
    substation: string;
    predicted_fault: string;
    probability: number;
    anomaly: boolean;
    anomaly_score: number;
    timestamp: string;
};


export type PredictionMetrics = {
    predicted_faults: number;
    risk_score: number;
    system_risk_level: string;
};


export type LoadBalancingAction = {
    id: number;
    source_node: string;
    target_node: string;
    load_shifted: number;
    trigger_reason: string;
    action_status: string;
    source_load_before: number;
    source_load_after: number;
    target_load_before: number;
    target_load_after: number;
    risk_before: number;
    risk_after: number;
    effectiveness: string;
    execution_mode: string;
    decision_notes: string;
    created_at: string;
};


export type LoadBalancingImpact = {
    action_id: number;
    source_node: string;
    target_node: string;
    load_shifted: number;
    action_status: string;
    execution_mode: string;
    effectiveness: string;
    feedback_status: string;
    trigger_reason: string;
    decision_notes: string;
    before: {
        source_load: number;
        target_load: number;
        risk_score: number;
    };
    after: {
        source_load: number;
        target_load: number;
        risk_score: number;
    };
    impact: {
        source_load_reduction: number;
        source_load_reduction_percent: number;
        target_load_increase: number;
        risk_reduction: number;
        risk_reduction_percent: number;
    };
    created_at: string;
};


export type LoadBalancingSummary = {
    status: string;
    total_actions: number;
    successful_actions: number;
    success_rate: number;
    average_load_reduction: number;
    average_risk_reduction: number;
};


export type LoadBalancingDecisionLog = {
    decision_id: number;
    timestamp: string;
    prediction_trigger: string;
    decision_taken: string;
    action_status: string;
    execution_mode: string;
    operator_workflow: string;
    result_observed: string;
    effectiveness: string;
    before: {
        source_node: string;
        target_node: string;
        source_load: number;
        target_load: number;
        risk_score: number;
    };
    after: {
        source_node: string;
        target_node: string;
        source_load: number;
        target_load: number;
        risk_score: number;
    };
    audit_notes: string;
};


export type LoadBalancingDecisionLogSummary = {
    status: string;
    total_decisions: number;
    executed_decisions: number;
    pending_decisions: number;
    rejected_decisions: number;
    automatic_decisions: number;
    manual_decisions: number;
    approval_mode_decisions: number;
};


async function apiFetch<T>(
    endpoint: string,
    options?: RequestInit,
): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        cache: "no-store",
        ...options,
    });

    if (!response.ok) {
        throw new Error(`API request failed: ${endpoint}`);
    }

    return response.json();
}


export const api = {
    getTelemetry(limit = 50): Promise<TelemetryRecord[]> {
        return apiFetch<TelemetryRecord[]>(`/telemetry?limit=${limit}`);
    },


    getFaults(limit = 50): Promise<FaultRecord[]> {
        return apiFetch<FaultRecord[]>(`/faults?limit=${limit}`);
    },


    getNodes(): Promise<NodeStatus[]> {
        return apiFetch<NodeStatus[]>("/nodes");
    },


    getDashboardMetrics(): Promise<DashboardMetrics> {
        return apiFetch<DashboardMetrics>("/dashboard/metrics");
    },


    getPredictions(limit = 50): Promise<PredictionRecord[]> {
        return apiFetch<PredictionRecord[]>(`/predictions?limit=${limit}`);
    },


    getPredictionMetrics(): Promise<PredictionMetrics> {
        return apiFetch<PredictionMetrics>("/predictions/metrics");
    },


    runPredictions(): Promise<{
        message: string;
        count: number;
        predictions: PredictionRecord[];
    }> {
        return apiFetch<{
            message: string;
            count: number;
            predictions: PredictionRecord[];
        }>("/predictions/run", {
            method: "POST",
        });
    },


    getLoadBalancingActions(limit = 10): Promise<LoadBalancingAction[]> {
        return apiFetch<LoadBalancingAction[]>(`/load-balancing?limit=${limit}`);
    },


    async getLatestLoadBalancingImpact(): Promise<LoadBalancingImpact | null> {
        const data = await apiFetch<{
            status: string;
            impact: LoadBalancingImpact | null;
        }>("/load-balancing/impact/latest");

        return data.impact;
    },


    getLoadBalancingSummary(): Promise<LoadBalancingSummary> {
        return apiFetch<LoadBalancingSummary>("/load-balancing/impact/summary");
    },


    createLoadBalancingRecommendation() {
        return apiFetch("/load-balancing/recommend", {
            method: "POST",
        });
    },


    async getPendingLoadBalancingActions(
        limit = 10,
    ): Promise<LoadBalancingAction[]> {
        const data = await apiFetch<{
            status: string;
            count: number;
            actions: LoadBalancingAction[];
        }>(`/load-balancing/pending?limit=${limit}`);

        return data.actions;
    },


    approveLoadBalancingAction(actionId: number) {
        return apiFetch(`/load-balancing/approve/${actionId}`, {
            method: "POST",
        });
    },


    rejectLoadBalancingAction(actionId: number) {
        return apiFetch(`/load-balancing/reject/${actionId}`, {
            method: "POST",
        });
    },


    async getLoadBalancingDecisionLog(
        limit = 50,
    ): Promise<LoadBalancingDecisionLog[]> {
        const data = await apiFetch<{
            status: string;
            count: number;
            decision_log: LoadBalancingDecisionLog[];
        }>(`/load-balancing/decision-log?limit=${limit}`);

        return data.decision_log;
    },


    async getLatestLoadBalancingDecisionLog():
        Promise<LoadBalancingDecisionLog | null> {
        const data = await apiFetch<{
            status: string;
            decision_log: LoadBalancingDecisionLog | null;
        }>("/load-balancing/decision-log/latest");

        return data.decision_log;
    },


    getLoadBalancingDecisionLogSummary():
        Promise<LoadBalancingDecisionLogSummary> {
        return apiFetch<LoadBalancingDecisionLogSummary>(
            "/load-balancing/decision-log/summary",
        );
    },
};