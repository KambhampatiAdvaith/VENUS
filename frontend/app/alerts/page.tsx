import Sidebar from "../../components/Sidebar";
import Navbar from "../../components/Navbar";
import StatusBadge from "../../components/StatusBadge";
import AutoRefreshControls from "../../components/AutoRefreshControls";
import LiveUpdateBanner from "../../components/LiveUpdateBanner";
import { api, DashboardMetrics, FaultRecord } from "../../services/api";

export const dynamic = "force-dynamic";


const fallbackFaults: FaultRecord[] = [];
const fallbackMetrics: DashboardMetrics = {
  total_nodes: 20,
  active_faults: 0,
  avg_load: 0,
  system_health: "unknown",
};


function formatFaultType(faultType: string): string {
  return faultType
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}


function formatTimestamp(timestamp: string): string {
  return new Date(timestamp).toLocaleString();
}


function formatSeverity(severity: string): string {
  return severity.charAt(0).toUpperCase() + severity.slice(1);
}


export default async function Alerts() {
  let faults = fallbackFaults;
  let metrics = fallbackMetrics;
  let apiError = false;

  try {
    [faults, metrics] = await Promise.all([
      api.getFaults(100),
      api.getDashboardMetrics(),
    ]);
  } catch (error) {
    console.error("Failed to fetch fault data:", error);
    apiError = true;
  }

  const activeFaultCount = Math.min(metrics.active_faults, faults.length);
  const activeFaults = faults.slice(0, activeFaultCount);
  const historicalFaults = faults.slice(activeFaultCount);

  return (
    <div className="flex min-h-screen bg-slate-950 text-white">
      <Sidebar />

      <main className="flex-1 p-8">
        <Navbar />

        <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between mb-8">
          <div>
            <h1 className="text-4xl font-bold mb-2">
              Grid Events & AI Alerts
            </h1>

            <p className="text-slate-400">
              Active faults come from the backend active-fault window; historical events remain visible for audit.
            </p>
          </div>

          <div className="flex flex-col items-start md:items-end gap-2">
            <AutoRefreshControls label="Refresh Alerts" />
            <LiveUpdateBanner listenTo={["fault", "prediction"]} />
          </div>
        </div>

        {apiError && (
          <div className="mb-6 rounded-xl border border-red-500/40 bg-red-500/10 p-4 text-red-300">
            <p className="font-semibold">Unable to load alerts</p>
            <p className="text-sm mt-1">
              The backend could not be reached. Make sure the V.E.N.U.S backend is running, then refresh the page.
            </p>
          </div>
        )}

        <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-3">
          <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4">
            <p className="text-sm text-red-200">Active faults (window)</p>
            <p className="mt-2 text-3xl font-bold text-red-300">{metrics.active_faults}</p>
          </div>
          <div className="rounded-xl border border-slate-700 bg-slate-900 p-4">
            <p className="text-sm text-slate-300">Historical faults</p>
            <p className="mt-2 text-3xl font-bold">{historicalFaults.length}</p>
          </div>
          <div className="rounded-xl border border-slate-700 bg-slate-900 p-4">
            <p className="text-sm text-slate-300">Severity guide</p>
            <p className="mt-2 text-xs text-slate-400">
              Critical: immediate intervention · High: urgent inspection · Medium/Low: monitor trend
            </p>
          </div>
        </div>

        <div className="space-y-4">
          {faults.length === 0 ? (
            <div className="bg-slate-900 p-5 rounded-xl border border-slate-800 text-slate-400">
              <p className="font-semibold text-slate-300">No fault alerts yet</p>
              <p className="text-sm mt-1">
                Alerts appear here when a fault event is detected. To generate one, inject a fault via the simulator:
              </p>
              <p className="text-sm mt-2 font-mono text-slate-500">
                POST /telemetry/simulate/fault
              </p>
            </div>
          ) : (
            <>
              <div>
                <h2 className="mb-3 text-xl font-semibold text-red-300">Active Alerts</h2>
                {activeFaults.length === 0 ? (
                  <p className="text-sm text-slate-400">No active alerts in the current fault window.</p>
                ) : (
                  activeFaults.map((fault) => (
                    <div
                      key={fault.id}
                      className="mb-3 bg-slate-900 p-5 rounded-xl flex justify-between gap-6 border border-red-500/30"
                    >
                      <div>
                        <h2 className="text-lg font-semibold">
                          {formatFaultType(fault.fault_type)}
                        </h2>
                        <p className="text-slate-400">Substation {fault.substation}</p>
                        <p className="text-slate-500 text-sm mt-1">{formatTimestamp(fault.timestamp)}</p>
                      </div>
                      <StatusBadge status={formatSeverity(fault.severity)} />
                    </div>
                  ))
                )}
              </div>

              <div>
                <h2 className="mb-3 text-xl font-semibold text-slate-200">Historical Alerts</h2>
                {historicalFaults.length === 0 ? (
                  <p className="text-sm text-slate-400">No historical alerts outside the current active window.</p>
                ) : (
                  historicalFaults.map((fault) => (
                    <div
                      key={fault.id}
                      className="mb-3 bg-slate-900 p-5 rounded-xl flex justify-between gap-6 border border-slate-800"
                    >
                      <div>
                        <h2 className="text-lg font-semibold">
                          {formatFaultType(fault.fault_type)}
                        </h2>
                        <p className="text-slate-400">Substation {fault.substation}</p>
                        <p className="text-slate-500 text-sm mt-1">{formatTimestamp(fault.timestamp)}</p>
                      </div>
                      <StatusBadge status={formatSeverity(fault.severity)} />
                    </div>
                  ))
                )}
              </div>
            </>
          )}
        </div>
      </main>
    </div>
  );
}