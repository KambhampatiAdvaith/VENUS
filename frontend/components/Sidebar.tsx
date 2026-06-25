"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export default function Sidebar() {
  const pathname = usePathname();

  const linkClass = (path: string) =>
    pathname === path
      ? "bg-blue-600 p-3 rounded-lg"
      : "p-3 rounded-lg hover:bg-slate-800";

  return (
    <aside className="w-64 min-h-screen bg-slate-900 border-r border-slate-800 text-white p-6">
      <h1 className="text-3xl font-bold mb-10">
        V.E.N.U.S
      </h1>

      <nav className="flex flex-col gap-3">
        <Link href="/dashboard" className={linkClass("/dashboard")}>
          Dashboard
        </Link>

        <Link href="/telemetry" className={linkClass("/telemetry")}>
          Telemetry
        </Link>

        <Link href="/alerts" className={linkClass("/alerts")}>
          Alerts
        </Link>

        <Link href="/nodes" className={linkClass("/nodes")}>
          Node Status
        </Link>

        <Link
          href="/load-balancing"
          className={linkClass("/load-balancing")}
        >
          Load Balancing
        </Link>

        <Link href="/analytics" className={linkClass("/analytics")}>
          Analytics
        </Link>

        <Link
          href="/predictions"
          className={linkClass("/predictions")}
        >
          AI Predictions
        </Link>

        <Link href="/settings" className={linkClass("/settings")}>
          Settings
        </Link>
      </nav>
    </aside>
  );
}