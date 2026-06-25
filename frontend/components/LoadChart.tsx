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
  load: number;
};


type LoadChartProps = {
  data: LoadChartData[];
};


export default function LoadChart({ data }: LoadChartProps) {
  return (
    <div className="bg-slate-900 rounded-xl p-6 border border-slate-800">
      <h2 className="text-xl font-bold mb-4">
        Power Load Trend
      </h2>

      {data.length === 0 ? (
        <div className="h-[300px] flex items-center justify-center text-slate-400">
          No load trend data available.
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />

            <XAxis dataKey="time" />

            <YAxis />

            <Tooltip />

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