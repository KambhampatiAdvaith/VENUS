import Sidebar from "../../components/Sidebar";
import Navbar from "../../components/Navbar";
import AutoRefreshControls from "../../components/AutoRefreshControls";
import LiveUpdateBanner from "../../components/LiveUpdateBanner";
import { api, TelemetryRecord } from "../../services/api";
import { getTelemetryFreshness } from "../../services/telemetryFreshness";
import { formatDisplayTimestamp } from "../../services/timestamps";

export const dynamic = "force-dynamic";


const fallbackTelemetry: TelemetryRecord[] = [];


export default async function Telemetry() {
  let telemetryData = fallbackTelemetry;
  let apiError = false;

  try {
    telemetryData = await api.getTelemetry(100);
  } catch (error) {
    console.error("Failed to fetch telemetry data:", error);
    apiError = true;
  }

  const telemetryFreshness = getTelemetryFreshness(
    telemetryData[0]?.timestamp,
    new Date(),
    telemetryData[0]?.database_written_at,
  );

  return (
    <div className="flex min-h-screen bg-slate-950 text-white">
      <Sidebar />

      <main className="flex-1 p-8">
        <Navbar />

        <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between mb-8">
          <div>
            <h1 className="text-4xl font-bold mb-2">
              Telemetry
            </h1>

            <p className="text-slate-400">
              V.E.N.U.S telemetry monitoring based on latest backend records
            </p>
          </div>

          <div className="flex flex-col items-start md:items-end gap-2">
            <AutoRefreshControls label="Refresh Telemetry" />
            <LiveUpdateBanner listenTo={["telemetry"]} />
          </div>
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
            <p className="font-semibold">Unable to load telemetry</p>
            <p className="text-sm mt-1">
              The backend could not be reached. Make sure the V.E.N.U.S backend is running, then refresh the page.
            </p>
          </div>
        )}

        <div className="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="bg-slate-800">
                <th className="p-4 text-left border border-slate-700">
                  Substation
                </th>

                <th className="p-4 text-left border border-slate-700">
                  Voltage
                </th>

                <th className="p-4 text-left border border-slate-700">
                  Current
                </th>

                <th className="p-4 text-left border border-slate-700">
                  Temperature
                </th>

                <th className="p-4 text-left border border-slate-700">
                  Load
                </th>

                <th className="p-4 text-left border border-slate-700">
                  Frequency
                </th>

                <th className="p-4 text-left border border-slate-700">
                  Ingested At
                </th>

                <th className="p-4 text-left border border-slate-700">
                  Payload Timestamp
                </th>
              </tr>
            </thead>

            <tbody>
              {telemetryData.length === 0 ? (
                <tr>
                  <td
                    colSpan={8}
                    className="p-6 border border-slate-700"
                  >
                    <p className="font-semibold text-slate-300">No telemetry records yet</p>
                    <p className="text-sm mt-1 text-slate-400">
                      Start the simulator to begin collecting data:
                    </p>
                    <p className="text-sm mt-1 font-mono text-slate-500">
                      POST /telemetry/simulate/normal
                    </p>
                  </td>
                </tr>
              ) : (
                telemetryData.map((item) => (
                  <tr
                    key={item.id}
                    className="hover:bg-slate-800 transition"
                  >
                    <td className="p-4 border border-slate-700">
                      Substation {item.substation}
                    </td>

                    <td className="p-4 border border-slate-700">
                      {item.voltage} V
                    </td>

                    <td className="p-4 border border-slate-700">
                      {item.current} A
                    </td>

                    <td className="p-4 border border-slate-700">
                      {item.temperature} °C
                    </td>

                    <td className="p-4 border border-slate-700">
                      {item.load}%
                    </td>

                    <td className="p-4 border border-slate-700">
                      {item.frequency} Hz
                    </td>

                    <td className="p-4 border border-slate-700 text-sm text-slate-300">
                      {formatDisplayTimestamp(item)}
                    </td>

                    <td className="p-4 border border-slate-700 text-sm text-slate-500">
                      {formatDisplayTimestamp({ timestamp: item.timestamp })}
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