import React, { useState } from "react";
import {
  Zap,
  TrendingUp,
  TrendingDown,
  BatteryCharging,
  LineChart,
  CheckCircle2,
  Download,
  Coins,
  Activity,
  Sliders,
  Satellite,
  Play,
} from "lucide-react";
import {
  AreaChart,
  Area,
  Line,
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
    className={`trend-badge ${isPositive ? "trend-badge--positive" : "trend-badge--negative"}`}
  >
    {isPositive ? <TrendingUp size={13} /> : <TrendingDown size={13} />}
    {value} <span className="trend-badge__sub">{label}</span>
  </div>
);

export default function MainArea({ results }) {
  const [graphMode, setGraphMode] = useState("optimized");

  if (!results) {
    return (
      <main className="main-content">
        <div className="header">
          <h1>
            <Zap size={24} color="#10b981" /> System Overview
          </h1>
          <span className="header-badge header-badge--ready">Idle • Ready</span>
        </div>

        <div className="kpi-grid">
          <div className="empty-kpi">
            <div className="empty-kpi__head">
              <span className="empty-kpi__label">Optimized Grid Import</span>
              <span className="empty-kpi__icon">
                <Download size={18} />
              </span>
            </div>
            <div className="empty-kpi__value">
              —<span className="empty-kpi__unit">kWh</span>
            </div>
            <span className="empty-kpi__caption">
              Energy pulled from the grid after the AI schedules appliances
              onto solar surplus.
            </span>
          </div>

          <div className="empty-kpi">
            <div className="empty-kpi__head">
              <span className="empty-kpi__label">Self-Consumption Ratio</span>
              <span className="empty-kpi__icon">
                <BatteryCharging size={18} />
              </span>
            </div>
            <div className="empty-kpi__value">
              —<span className="empty-kpi__unit">%</span>
            </div>
            <span className="empty-kpi__caption">
              Share of solar generation consumed on-site rather than exported
              back to the grid.
            </span>
          </div>

          <div className="empty-kpi">
            <div className="empty-kpi__head">
              <span className="empty-kpi__label">Daily Financial Impact</span>
              <span className="empty-kpi__icon">
                <Coins size={18} />
              </span>
            </div>
            <div className="empty-kpi__value">
              —<span className="empty-kpi__unit">EGP</span>
            </div>
            <span className="empty-kpi__caption">
              Estimated daily savings vs. running appliances at default peak
              hours (Egyptian tariff).
            </span>
          </div>
        </div>

        <div className="empty-chart">
          <div className="empty-chart__icon">
            <Activity size={32} />
          </div>
          <div className="empty-chart__title">Ready to Simulate</div>
          <div className="empty-chart__sub">
            Configure your PV hardware and appliance windows on the left,
            then press <strong>Run AI Optimization</strong> to see your 24-hour
            power profile with AI-shifted load blocks overlaid on solar
            generation.
          </div>
          <div className="empty-chart__steps">
            <div className="empty-chart__step">
              <span className="empty-chart__step-num">1</span>
              <Satellite size={14} /> Choose data source
            </div>
            <div className="empty-chart__step">
              <span className="empty-chart__step-num">2</span>
              <Sliders size={14} /> Tune hardware + appliances
            </div>
            <div className="empty-chart__step">
              <span className="empty-chart__step-num">3</span>
              <Play size={14} /> Run AI to generate schedule
            </div>
          </div>
        </div>
      </main>
    );
  }

  const { kpis, charts, schedules } = results;
  const isCompareMode = Array.isArray(charts.pv_compare);

  // Mean absolute % difference between the two PV curves, restricted to daylight hours.
  // Using the symmetric denominator (mean of the two values) avoids blow-up when one
  // curve dips near zero.
  let meanDelta = null;
  if (isCompareMode) {
    const pairs = charts.pv_generation
      .map((v, i) => ({ a: v, b: charts.pv_compare[i] }))
      .filter((p) => p.a + p.b > 0.1); // ignore nighttime hours
    if (pairs.length) {
      const diffs = pairs.map(
        (p) => (Math.abs(p.a - p.b) / ((p.a + p.b) / 2)) * 100,
      );
      meanDelta = diffs.reduce((s, d) => s + d, 0) / diffs.length;
    }
  }

  // --- DATA MAPPING: Safely map Before and After logic ---
  const chartData = charts.timestamps.map((time, index) => {
    const totalOptimized = charts.load_profile[index];
    const base = charts.base_load ? charts.base_load[index] : totalOptimized;

    // If we are in 'baseline' mode, the appliance load is 0 visually (it's embedded in the grey base load).
    // If 'optimized', we calculate the red spike.
    const applianceOnly =
      graphMode === "optimized" ? Math.max(0, totalOptimized - base) : 0;

    // In baseline mode, the total house load is just the grey base. In optimized, it's the grey base + red AI shifts.
    const displayBaseLoad = graphMode === "optimized" ? base : base;

    return {
      time: time,
      pv: charts.pv_generation[index],
      pvCompare: isCompareMode ? charts.pv_compare[index] : null,
      baseLoad: displayBaseLoad,
      applianceLoad: applianceOnly,
    };
  });

  const importSaved = (kpis.original_import - kpis.optimized_import).toFixed(1);
  const scImprovement = (kpis.self_consumption - (kpis.base_sc || 0)).toFixed(
    1,
  );

  return (
    <main className="main-content">
      <div className="header">
        <h1>
          <Zap size={24} color="#10b981" /> Optimization Results
        </h1>
        <span className="header-badge">
          {isCompareMode ? "Compare Mode" : "Live"}
        </span>
      </div>

      <div className="kpi-grid">
        <div className="kpi-card kpi-card--import">
          <div className="kpi-card__head">
            <span className="kpi-card__label">Optimized Grid Import</span>
            <span className="kpi-card__icon">
              <Download size={18} />
            </span>
          </div>
          <div className="kpi-card__value">
            {kpis.optimized_import}
            <span className="kpi-card__unit">kWh</span>
          </div>
          <TrendBadge
            value={`${importSaved} kWh`}
            label={`avoided (from ${kpis.original_import} kWh)`}
            isPositive={true}
          />
        </div>

        <div className="kpi-card kpi-card--sc">
          <div className="kpi-card__head">
            <span className="kpi-card__label">Self-Consumption Ratio</span>
            <span className="kpi-card__icon">
              <BatteryCharging size={18} />
            </span>
          </div>
          <div className="kpi-card__value">
            {kpis.self_consumption}
            <span className="kpi-card__unit">%</span>
          </div>
          {kpis.base_sc !== undefined && (
            <TrendBadge
              value={`+${scImprovement}%`}
              label={`improvement (from ${kpis.base_sc}%)`}
              isPositive={true}
            />
          )}
        </div>

        <div className="kpi-card kpi-card--cost">
          <div className="kpi-card__head">
            <span className="kpi-card__label">Daily Financial Impact</span>
            <span className="kpi-card__icon">
              <Coins size={18} />
            </span>
          </div>
          <div className="kpi-card__value">
            {kpis.cost_saved}
            <span className="kpi-card__unit">EGP</span>
          </div>
          <div className="kpi-card__footer">
            Egyptian Ministry of Electricity Tariff
          </div>
        </div>
      </div>

      {/* GRAPH SECTION WITH TOGGLE */}
      <div className="chart-panel">
        <div className="chart-panel__head">
          <div className="chart-panel__title">
            <h3>24-Hour Power Profile</h3>
            <span>
              {isCompareMode
                ? `PVGIS Live vs. NASA Historical • Mean daytime Δ: ${
                    meanDelta !== null ? meanDelta.toFixed(1) : "—"
                  }%`
                : "Solar generation vs. household load across the day"}
            </span>
          </div>

          <div className="toggle-group">
            <button
              onClick={() => setGraphMode("baseline")}
              className={`pill ${graphMode === "baseline" ? "pill--active-neutral" : ""}`}
            >
              <LineChart size={14} /> Baseline (Before)
            </button>
            <button
              onClick={() => setGraphMode("optimized")}
              className={`pill ${graphMode === "optimized" ? "pill--active-green" : ""}`}
            >
              <CheckCircle2 size={14} /> AI Optimized (After)
            </button>
          </div>
        </div>

        {/* THE GRAPH */}
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

            {/* Appliance overlay hidden in compare mode — the chart is about curve divergence, not scheduling */}
            {graphMode === "optimized" &&
              !isCompareMode &&
              schedules &&
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

            {graphMode === "optimized" && !isCompareMode && (
              <Area
                type="stepAfter"
                dataKey="applianceLoad"
                stroke="#ef4444"
                strokeWidth={2}
                fill="url(#colorAppLoad)"
                fillOpacity={1}
                name="AI Shifted Appliances (kW)"
              />
            )}

            <Area
              type="monotone"
              dataKey="pv"
              stroke="#10b981"
              strokeWidth={2}
              fillOpacity={1}
              fill="url(#colorPv)"
              name={isCompareMode ? "PVGIS Live (kW)" : "Solar Generation (kW)"}
            />

            {isCompareMode && (
              <Line
                type="monotone"
                dataKey="pvCompare"
                stroke="#3b82f6"
                strokeWidth={2}
                strokeDasharray="6 4"
                dot={false}
                activeDot={{ r: 4 }}
                name="NASA Historical (kW)"
                isAnimationActive={false}
              />
            )}
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </main>
  );
}
