import Sidebar from "../../components/Sidebar";
import Navbar from "../../components/Navbar";
import LoadChart, { LoadChartData } from "../../components/LoadChart";
import AutoRefreshControls from "../../components/AutoRefreshControls";
import LiveUpdateBanner from "../../components/LiveUpdateBanner";
import LiveAnalysisCard from "../../components/LiveAnalysisCard";
import LoadBalancingStatusSummary from "../../components/LoadBalancingStatusSummary";
import { api, NodeStatus, TelemetryRecord } from "../../services/api";
import { getTelemetryFreshness } from "../../services/telemetryFreshness";
import { formatDisplayTime } from "../../services/timestamps";

export const dynamic = "force-dynamic";


const fallbackNodes: NodeStatus[] = [];
const fallbackTelemetry: TelemetryRecord[] = [];


function buildLoadChartData(telemetry: TelemetryRecord[]): LoadChartData[] {
  return telemetry
    .slice()
    .reverse()
    .map((item) => ({
      time: formatDisplayTime(item),
      load: item.load,
    }));
}


export default async function LoadBalancing() {
  let nodes = fallbackNodes;
  let telemetry = fallbackTelemetry;
  let apiError = false;

  try {
    const [nodesResponse, telemetryResponse] = await Promise.all([
      api.getNodes(),
      api.getTelemetry(25),
    ]);

    nodes = nodesResponse;
    telemetry = telemetryResponse;
  } catch (error) {
    console.error("Failed to fetch load balancing data:", error);
    apiError = true;
  }

  const loadChartData = buildLoadChartData(telemetry);
  const telemetryFreshness = getTelemetryFreshness(
    telemetry[0]?.timestamp,
    new Date(),
    telemetry[0]?.database_written_at,
  );

  return (
    <div className="flex min-h-screen bg-slate-950 text-white">
      <Sidebar />

      <main className="flex-1 p-8">
        <Navbar />

        <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between mb-8">
          <div>
            <h1 className="text-4xl font-bold mb-2">
              Load Balancing
            </h1>

            <p className="text-slate-400">
              V.E.N.U.S power distribution monitoring from latest backend records
            </p>
          </div>

          <div className="flex flex-col items-start md:items-end gap-2">
            <AutoRefreshControls label="Refresh Load Balancing" />
            <LiveUpdateBanner listenTo={["telemetry", "load_balancing"]} />
          </div>
        </div>

        <LiveAnalysisCard
          title="Live Load Analysis"
          headline={
            telemetryFreshness.isStale
              ? "Waiting for fresh data"
              : "Load distribution active"
          }
          subtext={
            telemetryFreshness.isStale
              ? "Load data is stale; analysis will update when new telemetry arrives."
              : `Monitoring ${nodes.length} node${nodes.length !== 1 ? "s" : ""} · updated ${telemetryFreshness.dataAge} ago.`
          }
          isStale={telemetryFreshness.isStale}
          metrics={[
            { label: "Active Nodes", value: String(nodes.length) },
            {
              label: "Latest Load",
              value:
                telemetry[0] != null ? `${telemetry[0].load}%` : "N/A",
            },
            {
              label: "Peak Load",
              value:
                telemetry.length > 0
                  ? `${Math.max(...telemetry.map((t) => t.load)).toFixed(1)}%`
                  : "N/A",
            },
            {
              label: "Healthy Nodes",
              value: String(
                nodes.filter((n) => n.status === "healthy").length,
              ),
            },
          ]}
        />

        {apiError && (
          <div className="mb-6 rounded-xl border border-red-500/40 bg-red-500/10 p-4 text-red-300">
            <p className="font-semibold">Unable to load load balancing data</p>
            <p className="text-sm mt-1">
              The backend could not be reached. Make sure the V.E.N.U.S backend is running, then refresh the page.
            </p>
          </div>
        )}

        <LoadBalancingStatusSummary nodes={nodes} />

        <LoadChart data={loadChartData} />
      </main>
    </div>
  );
}