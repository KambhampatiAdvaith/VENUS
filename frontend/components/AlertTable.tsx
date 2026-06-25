export default function AlertTable() {
  const alerts = [
    {
      id: 1,
      type: "Overload",
      location: "Node N-103",
    },
    {
      id: 2,
      type: "Voltage Drop",
      location: "Node N-107",
    },
  ];

  return (
    <div className="bg-slate-800 rounded-xl p-6">
      <h2 className="text-xl font-bold mb-4">
        Active Alerts
      </h2>

      {alerts.map((alert) => (
        <div
          key={alert.id}
          className="border-b border-slate-700 py-3"
        >
          <p>{alert.type}</p>
          <p className="text-slate-400">
            {alert.location}
          </p>
        </div>
      ))}
    </div>
  );
}