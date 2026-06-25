type Props = {
  title: string;
  value: string;
};

export default function MetricCard({
  title,
  value,
}: Props) {
  let borderColor = "border-slate-700";
  let valueColor = "text-white";

  switch (title) {
    case "Total Nodes":
      borderColor = "border-cyan-500";
      valueColor = "text-cyan-400";
      break;

    case "Power Load":
      borderColor = "border-violet-500";
      valueColor = "text-violet-400";
      break;

    case "Active Alerts":
      borderColor = "border-rose-500";
      valueColor = "text-rose-400";
      break;

    case "Grid Health":
      borderColor = "border-emerald-500";
      valueColor = "text-emerald-400";
      break;
  }

  return (
    <div
      className={`
        bg-slate-900
        rounded-xl
        p-6
        border-2
        ${borderColor}
        hover:shadow-xl
        hover:-translate-y-1
        transition-all
        duration-300
      `}
    >
      <p className="text-slate-400 text-sm font-medium">
        {title}
      </p>

      <h2 className={`text-4xl font-bold mt-3 ${valueColor}`}>
        {value}
      </h2>
    </div>
  );
}