import React from "react";
import { Zap, TrendingUp, TrendingDown, BatteryCharging } from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  ReferenceArea,
} from "recharts";

// --- SAAS PILL BADGE ---
const ApplianceBadge = (props) => {
  const { viewBox, value, index } = props;
  if (!viewBox) return null;

  const { x, width, y } = viewBox;
  const centerX = x + width / 2;
  const yPos = y + 20 + index * 35;

  return (
    <g style={{ pointerEvents: "none" }}>
      <line
        x1={centerX}
        y1={yPos + 24}
        x2={centerX}
        y2={300}
        stroke="#ef4444"
        strokeDasharray="3 3"
        opacity={0.5}
      />
      <rect
        x={centerX - 65}
        y={yPos}
        width={130}
        height={24}
        fill="#0f172a"
        stroke="#ef4444"
        strokeWidth={1}
        strokeOpacity={0.8}
        rx={6}
      />
      <text
        x={centerX}
        y={yPos + 16}
        fill="#f8fafc"
        fontSize={11}
        fontWeight="bold"
        textAnchor="middle"
      >
        {value}
      </text>
    </g>
  );
};

// --- TREND BADGE COMPONENT ---
const TrendBadge = ({ value, label, isPositive }) => (
  <div
    style={{
      display: "inline-flex",
      alignItems: "center",
      gap: "4px",
      background: isPositive
        ? "rgba(16, 185, 129, 0.15)"
        : "rgba(239, 68, 68, 0.15)",
      color: isPositive ? "#10b981" : "#ef4444",
      padding: "4px 8px",
      borderRadius: "12px",
      fontSize: "0.75rem",
      fontWeight: "bold",
      marginTop: "8px",
    }}
  >
    {isPositive ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
    {value} {label}
  </div>
);

export default function MainArea({ results }) {
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
          <div className="placeholder-box" style={{ height: "120px" }}>
            [Awaiting AI Input...]
          </div>
          <div className="placeholder-box" style={{ height: "120px" }}>
            [Awaiting AI Input...]
          </div>
          <div className="placeholder-box" style={{ height: "120px" }}>
            [Awaiting AI Input...]
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

  const { kpis, charts, schedules } = results;

  // --- DATA MAPPING ---
  const chartData = charts.timestamps.map((time, index) => {
    const total = charts.load_profile[index];
    const base = charts.base_load ? charts.base_load[index] : total;
    const applianceOnly = Math.max(0, total - base);

    return {
      time: time,
      pv: charts.pv_generation[index],
      baseLoad: base,
      applianceLoad: applianceOnly,
    };
  });

  // Calculate UI Deltas safely
  const importSaved = (kpis.original_import - kpis.optimized_import).toFixed(1);
  const scImprovement = (kpis.self_consumption - (kpis.base_sc || 0)).toFixed(
    1,
  );

  return (
    <main className="main-content">
      <div className="header">
        <h1 style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <Zap size={28} color="#10b981" /> Optimization Results
        </h1>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: "24px",
        }}
      >
        {/* KPI 1: Grid Import */}
        <div
          style={{
            background: "#1e293b",
            padding: "20px",
            borderRadius: "8px",
            borderLeft: "4px solid #3b82f6",
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
          }}
        >
          <div>
            <p
              style={{
                color: "#94a3b8",
                fontSize: "0.85rem",
                marginBottom: "4px",
              }}
            >
              Optimized Grid Import
            </p>
            <h2 style={{ fontSize: "2rem", color: "#f8fafc", margin: 0 }}>
              {kpis.optimized_import}{" "}
              <span style={{ fontSize: "1rem", color: "#94a3b8" }}>kWh</span>
            </h2>
          </div>
          <TrendBadge
            value={`${importSaved} kWh`}
            label={`avoided (from original ${kpis.original_import} kWh)`}
            isPositive={true}
          />
        </div>

        {/* KPI 2: Self-Consumption */}
        <div
          style={{
            background: "#1e293b",
            padding: "20px",
            borderRadius: "8px",
            borderLeft: "4px solid #10b981",
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
          }}
        >
          <div>
            <p
              style={{
                color: "#94a3b8",
                fontSize: "0.85rem",
                marginBottom: "4px",
                display: "flex",
                alignItems: "center",
                gap: "6px",
              }}
            >
              <BatteryCharging size={14} color="#10b981" /> Self-Consumption
              Ratio
            </p>
            <h2 style={{ fontSize: "2rem", color: "#f8fafc", margin: 0 }}>
              {kpis.self_consumption}%
            </h2>
          </div>
          {/* UPDATED: Clearly shows the exact Baseline SC before optimization */}
          {kpis.base_sc !== undefined && (
            <TrendBadge
              value={`+${scImprovement}%`}
              label={`improvement (from original ${kpis.base_sc}%)`}
              isPositive={true}
            />
          )}
        </div>

        {/* KPI 3: Financials */}
        <div
          style={{
            background: "#1e293b",
            padding: "20px",
            borderRadius: "8px",
            borderLeft: "4px solid #eab308",
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
          }}
        >
          <div>
            <p
              style={{
                color: "#94a3b8",
                fontSize: "0.85rem",
                marginBottom: "4px",
              }}
            >
              Daily Financial Impact
            </p>
            <h2 style={{ fontSize: "2rem", color: "#f8fafc", margin: 0 }}>
              {kpis.cost_saved}{" "}
              <span style={{ fontSize: "1rem", color: "#94a3b8" }}>EGP</span>
            </h2>
          </div>
          <p
            style={{
              color: "#94a3b8",
              fontSize: "0.75rem",
              margin: 0,
              marginTop: "12px",
            }}
          >
            Calculated via Egyptian Ministry of Electricity Tariff
          </p>
        </div>
      </div>

      <div
        style={{
          background: "#1e293b",
          padding: "24px",
          borderRadius: "8px",
          flex: 1,
          minHeight: "400px",
          marginTop: "24px",
          display: "flex",
          flexDirection: "column",
        }}
      >
        <h3
          style={{ marginBottom: "20px", fontSize: "1rem", color: "#f8fafc" }}
        >
          24-Hour Power Profile
        </h3>

        <ResponsiveContainer width="100%" flex={1}>
          <AreaChart
            data={chartData}
            margin={{ top: 20, right: 30, left: 0, bottom: 0 }}
          >
            <defs>
              <linearGradient id="colorPv" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#10b981" stopOpacity={0.8} />
                <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="colorAppLoad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#ef4444" stopOpacity={0.6} />
                <stop offset="100%" stopColor="#ef4444" stopOpacity={0.1} />
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
              tickFormatter={(timeStr) =>
                timeStr.length > 10 ? timeStr.substring(11, 16) : timeStr
              }
            />
            <YAxis
              domain={[0, 7]}
              stroke="#94a3b8"
              tick={{ fill: "#94a3b8" }}
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
                borderRadius: "8px",
              }}
              itemStyle={{ color: "#f8fafc", fontWeight: "bold" }}
            />
            <Legend
              verticalAlign="bottom"
              height={36}
              iconType="circle"
              wrapperStyle={{ paddingTop: "20px" }}
            />

            {schedules &&
              schedules.map((app, index) => (
                <ReferenceArea
                  key={index}
                  x1={app.start}
                  x2={app.end}
                  strokeOpacity={0}
                  fill="#ef4444"
                  fillOpacity={0.05}
                  label={(props) => (
                    <ApplianceBadge {...props} value={app.name} index={index} />
                  )}
                />
              ))}

            <Area
              type="stepAfter"
              dataKey="baseLoad"
              stroke="#64748b"
              strokeWidth={2}
              fill="#0f172a"
              fillOpacity={0.8}
              name="Base Load (kW)"
            />
            <Area
              type="stepAfter"
              dataKey="applianceLoad"
              stroke="#ef4444"
              strokeWidth={2}
              fill="url(#colorAppLoad)"
              fillOpacity={1}
              name="AI Shifted Appliances (kW)"
            />
            <Area
              type="monotone"
              dataKey="pv"
              stroke="#10b981"
              strokeWidth={2}
              fillOpacity={1}
              fill="url(#colorPv)"
              name="Solar Generation (kW)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </main>
  );
}
