"use client";

import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
} from "recharts";


export type AnalyticsChartData = {
  zone: string;
  load: number;
};


type AnalyticsChartProps = {
  data: AnalyticsChartData[];
};


export default function AnalyticsChart({ data }: AnalyticsChartProps) {
  return (
    <div className="bg-slate-900 rounded-xl p-6 border border-slate-800">
      <h2 className="text-xl font-bold mb-4">
        Zone Load Analysis
      </h2>

      {data.length === 0 ? (
        <div className="h-[300px] flex items-center justify-center text-slate-400">
          No load analytics available.
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={data}>
            <XAxis dataKey="zone" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="load" fill="#22c55e" />
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}