"use client";

import { useEffect, useState } from "react";


export default function Navbar() {
  const [currentTime, setCurrentTime] = useState("");


  useEffect(() => {
    function updateTime() {
      const time = new Date().toLocaleTimeString("en-GB", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });

      setCurrentTime(time);
    }

    updateTime();

    const timer = setInterval(updateTime, 1000);

    return () => clearInterval(timer);
  }, []);


  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl px-4 py-4 mb-8 flex items-center justify-between">
      <div>
        <h2 className="text-lg font-bold">
          V.E.N.U.S Control Center
        </h2>

        <p className="text-blue-300 text-sm">
          Volt Edge Network Utility System
        </p>
      </div>

      <div className="flex items-center gap-4">
        <span className="text-sm">
          {currentTime || "--:--:--"}
        </span>

        <span className="w-3 h-3 bg-green-500 rounded-full" />

        <button className="bg-slate-800 px-4 py-2 rounded-lg">
          Admin
        </button>
      </div>
    </div>
  );
}