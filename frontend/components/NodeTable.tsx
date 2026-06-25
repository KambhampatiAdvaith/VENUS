export default function NodeTable() {
  const nodes = [
    {
      id: "N-101",
      voltage: "230V",
      load: "15 MW",
      status: "Active",
    },
    {
      id: "N-102",
      voltage: "220V",
      load: "12 MW",
      status: "Active",
    },
    {
      id: "N-103",
      voltage: "210V",
      load: "18 MW",
      status: "Warning",
    },
  ];

  return (
    <div className="bg-slate-800 rounded-xl p-6">
      <h2 className="text-xl font-bold mb-4">
        Grid Nodes
      </h2>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="text-left border-b border-slate-700">
              <th>ID</th>
              <th>Voltage</th>
              <th>Load</th>
              <th>Status</th>
            </tr>
          </thead>

          <tbody>
            {nodes.map((node) => (
              <tr
                key={node.id}
                className="border-b border-slate-700"
              >
                <td>{node.id}</td>
                <td>{node.voltage}</td>
                <td>{node.load}</td>
                <td>{node.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}