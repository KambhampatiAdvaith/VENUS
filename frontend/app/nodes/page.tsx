import Sidebar from "../../components/Sidebar";
import Navbar from "../../components/Navbar";
import StatusBadge from "../../components/StatusBadge";
import AutoRefreshControls from "../../components/AutoRefreshControls";
import LiveUpdateBanner from "../../components/LiveUpdateBanner";
import LiveAnalysisCard from "../../components/LiveAnalysisCard";
import { api, NodeStatus } from "../../services/api";
import { getTelemetryFreshness } from "../../services/telemetryFreshness";

export const dynamic = "force-dynamic";


const fallbackNodes: NodeStatus[] = [];


function formatStatus(status: string): string {
  if (status === "healthy") {
    return "Online";
  }

  if (status === "warning") {
    return "Warning";
  }

  if (status === "fault" || status === "critical") {
    return "Critical";
  }

  return "Unknown";
}


function formatTimestamp(timestamp: string | null): string {
  if (!timestamp) {
    return "N/A";
  }

  return new Date(timestamp).toLocaleString();
}


export default async function Nodes() {
  let nodes = fallbackNodes;
  let apiError = false;

  try {
    nodes = await api.getNodes();
  } catch (error) {
    console.error("Failed to fetch node status data:", error);
    apiError = true;
  }

  const latestNodeTimestamp = nodes
    .map((node) => node.last_updated)
    .filter((timestamp): timestamp is string => Boolean(timestamp))
    .sort((a, b) => new Date(b).getTime() - new Date(a).getTime())[0];

  const telemetryFreshness = getTelemetryFreshness(latestNodeTimestamp);
  const orderedNodes = nodes.slice().sort(
    (left, right) => {
      const leftNumber = Number(left.node);
      const rightNumber = Number(right.node);

      if (Number.isNaN(leftNumber) || Number.isNaN(rightNumber)) {
        return left.node.localeCompare(right.node);
      }

      return leftNumber - rightNumber;
    },
  );

  return (
    <div className="flex min-h-screen bg-slate-950 text-white">
      <Sidebar />

      <main className="flex-1 p-8">
        <Navbar />

        <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between mb-8">
          <div>
            <h1 className="text-4xl font-bold mb-2">
              Node Status
            </h1>

            <p className="text-slate-400">
              V.E.N.U.S node health and operating parameters from latest telemetry
            </p>
          </div>

          <div className="flex flex-col items-start md:items-end gap-2">
            <AutoRefreshControls label="Refresh Nodes" />
            <LiveUpdateBanner listenTo={["telemetry", "fault"]} />
          </div>
        </div>

        <LiveAnalysisCard
          title="Live Node Health Analysis"
          headline={
            telemetryFreshness.isStale
              ? "Waiting for fresh data"
              : "Node health monitoring active"
          }
          subtext={
            telemetryFreshness.isStale
              ? "Node data is stale; display will update when new telemetry arrives."
              : `Monitoring ${nodes.length}/20 substations · updated ${telemetryFreshness.dataAge} ago. Status uses active-fault window + latest telemetry thresholds.`
          }
          isStale={telemetryFreshness.isStale}
          metrics={[
            {
              label: "Online",
              value: String(
                nodes.filter((n) => n.status === "healthy").length,
              ),
            },
            {
              label: "Warning",
              value: String(
                nodes.filter((n) => n.status === "warning").length,
              ),
            },
            {
              label: "Critical",
              value: String(
                nodes.filter(
                  (n) => n.status === "fault" || n.status === "critical",
                ).length,
              ),
            },
            { label: "Total Substations", value: "20" },
          ]}
        />

        {apiError && (
          <div className="mb-6 rounded-xl border border-red-500/40 bg-red-500/10 p-4 text-red-300">
            <p className="font-semibold">Unable to load node status</p>
            <p className="text-sm mt-1">
              The backend could not be reached. Make sure the V.E.N.U.S backend is running, then refresh the page.
            </p>
          </div>
        )}

        <div className="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="bg-slate-800">
                <th className="p-4 border border-slate-700 text-left">
                  Node
                </th>

                <th className="p-4 border border-slate-700 text-left">
                  Status
                </th>

                <th className="p-4 border border-slate-700 text-left">
                  Load
                </th>

                <th className="p-4 border border-slate-700 text-left">
                  Voltage
                </th>

                <th className="p-4 border border-slate-700 text-left">
                  Temperature
                </th>

                <th className="p-4 border border-slate-700 text-left">
                  Frequency
                </th>

                <th className="p-4 border border-slate-700 text-left">
                  Reason
                </th>

                <th className="p-4 border border-slate-700 text-left">
                  Last Updated
                </th>
              </tr>
            </thead>

            <tbody>
              {nodes.length === 0 ? (
                <tr>
                  <td
                    colSpan={8}
                    className="p-6 border border-slate-700"
                  >
                    <p className="font-semibold text-slate-300">No node status records yet</p>
                    <p className="text-sm mt-1 text-slate-400">
                      Node data is derived from telemetry. Start the simulator to populate node status:
                    </p>
                    <p className="text-sm mt-1 font-mono text-slate-500">
                      POST /telemetry/simulate/normal
                    </p>
                  </td>
                </tr>
              ) : (
                orderedNodes.map((node) => (
                  <tr
                    key={node.node}
                    className="hover:bg-slate-800 transition"
                  >
                    <td className="p-4 border border-slate-700">
                      Substation {node.node}
                    </td>

                    <td className="p-4 border border-slate-700">
                      <StatusBadge status={formatStatus(node.status)} />
                    </td>

                    <td className="p-4 border border-slate-700">
                      {node.load !== null ? `${node.load}%` : "N/A"}
                    </td>

                    <td className="p-4 border border-slate-700">
                      {node.voltage !== null ? `${node.voltage} V` : "N/A"}
                    </td>

                    <td className="p-4 border border-slate-700">
                      {node.temperature !== null
                        ? `${node.temperature} °C`
                        : "N/A"}
                    </td>

                    <td className="p-4 border border-slate-700">
                      {node.frequency !== null
                        ? `${node.frequency} Hz`
                        : "N/A"}
                    </td>

                    <td className="p-4 border border-slate-700 text-sm text-slate-300">
                      {node.reason ?? "Telemetry within thresholds"}
                    </td>

                    <td className="p-4 border border-slate-700 text-sm text-slate-300">
                      {formatTimestamp(node.last_updated)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}