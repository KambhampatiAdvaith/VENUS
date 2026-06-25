import Sidebar from "../../components/Sidebar";
import Navbar from "../../components/Navbar";
import { api, TelemetryRecord } from "../../services/api";


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

  return (
    <div className="flex min-h-screen bg-slate-950 text-white">
      <Sidebar />

      <main className="flex-1 p-8">
        <Navbar />

        <h1 className="text-4xl font-bold mb-2">
          Telemetry
        </h1>

        <p className="text-slate-400 mb-8">
          Real-time V.E.N.U.S telemetry monitoring
        </p>

        <div className="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden">
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