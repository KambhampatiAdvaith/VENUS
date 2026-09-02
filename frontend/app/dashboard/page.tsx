import Sidebar from "../../components/Sidebar";
import MetricCard from "../../components/MetricCard";
import LoadChart, { LoadChartData } from "../../components/LoadChart";
import Navbar from "../../components/Navbar";
import LoadBalancingControls from "../../components/LoadBalancingControls";
import DecisionLogPanel from "../../components/DecisionLogPanel";
import AutoRefreshControls from "../../components/AutoRefreshControls";
import LiveUpdateBanner from "../../components/LiveUpdateBanner";
import LiveAnalysisCard from "../../components/LiveAnalysisCard";
import { getTelemetryFreshness } from "../../services/telemetryFreshness";
import {
  formatDisplayTime,
  formatDisplayTimestamp,
} from "../../services/timestamps";
import {
  api,
  DashboardMetrics,
  NodeStatus,
  TelemetryRecord,
  PredictionMetrics,
  LoadBalancingAction,
  LoadBalancingImpact,
  LoadBalancingSummary,
  LatencyMetrics,
  FaultRecord,
} from "../../services/api";

export const dynamic = "force-dynamic";


const fallbackMetrics: DashboardMetrics = {
  total_nodes: 20,
  active_faults: 0,
  avg_load: 0,
  system_health: "unknown",
};


const fallbackNodes: NodeStatus[] = Array.from({ length: 20 }, (_, index) => ({
  node: String(index + 1),
  status: "unknown",
  load: null,
  voltage: null,
  temperature: null,
  frequency: null,
  last_updated: null,
}));


const fallbackTelemetry: TelemetryRecord[] = [];
const fallbackFaults: FaultRecord[] = [];


const fallbackPredictionMetrics: PredictionMetrics = {
  predicted_faults: 0,
  risk_score: 0,
  system_risk_level: "unknown",
};


const fallbackLoadBalancingActions: LoadBalancingAction[] = [];


const fallbackLoadBalancingSummary: LoadBalancingSummary = {
  status: "empty",
  total_actions: 0,
  successful_actions: 0,
  success_rate: 0,
  average_load_reduction: 0,
  average_risk_reduction: 0,
};


const fallbackLatencyMetrics: LatencyMetrics = {
  sample_count: 0,
  avg_latency_ms: null,
  min_latency_ms: null,
  max_latency_ms: null,
  median_latency_ms: null,
};


function formatHealthStatus(status: string): string {
  if (!status) {
    return "Unknown";
  }

  return status.charAt(0).toUpperCase() + status.slice(1);
}


function getStatusColor(status: string): string {
  if (status === "healthy") {
    return "text-green-400";
  }

  if (status === "warning") {
    return "text-yellow-400";
  }

  if (status === "fault" || status === "critical") {
    return "text-red-400";
  }

  return "text-slate-400";
}


function getStatusBorder(status: string): string {
  if (status === "healthy") {
    return "border-green-500/50";
  }

  if (status === "warning") {
    return "border-yellow-500/50";
  }

  if (status === "fault" || status === "critical") {
    return "border-red-500/50";
  }

  return "border-slate-800";
}


function buildLoadChartData(telemetry: TelemetryRecord[]): LoadChartData[] {
  return telemetry
    .slice()
    .sort((left, right) => {
      const leftTime = Date.parse(left.database_written_at ?? left.timestamp);
      const rightTime = Date.parse(right.database_written_at ?? right.timestamp);
      return leftTime - rightTime;
    })
    .map((item) => ({
      time: formatDisplayTime(item),
      fullTimestamp: formatDisplayTimestamp(item),
      load: item.load,
    }));
}


function formatRiskLevel(level: string): string {
  if (!level) {
    return "Unknown";
  }

  return level
    .replace("_", " ")
    .split(" ")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}


function getRiskColor(level: string): string {
  if (level === "high") {
    return "text-red-400";
  }

  if (level === "medium") {
    return "text-yellow-400";
  }

  if (level === "low") {
    return "text-green-400";
  }

  return "text-slate-400";
}


