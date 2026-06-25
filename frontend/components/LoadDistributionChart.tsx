"use client";

import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
} from "recharts";


export type LoadDistributionData = {
  name: string;
  value: number;
};


type LoadDistributionChartProps = {
  data: LoadDistributionData[];
};


const COLORS = [
  "#3b82f6",
  "#22c55e",
  "#f59e0b",
  "#ef4444",
  "#06b6d4",
  "#a855f7",
];


export default function LoadDistributionChart({
  data,
}: LoadDistributionChartProps) {
  return (
    <div className="bg-slate-900 rounded-xl p-6 border border-slate-800">
      <h2 className="text-xl font-bold mb-4">
        Load Distribution
      </h2>

      {data.length === 0 ? (
        <div className="h-[300px] flex items-center justify-center text-slate-400">
          No load distribution data available.
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={300}>
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              outerRadius={100}
              dataKey="value"
              label
            >
              {data.map((entry, index) => (
                <Cell
                  key={entry.name}
                  fill={COLORS[index % COLORS.length]}
                />
              ))}
            </Pie>

            <Tooltip />
          </PieChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}