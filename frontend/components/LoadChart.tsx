"use client";

import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";


export type LoadChartData = {
  time: string;
  fullTimestamp?: string;
  load: number;
};


type AggregatedLoadChartData = LoadChartData & {
  sampleCount: number;
};


type LoadChartProps = {
  data: LoadChartData[];
};


type LoadChartTooltipProps = {
  active?: boolean;
  payload?: Array<{
    value?: number | string;
    payload?: AggregatedLoadChartData;
  }>;
};


function formatLoadValue(value: number | string | undefined): string {
  const numericValue = typeof value === "number" ? value : Number(value);

  if (Number.isNaN(numericValue)) {
    return "N/A";
  }

  return `${numericValue.toFixed(2)}%`;
}


function aggregateLoadTrend(data: LoadChartData[]): AggregatedLoadChartData[] {
  const grouped = new Map<
    string,
    {
      time: string;
      fullTimestamp?: string;
      totalLoad: number;
      sampleCount: number;
    }
  >();

  data.forEach((item) => {
    const key = item.fullTimestamp ?? item.time;
    const existing = grouped.get(key);

    if (existing) {
      existing.totalLoad += item.load;
      existing.sampleCount += 1;
      return;
    }

    grouped.set(key, {
      time: item.time,
      fullTimestamp: item.fullTimestamp,
      totalLoad: item.load,
      sampleCount: 1,
    });
  });

  return Array.from(grouped.values()).map((item) => ({
    time: item.time,
    fullTimestamp: item.fullTimestamp,
    load: Number((item.totalLoad / item.sampleCount).toFixed(2)),
    sampleCount: item.sampleCount,
  }));
}


function getChartSubtitle(data: AggregatedLoadChartData[]): string | null {
  const timestamps = data
    .map((item) => item.fullTimestamp)
    .filter((value): value is string => value != null && value !== "N/A");

  if (timestamps.length === 0) {
    return null;
  }

  const start = timestamps[0];
  const end = timestamps[timestamps.length - 1];

  if (start === end) {
    return `Showing average grid load from ${start}`;
  }

  return `Showing average grid load from ${start} → ${end}`;
}


function LoadChartTooltip({ active, payload }: LoadChartTooltipProps) {
  if (!active || !payload?.length) {
    return null;
  }

  const point = payload[0];
  const pointData = point.payload;

  if (!pointData) {
    return null;
  }

  const timestamp = pointData.fullTimestamp ?? pointData.time;

  return (
    <div className="rounded-lg border border-slate-700 bg-slate-950/95 px-3 py-2 text-sm text-slate-100 shadow-lg">
      <p className="font-medium">{timestamp}</p>
      <p className="mt-1 text-slate-300">
        Average Load: {formatLoadValue(point.value)}
      </p>
      <p className="mt-1 text-xs text-slate-500">
        Combined from {pointData.sampleCount} telemetry reading{pointData.sampleCount !== 1 ? "s" : ""}
      </p>
    </div>
  );
}


export default function LoadChart({ data }: LoadChartProps) {
  const chartData = aggregateLoadTrend(data);
  const chartSubtitle = getChartSubtitle(chartData);

  return (
    <div className="bg-slate-900 rounded-xl p-6 border border-slate-800">
      <h2 className="text-xl font-bold">
        Power Load Trend
      </h2>

      <p className="mt-1 text-sm text-slate-400">
        Average load across reported substations for each telemetry cycle.
      </p>

      {chartSubtitle && (
        <div className="mb-4 mt-2 space-y-1">
          <p className="text-sm text-slate-400">{chartSubtitle}</p>
          <p className="text-xs text-slate-500">
            Uses recorded telemetry timestamps and refreshes live when new
            telemetry triggers the existing page update flow.
          </p>
        </div>
      )}

      {chartData.length === 0 ? (
        <div className="h-[300px] flex items-center justify-center text-slate-400">
          No load trend data available.
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />

            <XAxis dataKey="time" />

            <YAxis />

            <Tooltip content={<LoadChartTooltip />} />

            <Line
              type="monotone"
              dataKey="load"
              stroke="#22c55e"
              strokeWidth={3}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