function getRiskBorder(level: string): string {
  if (level === "high") {
    return "border-red-500/50";
  }

  if (level === "medium") {
    return "border-yellow-500/50";
  }

  if (level === "low") {
    return "border-green-500/50";
  }

  return "border-slate-800";
}


function getEffectivenessColor(effectiveness: string): string {
  if (effectiveness === "successful") {
    return "text-green-400";
  }

  if (effectiveness === "ineffective") {
    return "text-red-400";
  }

  return "text-yellow-400";
}


function getActionStatusColor(status: string): string {
  if (status === "executed") {
    return "text-green-400";
  }

  if (status === "dry_run") {
    return "text-yellow-400";
  }

  return "text-slate-400";
}


function readSettledValue<T>(
  result: PromiseSettledResult<T>,
  label: string,
  fallbackValue: T,
  failedLabels: string[],
  critical = false,
): T {
  if (result.status === "fulfilled") {
    return result.value;
  }

  failedLabels.push(label);

  if (critical) {
    console.error(`Failed to fetch ${label}:`, result.reason);
  } else {
    console.warn(`Failed to fetch ${label}:`, result.reason);
  }

  return fallbackValue;
}


function formatLatencyMs(value: number | null): string {
  if (value == null) {
    return "N/A";
  }

  if (value === 0) {
    return "<1 ms";
  }

  return `${value} ms`;
}


