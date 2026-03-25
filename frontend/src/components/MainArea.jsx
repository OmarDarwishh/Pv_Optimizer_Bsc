import React from "react";
import { Zap } from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

export default function MainArea({ results }) {
  // 1. THE WAITING STATE: If Python hasn't sent data yet, show the placeholders
  if (!results) {
    return (
      <main className="main-content">
        <div className="header">
          <h1 style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <Zap size={28} color="#10b981" /> System Overview
          </h1>
        </div>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(3, 1fr)",
            gap: "24px",
          }}
        >
          <div className="placeholder-box" style={{ height: "100px" }}>
            [Waiting for AI...]
          </div>
          <div className="placeholder-box" style={{ height: "100px" }}>
            [Waiting for AI...]
          </div>
          <div className="placeholder-box" style={{ height: "100px" }}>
            [Waiting for AI...]
          </div>
        </div>
        <div
          className="placeholder-box"
          style={{ flex: 1, minHeight: "400px" }}
        >
          [Interactive Chart will appear after Optimization]
        </div>
      </main>
    );
  }

  // 2. THE SUCCESS STATE: Format the Python data so Recharts can read it
  const { kpis, charts } = results;

  // We combine the 3 arrays Python sent into one clean array of objects
  const chartData = charts.timestamps.map((time, index) => ({
    time: time,
    pv: charts.pv_generation[index],
    load: charts.load_profile[index],
  }));

  // 3. DRAW THE REAL DASHBOARD
  return (
    <main className="main-content">
      <div className="header">
        <h1 style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <Zap size={28} color="#10b981" /> Optimization Results
        </h1>
      </div>

      {/* Top KPIs (Dynamically reading from Python) */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: "24px",
        }}
      >
        <div
          style={{
            background: "#1e293b",
            padding: "20px",
            borderRadius: "8px",
            borderLeft: "4px solid #3b82f6",
          }}
        >
          <p
            style={{
              color: "#94a3b8",
              fontSize: "0.85rem",
              marginBottom: "8px",
            }}
          >
            Optimized Grid Import
          </p>
          <h2 style={{ fontSize: "1.8rem", color: "#f8fafc" }}>
            {kpis.optimized_import} kWh
          </h2>
          <p
            style={{ color: "#ef4444", fontSize: "0.75rem", marginTop: "4px" }}
          >
            Down from {kpis.original_import} kWh
          </p>
        </div>

        <div
          style={{
            background: "#1e293b",
            padding: "20px",
            borderRadius: "8px",
            borderLeft: "4px solid #10b981",
          }}
        >
          <p
            style={{
              color: "#94a3b8",
              fontSize: "0.85rem",
              marginBottom: "8px",
            }}
          >
            Self-Consumption
          </p>
          <h2 style={{ fontSize: "1.8rem", color: "#f8fafc" }}>
            {kpis.self_consumption}%
          </h2>
        </div>

        <div
          style={{
            background: "#1e293b",
            padding: "20px",
            borderRadius: "8px",
            borderLeft: "4px solid #eab308",
          }}
        >
          <p
            style={{
              color: "#94a3b8",
              fontSize: "0.85rem",
              marginBottom: "8px",
            }}
          >
            Daily Financial Impact
          </p>
          <h2 style={{ fontSize: "1.8rem", color: "#f8fafc" }}>
            {kpis.cost_saved} EGP
          </h2>
          <p
            style={{ color: "#10b981", fontSize: "0.75rem", marginTop: "4px" }}
          >
            Saved per day
          </p>
        </div>
      </div>

      {/* The Main Chart (Using Recharts) */}
      <div
        style={{
          background: "#1e293b",
          padding: "24px",
          borderRadius: "8px",
          flex: 1,
          minHeight: "400px",
          marginTop: "24px",
        }}
      >
        <h3
          style={{ marginBottom: "20px", fontSize: "1rem", color: "#f8fafc" }}
        >
          24-Hour Power Profile
        </h3>

        <ResponsiveContainer width="100%" height={350}>
          <AreaChart
            data={chartData}
            margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
          >
            {/* Creates the cool fade effect under the lines */}
            <defs>
              <linearGradient id="colorPv" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#10b981" stopOpacity={0.8} />
                <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="colorLoad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#ef4444" stopOpacity={0.8} />
                <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
              </linearGradient>
            </defs>

            <CartesianGrid
              strokeDasharray="3 3"
              stroke="#334155"
              vertical={false}
            />
            <XAxis
              dataKey="time"
              stroke="#94a3b8"
              tick={{ fill: "#94a3b8" }}
              // This takes "2026-03-26 09:00:00" and chops it down to just "09:00"
              tickFormatter={(timeStr) =>
                timeStr.length > 10 ? timeStr.substring(11, 16) : timeStr
              }
            />

            <YAxis
              domain={[0, 7]} /* THIS IS THE MAGIC LINE */
              stroke="#94a3b8"
              tick={{ fill: "#94a3b8" }}
              // This adds the "Power (kW)" label to the side, just like Matplotlib
              label={{
                value: "Power (kW)",
                angle: -90,
                position: "insideLeft",
                fill: "#94a3b8",
                style: { textAnchor: "middle" },
              }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "#0f172a",
                borderColor: "#334155",
                color: "#f8fafc",
              }}
              itemStyle={{ color: "#f8fafc" }}
            />
            <Legend verticalAlign="top" height={36} />

            {/* The Green Solar Curve */}
            <Area
              type="monotone"
              dataKey="pv"
              stroke="#10b981"
              strokeWidth={2}
              fillOpacity={1}
              fill="url(#colorPv)"
              name="Solar Generation (kW)"
            />

            {/* The Red Appliance Load Curve (Using stepAfter to look like blocks) */}
            <Area
              type="stepAfter"
              dataKey="load"
              stroke="#ef4444"
              strokeWidth={2}
              fillOpacity={1}
              fill="url(#colorLoad)"
              name="Optimized Load (kW)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </main>
  );
}
