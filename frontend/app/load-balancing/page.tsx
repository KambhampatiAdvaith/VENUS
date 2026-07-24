import Sidebar from "../../components/Sidebar";
import Navbar from "../../components/Navbar";
import LoadChart, { LoadChartData } from "../../components/LoadChart";
import AutoRefreshControls from "../../components/AutoRefreshControls";
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

          <AutoRefreshControls label="Refresh Load Balancing" />
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