export default async function Dashboard() {
  let metrics = fallbackMetrics;
  let nodes = fallbackNodes;
  let telemetry = fallbackTelemetry;
  let predictionMetrics = fallbackPredictionMetrics;
  let loadBalancingActions = fallbackLoadBalancingActions;
  let latestLoadBalancingImpact: LoadBalancingImpact | null = null;
  let loadBalancingSummary = fallbackLoadBalancingSummary;
  let latencyMetrics = fallbackLatencyMetrics;
  let faults = fallbackFaults;
  const criticalFailures: string[] = [];
  const optionalFailures: string[] = [];
  let apiError = false;

  const [
    metricsResponse,
    nodesResponse,
    telemetryResponse,
    predictionMetricsResponse,
    loadBalancingActionsResponse,
    latestLoadBalancingImpactResponse,
    loadBalancingSummaryResponse,
    latencyMetricsResponse,
    faultsResponse,
  ] = await Promise.allSettled([
    api.getDashboardMetrics(),
    api.getNodes(),
    api.getTelemetry(25),
    api.getPredictionMetrics(),
    api.getLoadBalancingActions(8),
    api.getLatestLoadBalancingImpact(),
    api.getLoadBalancingSummary(),
    api.getLatencyMetrics(),
    api.getFaults(100),
  ]);

  metrics = readSettledValue(
    metricsResponse,
    "dashboard metrics",
    fallbackMetrics,
    criticalFailures,
    true,
  );
  nodes = readSettledValue(
    nodesResponse,
    "node status",
    fallbackNodes,
    criticalFailures,
    true,
  );
  telemetry = readSettledValue(
    telemetryResponse,
    "telemetry feed",
    fallbackTelemetry,
    criticalFailures,
    true,
  );
  predictionMetrics = readSettledValue(
    predictionMetricsResponse,
    "prediction metrics",
    fallbackPredictionMetrics,
    optionalFailures,
  );
  loadBalancingActions = readSettledValue(
    loadBalancingActionsResponse,
    "load balancing history",
    fallbackLoadBalancingActions,
    optionalFailures,
  );
  latestLoadBalancingImpact = readSettledValue(
    latestLoadBalancingImpactResponse,
    "latest load balancing impact",
    null,
    optionalFailures,
  );
  loadBalancingSummary = readSettledValue(
    loadBalancingSummaryResponse,
    "load balancing summary",
    fallbackLoadBalancingSummary,
    optionalFailures,
  );
  latencyMetrics = readSettledValue(
    latencyMetricsResponse,
    "latency metrics",
    fallbackLatencyMetrics,
    optionalFailures,
  );
  faults = readSettledValue(
    faultsResponse,
    "fault history",
    fallbackFaults,
    optionalFailures,
  );
  apiError = criticalFailures.length > 0;

  const loadChartData = buildLoadChartData(telemetry);
  const telemetryFreshness = getTelemetryFreshness(
    telemetry[0]?.timestamp,
    new Date(),
    telemetry[0]?.database_written_at,
  );
  const latencyValues = [
    latencyMetrics.avg_latency_ms,
    latencyMetrics.min_latency_ms,
    latencyMetrics.max_latency_ms,
    latencyMetrics.median_latency_ms,
  ];
  const hasLatencyValues = latencyValues.some((value) => (value ?? 0) > 0);
  const hasLoadBalancingActions = loadBalancingSummary.total_actions > 0;

  return (
    <div className="flex min-h-screen bg-slate-950 text-white">
      <Sidebar />

      <main className="flex-1 p-8">
        <Navbar />

        <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between mb-8">
          <div>
            <h1 className="text-4xl font-bold mb-2">
              Dashboard
            </h1>

            <p className="text-slate-400">
              V.E.N.U.S Monitoring & Load Management System
            </p>
          </div>

          <div className="flex flex-col items-start md:items-end gap-2">
            <AutoRefreshControls label="Refresh Dashboard" />
            <LiveUpdateBanner listenTo={["telemetry", "prediction", "fault", "load_balancing"]} />
          </div>
        </div>

        <LiveAnalysisCard
          title="Live Grid Analysis"
          headline={
            telemetryFreshness.isStale
              ? "Waiting for fresh telemetry"
              : "Real-time monitoring active"
          }
          subtext={
            telemetryFreshness.isStale
              ? "Latest telemetry is stale; live analysis will update when new events arrive."
              : `Fresh telemetry received ${telemetryFreshness.dataAge} ago. Active faults: ${metrics.active_faults} (active window) vs historical fault records: ${faults.length}.`
          }
          isStale={telemetryFreshness.isStale}
          metrics={[
            { label: "Avg Load (latest)", value: `${metrics.avg_load}%` },
            { label: "Grid Health", value: formatHealthStatus(metrics.system_health) },
            {
              label: "Predicted Faults (latest)",
              value: String(predictionMetrics.predicted_faults),
            },
            { label: "AI Prediction Confidence", value: `${predictionMetrics.risk_score}%` },
          ]}
        />

        {apiError && (
          <div className="mb-6 rounded-xl border border-red-500/40 bg-red-500/10 p-4 text-red-300">
            <p className="font-semibold">Unable to load dashboard data</p>
            <p className="text-sm mt-1">
              Core dashboard feeds are unavailable ({criticalFailures.join(", ")}). The page is showing fallback values until the backend recovers.
            </p>
          </div>
        )}

        {optionalFailures.length > 0 && (
          <div className="mb-6 rounded-xl border border-yellow-500/40 bg-yellow-500/10 p-4 text-yellow-200">
            <p className="font-semibold">Some supplementary insights are temporarily unavailable</p>
            <p className="text-sm mt-1">
              Optional sections could not be loaded ({optionalFailures.join(", ")}). Core dashboard monitoring is still live.
            </p>
          </div>
        )}

        {latencyMetrics.sample_count > 0 && hasLatencyValues && (
          <section className="mb-8">
            <h2 className="text-xl font-semibold mb-3 text-slate-300">
              End-to-End Latency Metrics
            </h2>

            <div className="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden overflow-x-auto">
              <table className="w-full border-collapse text-sm">
                <thead>
                  <tr className="bg-slate-800">
                    <th className="p-3 text-left border border-slate-700 text-slate-300">
                      Samples
                    </th>

                    <th className="p-3 text-left border border-slate-700 text-slate-300">
                      Avg Latency
                    </th>

                    <th className="p-3 text-left border border-slate-700 text-slate-300">
                      Min Latency
                    </th>

                    <th className="p-3 text-left border border-slate-700 text-slate-300">
                      Max Latency
                    </th>

                    <th className="p-3 text-left border border-slate-700 text-slate-300">
                      Median Latency
                    </th>
                  </tr>
                </thead>

                <tbody>
                  <tr>
                    <td className="p-3 border border-slate-700">
                      {latencyMetrics.sample_count}
                    </td>

                    <td className="p-3 border border-slate-700">
                      {formatLatencyMs(latencyMetrics.avg_latency_ms)}
                    </td>

                    <td className="p-3 border border-slate-700">
                      {formatLatencyMs(latencyMetrics.min_latency_ms)}
                    </td>

                    <td className="p-3 border border-slate-700">
                      {formatLatencyMs(latencyMetrics.max_latency_ms)}
                    </td>

                    <td className="p-3 border border-slate-700">
                      {formatLatencyMs(latencyMetrics.median_latency_ms)}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
        )}

        {/* Main Metrics */}
        <section>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
            <MetricCard
              title="Total Nodes"
              value={String(metrics.total_nodes)}
              unitLabel="substations"
              formulaHint="Count of distinct substations in telemetry"
            />

            <MetricCard
              title="Active Faults"
              value={String(metrics.active_faults)}
              unitLabel="fault events"
              formulaHint="Fault events with timestamp inside ACTIVE_FAULT_WINDOW_MINUTES"
            />

            <MetricCard
              title="Average Load"
              value={`${metrics.avg_load}%`}
              unitLabel="% load"
              formulaHint="Average(load) across latest telemetry records"
            />

            <div
              className={`bg-slate-900 rounded-xl p-6 border ${getStatusBorder(
                metrics.system_health
              )}`}
            >
              <h3 className="text-slate-400">
                Grid Health
              </h3>

              <p
                className={`text-4xl font-bold mt-4 ${getStatusColor(
                  metrics.system_health
                )}`}
              >
                {formatHealthStatus(metrics.system_health)}
              </p>

              <p className="text-slate-500 text-sm mt-2">
                Based on recent active faults only
              </p>
            </div>
          </div>
        </section>

        {/* AI Intelligence */}
        <section className="mt-10">
          <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-3 mb-5">
            <div>
              <h2 className="text-2xl font-bold">
                AI Risk Intelligence
              </h2>

              <p className="text-slate-400 text-sm mt-1">
                Predictive fault analysis generated by the V.E.N.U.S AI engine
              </p>
            </div>

            <div className="rounded-full bg-blue-500/10 border border-blue-500/30 px-4 py-2 text-blue-300 text-sm">
              Isolation Forest + XGBoost
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-slate-900 rounded-xl p-6 border border-cyan-500/40 min-h-[150px]">
              <div className="flex items-center justify-between">
                <h3 className="text-slate-400">
                  Predicted Faults
                </h3>

                <span className="text-cyan-400 text-sm">
                  AI
                </span>
              </div>

              <p className="text-4xl font-bold mt-4 text-cyan-400">
                {predictionMetrics.predicted_faults}
              </p>

              <p className="text-slate-500 text-sm mt-3">
                Latest non-normal predictions detected by the model
              </p>
            </div>

            <div className="bg-slate-900 rounded-xl p-6 border border-yellow-500/40 min-h-[150px]">
              <div className="flex items-center justify-between">
                <h3 className="text-slate-400">
                  AI Prediction Confidence
                </h3>

                <span className="text-yellow-400 text-sm">
                  Confidence
                </span>
              </div>

              <p className="text-4xl font-bold mt-4 text-yellow-400">
                {predictionMetrics.risk_score}%
              </p>

              <p className="text-slate-500 text-sm mt-3">
                Average confidence across latest per-substation predictions
              </p>
            </div>

            <div
              className={`bg-slate-900 rounded-xl p-6 border min-h-[150px] ${getRiskBorder(
                predictionMetrics.system_risk_level
              )}`}
            >
              <div className="flex items-center justify-between">
                <h3 className="text-slate-400">
                  System Risk Level
                </h3>

                <span className={getRiskColor(predictionMetrics.system_risk_level)}>
                  Live
                </span>
              </div>

              <p
                className={`text-4xl font-bold mt-4 ${getRiskColor(
                  predictionMetrics.system_risk_level
                )}`}
              >
                {formatRiskLevel(predictionMetrics.system_risk_level)}
              </p>

              <p className="text-slate-500 text-sm mt-3">
                Overall predicted risk based on anomaly and fault outputs
              </p>
            </div>
          </div>
        </section>

        {/* Autonomous Load Balancing */}
        <section className="mt-10">
          <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-3 mb-5">
            <div>
              <h2 className="text-2xl font-bold">
                Autonomous Load Balancing
              </h2>

              <p className="text-slate-400 text-sm mt-1">
                Closed-loop operational decisions made by the V.E.N.U.S balancing engine
              </p>
            </div>

            <div className="rounded-full bg-emerald-500/10 border border-emerald-500/30 px-4 py-2 text-emerald-300 text-sm">
              Decision Engine Active
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
            <div className="bg-slate-900 rounded-xl p-6 border border-emerald-500/40">
              <h3 className="text-slate-400">
                Total Actions
              </h3>

              <p className={`mt-4 font-bold text-emerald-400 ${hasLoadBalancingActions ? "text-4xl" : "text-2xl"}`}>
                {hasLoadBalancingActions
                  ? loadBalancingSummary.total_actions
                  : "No actions yet"}
              </p>

              <p className="text-slate-500 text-sm mt-2">
                {hasLoadBalancingActions
                  ? "Recent balancing decisions"
                  : "Load balancing history will appear here once recommendations run"}
              </p>
            </div>

            <div className="bg-slate-900 rounded-xl p-6 border border-green-500/40">
              <h3 className="text-slate-400">
                Success Rate
              </h3>

              <p className={`mt-4 font-bold text-green-400 ${hasLoadBalancingActions ? "text-4xl" : "text-2xl"}`}>
                {hasLoadBalancingActions
                  ? `${loadBalancingSummary.success_rate}%`
                  : "Awaiting decisions"}
              </p>

              <p className="text-slate-500 text-sm mt-2">
                {hasLoadBalancingActions
                  ? "Effective closed-loop actions"
                  : "Success metrics will update after the first executed action"}
              </p>
            </div>

            <div className="bg-slate-900 rounded-xl p-6 border border-cyan-500/40">
              <h3 className="text-slate-400">
                Avg Load Reduction
              </h3>

              <p className={`mt-4 font-bold text-cyan-400 ${hasLoadBalancingActions ? "text-4xl" : "text-2xl"}`}>
                {hasLoadBalancingActions
                  ? `${loadBalancingSummary.average_load_reduction}%`
                  : "Pending"}
              </p>

              <p className="text-slate-500 text-sm mt-2">
                {hasLoadBalancingActions
                  ? "Source node load decrease"
                  : "Average reduction appears after completed balancing actions"}
              </p>
            </div>

            <div className="bg-slate-900 rounded-xl p-6 border border-purple-500/40">
              <h3 className="text-slate-400">
                Avg Risk Reduction
              </h3>

              <p className={`mt-4 font-bold text-purple-400 ${hasLoadBalancingActions ? "text-4xl" : "text-2xl"}`}>
                {hasLoadBalancingActions
                  ? loadBalancingSummary.average_risk_reduction
                  : "Awaiting impact"}
              </p>

              <p className="text-slate-500 text-sm mt-2">
                {hasLoadBalancingActions
                  ? "Risk score improvement"
                  : "Impact metrics will appear after a recorded balancing result"}
              </p>
            </div>
          </div>

          {latestLoadBalancingImpact ? (
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
              <div className="xl:col-span-2 bg-slate-900 rounded-xl p-6 border border-slate-800">
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <h3 className="text-xl font-bold">
                      Latest Balancing Action
                    </h3>

                    <p className="text-slate-400 text-sm mt-1">
                      Substation {latestLoadBalancingImpact.source_node} → Substation {latestLoadBalancingImpact.target_node}
                    </p>
                  </div>

                  <span
                    className={`font-semibold ${getEffectivenessColor(
                      latestLoadBalancingImpact.effectiveness
                    )}`}
                  >
                    {formatRiskLevel(latestLoadBalancingImpact.effectiveness)}
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="bg-slate-800 rounded-lg p-5">
                    <p className="text-slate-400 text-sm">
                      Load Shifted
                    </p>

                    <p className="text-3xl font-bold mt-2 text-cyan-400">
                      {latestLoadBalancingImpact.load_shifted}%
                    </p>

                    <p className="text-slate-500 text-xs mt-2">
                      From Substation {latestLoadBalancingImpact.source_node} to {latestLoadBalancingImpact.target_node}
                    </p>
                  </div>

                  <div className="bg-slate-800 rounded-lg p-5">
                    <p className="text-slate-400 text-sm">
                      Source Load
                    </p>

                    <p className="text-3xl font-bold mt-2">
                      {latestLoadBalancingImpact.before.source_load}% →{" "}
                      <span className="text-green-400">
                        {latestLoadBalancingImpact.after.source_load}%
                      </span>
                    </p>

                    <p className="text-slate-500 text-xs mt-2">
                      Reduced by {latestLoadBalancingImpact.impact.source_load_reduction_percent}%
                    </p>
                  </div>

                  <div className="bg-slate-800 rounded-lg p-5">
                    <p className="text-slate-400 text-sm">
                      Risk Score
                    </p>

                    <p className="text-3xl font-bold mt-2">
                      {latestLoadBalancingImpact.before.risk_score} →{" "}
                      <span className="text-green-400">
                        {latestLoadBalancingImpact.after.risk_score}
                      </span>
                    </p>

                    <p className="text-slate-500 text-xs mt-2">
                      Reduced by {latestLoadBalancingImpact.impact.risk_reduction_percent}%
                    </p>
                  </div>
                </div>

                <div className="mt-5 bg-slate-800 rounded-lg p-5">
                  <p className="text-slate-400 text-sm mb-2">
                    Decision Reason
                  </p>

                  <p className="text-slate-200">
                    {latestLoadBalancingImpact.trigger_reason}
                  </p>

                  <p className="text-slate-500 text-sm mt-3">
                    {latestLoadBalancingImpact.decision_notes}
                  </p>
                </div>
              </div>

              <div className="bg-slate-900 rounded-xl p-6 border border-slate-800">
                <h3 className="text-xl font-bold mb-5">
                  Before / After Impact
                </h3>

                <div className="space-y-4">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                    <span className="text-slate-400">Source Node</span>
                    <span>Substation {latestLoadBalancingImpact.source_node}</span>
                  </div>

                  <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                    <span className="text-slate-400">Target Node</span>
                    <span>Substation {latestLoadBalancingImpact.target_node}</span>
                  </div>

                  <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                    <span className="text-slate-400">Target Load</span>
                    <span>
                      {latestLoadBalancingImpact.before.target_load}% →{" "}
                      {latestLoadBalancingImpact.after.target_load}%
                    </span>
                  </div>

                  <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                    <span className="text-slate-400">Execution Mode</span>
                    <span>{formatRiskLevel(latestLoadBalancingImpact.execution_mode)}</span>
                  </div>

                  <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                    <span className="text-slate-400">Status</span>
                    <span
                      className={getActionStatusColor(
                        latestLoadBalancingImpact.action_status
                      )}
                    >
                      {formatRiskLevel(latestLoadBalancingImpact.action_status)}
                    </span>
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Timestamp</span>
                    <span className="text-right text-sm">
                      {formatDisplayTimestamp({
                        created_at: latestLoadBalancingImpact.created_at,
                      })}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-slate-900 rounded-xl p-6 border border-slate-800">
              <p className="text-slate-400">
                No load balancing actions available yet. Trigger one from the backend API to populate this section.
              </p>
            </div>
          )}
          <LoadBalancingControls />

          <div className="mt-6 bg-slate-900 rounded-xl border border-slate-800 overflow-hidden">
            <div className="p-6 border-b border-slate-800">
              <h3 className="text-xl font-bold">
                Balancing History
              </h3>

              <p className="text-slate-400 text-sm mt-1">
                Recent autonomous and manual load redistribution actions
              </p>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full border-collapse">
                <thead>
                  <tr className="bg-slate-800">
                    <th className="p-4 text-left border border-slate-700">Action</th>
                    <th className="p-4 text-left border border-slate-700">Load Shifted</th>
                    <th className="p-4 text-left border border-slate-700">Source Load</th>
                    <th className="p-4 text-left border border-slate-700">Target Load</th>
                    <th className="p-4 text-left border border-slate-700">Risk</th>
                    <th className="p-4 text-left border border-slate-700">Mode</th>
                    <th className="p-4 text-left border border-slate-700">Status</th>
                    <th className="p-4 text-left border border-slate-700">Time</th>
                  </tr>
                </thead>

                <tbody>
                  {loadBalancingActions.length === 0 ? (
                    <tr>
                      <td
                        colSpan={8}
                        className="p-6 text-center text-slate-400 border border-slate-700"
                      >
                        No balancing history available.
                      </td>
                    </tr>
                  ) : (
                    loadBalancingActions.map((action) => (
                      <tr
                        key={action.id}
                        className="hover:bg-slate-800 transition"
                      >
                        <td className="p-4 border border-slate-700">
                          {action.source_node} → {action.target_node}
                        </td>

                        <td className="p-4 border border-slate-700 text-cyan-400 font-semibold">
                          {action.load_shifted}%
                        </td>

                        <td className="p-4 border border-slate-700">
                          {action.source_load_before}% → {action.source_load_after}%
                        </td>

                        <td className="p-4 border border-slate-700">
                          {action.target_load_before}% → {action.target_load_after}%
                        </td>

                        <td className="p-4 border border-slate-700">
                          {action.risk_before} → {action.risk_after}
                        </td>

                        <td className="p-4 border border-slate-700">
                          {formatRiskLevel(action.execution_mode)}
                        </td>

                        <td
                          className={`p-4 border border-slate-700 font-semibold ${getEffectivenessColor(
                            action.effectiveness
                          )}`}
                        >
                          {formatRiskLevel(action.effectiveness)}
                        </td>

                        <td className="p-4 border border-slate-700 text-sm text-slate-300">
                          {formatDisplayTimestamp({
                            created_at: action.created_at,
                          })}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </section>

        <DecisionLogPanel />

        {/* Load Chart */}
        <section className="mt-10">
          <LoadChart data={loadChartData} />
        </section>

        {/* System Overview */}
        <section className="mt-10 bg-slate-900 rounded-xl p-6 border border-slate-800">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-2xl font-bold">
                System Overview
              </h2>

              <p className="text-slate-400 text-sm mt-1">
                Latest status of active substations
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {nodes.map((node) => (
              <div
                key={node.node}
                className={`bg-slate-800 rounded-xl p-5 border ${getStatusBorder(
                  node.status
                )}`}
              >
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-semibold">
                    Substation {node.node}
                  </h3>

                  <span
                    className={`text-sm font-semibold ${getStatusColor(
                      node.status
                    )}`}
                  >
                    {formatHealthStatus(node.status)}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-4 mt-5">
                  <div>
                    <p className="text-slate-500 text-xs">
                      Load
                    </p>

                    <p className="font-semibold mt-1">
                      {node.load !== null ? `${node.load}%` : "N/A"}
                    </p>
                  </div>

                  <div>
                    <p className="text-slate-500 text-xs">
                      Voltage
                    </p>

                    <p className="font-semibold mt-1">
                      {node.voltage !== null ? `${node.voltage} V` : "N/A"}
                    </p>
                  </div>

                  <div>
                    <p className="text-slate-500 text-xs">
                      Temperature
                    </p>

                    <p className="font-semibold mt-1">
                      {node.temperature !== null ? `${node.temperature} °C` : "N/A"}
                    </p>
                  </div>

                  <div>
                    <p className="text-slate-500 text-xs">
                      Frequency
                    </p>

                    <p className="font-semibold mt-1">
                      {node.frequency !== null ? `${node.frequency} Hz` : "N/A"}
                    </p>
                  </div>
                </div>

                <p className="text-slate-500 text-xs mt-5">
                  Last updated:{" "}
                  {formatDisplayTimestamp({ timestamp: node.last_updated })}
                </p>
              </div>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}