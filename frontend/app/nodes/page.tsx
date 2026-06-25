import Sidebar from "../../components/Sidebar";
import Navbar from "../../components/Navbar";
import StatusBadge from "../../components/StatusBadge";
import AutoRefreshControls from "../../components/AutoRefreshControls";
import { api, NodeStatus } from "../../services/api";
import { getTelemetryFreshness } from "../../services/telemetryFreshness";


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

  try {
    nodes = await api.getNodes();
  } catch (error) {
    console.error("Failed to fetch node status data:", error);
  }

  const latestNodeTimestamp = nodes
    .map((node) => node.last_updated)
    .filter((timestamp): timestamp is string => Boolean(timestamp))
    .sort((a, b) => new Date(b).getTime() - new Date(a).getTime())[0];

  const telemetryFreshness = getTelemetryFreshness(latestNodeTimestamp);

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

          <AutoRefreshControls label="Refresh Nodes" />
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
                  Last Updated
                </th>
              </tr>
            </thead>

            <tbody>
              {nodes.length === 0 ? (
                <tr>
                  <td
                    colSpan={7}
                    className="p-6 border border-slate-700 text-center text-slate-400"
                  >
                    No node status records available.
                  </td>
                </tr>
              ) : (
                nodes.map((node) => (
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