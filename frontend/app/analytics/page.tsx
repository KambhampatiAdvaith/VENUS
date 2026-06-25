import Sidebar from "../../components/Sidebar";
import Navbar from "../../components/Navbar";
import AutoRefreshControls from "../../components/AutoRefreshControls";
import AnalyticsChart from "../../components/AnalyticsChart";
import LoadDistributionChart from "../../components/LoadDistributionChart";
import {
  api,
  DashboardMetrics,
  FaultRecord,
  NodeStatus,
  TelemetryRecord,
} from "../../services/api";
import { getTelemetryFreshness } from "../../services/telemetryFreshness";

export const dynamic = "force-dynamic";


const fallbackTelemetry: TelemetryRecord[] = [];
const fallbackFaults: FaultRecord[] = [];
const fallbackNodes: NodeStatus[] = [];

const fallbackMetrics: DashboardMetrics = {
  total_nodes: 0,
  active_faults: 0,
  avg_load: 0,
  system_health: "unknown",
};


function roundValue(value: number): number {
  return Math.round(value * 100) / 100;
}


function getAverage(values: number[]): number {
  if (values.length === 0) {
    return 0;
  }

  const total = values.reduce((sum, value) => sum + value, 0);
  return roundValue(total / values.length);
}


function getPeakLoad(telemetry: TelemetryRecord[]): number {
  if (telemetry.length === 0) {
    return 0;
  }

  return roundValue(Math.max(...telemetry.map((item) => item.load)));
}


function getEfficiency(nodes: NodeStatus[]): number {
  if (nodes.length === 0) {
    return 0;
  }

  const healthyNodes = nodes.filter((node) => node.status === "healthy").length;
  return roundValue((healthyNodes / nodes.length) * 100);
}


function formatNodeStatus(status: string): string {
  if (status === "healthy") {
    return "Optimal";
  }

  if (status === "warning") {
    return "High Load";
  }

  if (status === "fault" || status === "critical") {
    return "Fault Detected";
  }

  return "Unknown";
}


