import Sidebar from "../../components/Sidebar";
import Navbar from "../../components/Navbar";
import AutoRefreshControls from "../../components/AutoRefreshControls";
import { api, TelemetryRecord } from "../../services/api";
import { getTelemetryFreshness } from "../../services/telemetryFreshness";

export const dynamic = "force-dynamic";


const fallbackTelemetry: TelemetryRecord[] = [];


function formatTimestamp(timestamp: string): string {
  return new Date(timestamp).toLocaleString();
}


export default async function Telemetry() {
  let telemetryData = fallbackTelemetry;

  try {
    telemetryData = await api.getTelemetry(100);
  } catch (error) {
    console.error("Failed to fetch telemetry data:", error);
  }

  const telemetryFreshness = getTelemetryFreshness(telemetryData[0]?.timestamp);

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

          <AutoRefreshControls label="Refresh Telemetry" />
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
                  Timestamp
                </th>
              </tr>
            </thead>

            <tbody>
              {telemetryData.length === 0 ? (
                <tr>
                  <td
                    colSpan={7}
                    className="p-6 text-center text-slate-400 border border-slate-700"
                  >
                    No telemetry records available.
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
                      {formatTimestamp(item.timestamp)}
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