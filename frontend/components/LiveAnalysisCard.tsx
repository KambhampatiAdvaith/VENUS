type Metric = {
  label: string;
  value: string;
};

type LiveAnalysisCardProps = {
  /** Short uppercase label, e.g. "Live Grid Analysis" */
  title: string;
  /** Bold headline shown below the title */
  headline: string;
  /** Optional secondary line shown below the headline */
  subtext?: string;
  /** Up to 4 key metrics displayed in a grid */
  metrics?: Metric[];
  /** When true, renders in amber warning colours instead of cyan */
  isStale?: boolean;
};

/**
 * Server-renderable card that replaces the raw "Last telemetry update / Data age"
 * banner with a live-analysis-oriented summary.
 */
export default function LiveAnalysisCard({
  title,
  headline,
  subtext,
  metrics = [],
  isStale = false,
}: LiveAnalysisCardProps) {
  const borderColor = isStale ? "border-amber-500/40" : "border-cyan-500/40";
  const bgColor = isStale ? "bg-amber-500/10" : "bg-cyan-500/10";
  const textColor = isStale ? "text-amber-100" : "text-cyan-100";
  const labelColor = isStale ? "text-amber-300" : "text-cyan-300";
  const subtextColor = isStale ? "text-amber-200/80" : "text-cyan-200/80";

  return (
    <div
      className={`mb-8 rounded-xl border ${borderColor} ${bgColor} p-4 ${textColor}`}
    >
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <p className={`text-sm uppercase tracking-wide ${labelColor}`}>
            {title}
          </p>

          <p className="text-xl font-bold">{headline}</p>

          {subtext ? (
            <p className={`mt-1 text-sm ${subtextColor}`}>{subtext}</p>
          ) : null}
        </div>

        {metrics.length > 0 ? (
          <div className="grid grid-cols-2 gap-4 text-sm md:grid-cols-4">
            {metrics.map((metric) => (
              <div key={metric.label}>
                <p className={labelColor}>{metric.label}</p>
                <p className="font-semibold">{metric.value}</p>
              </div>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}