function getNodeStatusColor(status: string): string {
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


function getMostCommonFault(faults: FaultRecord[]): string {
  if (faults.length === 0) {
    return "None";
  }

  const counts: Record<string, number> = {};

  faults.forEach((fault) => {
    counts[fault.fault_type] = (counts[fault.fault_type] || 0) + 1;
  });

  const mostCommonFault = Object.entries(counts).sort(
    (a, b) => b[1] - a[1]
  )[0][0];

  return mostCommonFault
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}


function getLatestTelemetryTimestamp(telemetry: TelemetryRecord[]): string | undefined {
  return telemetry
    .map((item) => item.timestamp)
    .sort((a, b) => new Date(b).getTime() - new Date(a).getTime())[0];
}


export default async function Analytics() {
  let telemetry = fallbackTelemetry;
  let faults = fallbackFaults;
  let nodes = fallbackNodes;
  let metrics = fallbackMetrics;

  try {
    const [
      telemetryResponse,
      faultsResponse,
      nodesResponse,
      metricsResponse,
    ] = await Promise.all([
      api.getTelemetry(100),
      api.getFaults(100),
      api.getNodes(),
      api.getDashboardMetrics(),
    ]);

    telemetry = telemetryResponse;
    faults = faultsResponse;
    nodes = nodesResponse;
    metrics = metricsResponse;
  } catch (error) {
    console.error("Failed to fetch analytics data:", error);
  }

  const peakLoad = getPeakLoad(telemetry);
  const avgVoltage = getAverage(telemetry.map((item) => item.voltage));
  const efficiency = getEfficiency(nodes);
  const mostCommonFault = getMostCommonFault(faults);
  const telemetryFreshness = getTelemetryFreshness(
    getLatestTelemetryTimestamp(telemetry)
  );

  const analyticsChartData = nodes.map((node) => ({
    zone: `Substation ${node.node}`,
    load: node.load ?? 0,
  }));

  const loadDistributionData = nodes.map((node) => ({
    name: `Substation ${node.node}`,
    value: node.load ?? 0,
  }));

  return (
    <div className="flex min-h-screen bg-slate-950 text-white">
      <Sidebar />

      <main className="flex-1 p-8">
        <Navbar />

        <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between mb-8">
          <div>
            <h1 className="text-4xl font-bold mb-2">
              Analytics Dashboard
            </h1>

            <p className="text-slate-400">
              V.E.N.U.S Performance Analysis from real telemetry and fault data
            </p>
          </div>

          <AutoRefreshControls label="Refresh Analytics" />
        </div>

        <div
          className={`mb-8 rounded-xl border p-4 ${
            telemetryFreshness.isStale
              ? "border-yellow-500/40 bg-yellow-500/10 text-yellow-200"
              : "border-emerald-500/30 bg-emerald-500/10 text-emerald-200"
          }`}
        >
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-2">
            <p className="font-semibold">
              Last telemetry update: {telemetryFreshness.lastTelemetryUpdate}
            </p>

            <p>
              Data age: {telemetryFreshness.dataAge}
            </p>
          </div>

          {telemetryFreshness.isStale ? (
            <p className="mt-2 text-sm">
              Telemetry data is stale.
            </p>
          ) : null}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="bg-slate-900 rounded-xl p-6 border border-slate-800">
            <h3 className="text-slate-400">
              Peak Load
            </h3>

            <p className="text-3xl font-bold mt-2">
              {peakLoad}%
            </p>
          </div>

          <div className="bg-slate-900 rounded-xl p-6 border border-slate-800">
            <h3 className="text-slate-400">
              Avg Voltage
            </h3>

            <p className="text-3xl font-bold mt-2">
              {avgVoltage} V
            </p>
          </div>

          <div className="bg-slate-900 rounded-xl p-6 border border-slate-800">
            <h3 className="text-slate-400">
              Node Efficiency
            </h3>

            <p className="text-3xl font-bold mt-2">
              {efficiency}%
            </p>
          </div>

          <div className="bg-slate-900 rounded-xl p-6 border border-slate-800">
            <h3 className="text-slate-400">
              Active Zones
            </h3>

            <p className="text-3xl font-bold mt-2">
              {metrics.total_nodes}
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <AnalyticsChart data={analyticsChartData} />

          <LoadDistributionChart data={loadDistributionData} />
        </div>

        <div className="mt-8 bg-slate-900 rounded-xl p-6 border border-slate-800">
          <h2 className="text-2xl font-bold mb-4">
            Performance Summary
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {nodes.length === 0 ? (
              <div className="bg-slate-800 rounded-lg p-4 text-slate-400">
                No node analytics available.
              </div>
            ) : (
              nodes.map((node) => (
                <div
                  key={node.node}
                  className="bg-slate-800 rounded-lg p-4"
                >
                  <h3 className="font-semibold">
                    Substation {node.node}
                  </h3>

                  <p className={`${getNodeStatusColor(node.status)} mt-2`}>
                    {formatNodeStatus(node.status)}
                  </p>

                  <p className="text-slate-400 text-sm mt-2">
                    Load: {node.load !== null ? `${node.load}%` : "N/A"}
                  </p>

                  <p className="text-slate-500 text-xs mt-1">
                    Voltage: {node.voltage !== null ? `${node.voltage} V` : "N/A"}
                  </p>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="mt-8 bg-slate-900 rounded-xl p-6 border border-slate-800">
          <h2 className="text-2xl font-bold mb-4">
            Fault Analytics
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-slate-800 rounded-lg p-4">
              <h3 className="text-slate-400">
                Total Fault Records
              </h3>

              <p className="text-2xl font-bold mt-2">
                {faults.length}
              </p>
            </div>

            <div className="bg-slate-800 rounded-lg p-4">
              <h3 className="text-slate-400">
                Active Faults
              </h3>

              <p className="text-2xl font-bold mt-2">
                {metrics.active_faults}
              </p>
            </div>

            <div className="bg-slate-800 rounded-lg p-4">
              <h3 className="text-slate-400">
                Most Common Fault
              </h3>

              <p className="text-2xl font-bold mt-2">
                {mostCommonFault}
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}