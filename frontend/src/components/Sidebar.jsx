import React from "react";
import {
  Clock,
  Sun,
  Play,
  Power,
  CloudSun,
  Database,
  Calendar,
} from "lucide-react";

export default function Sidebar({
  config,
  setConfig,
  handleOptimize,
  loading,
  dataMode,
  setDataMode,
  targetYear,
  setTargetYear,
}) {
  // NASA POWER's earliest hourly record is 2001; and we cap at last year so
  // the overlaid "tomorrow" is always in the past (NASA lags real-time by ~3-5 days).
  const MIN_YEAR = 2001;
  const MAX_YEAR = new Date().getFullYear() - 1;

  // Year picker visible whenever NASA is part of the request (nasa-only or compare).
  const needsYearPicker = dataMode === "nasa" || dataMode === "compare";

  // Preview: tomorrow's calendar day, overlaid on the chosen year
  const previewDate = (() => {
    const d = new Date();
    d.setDate(d.getDate() + 1);
    d.setFullYear(targetYear);
    return d.toLocaleDateString("en-US", {
      weekday: "long",
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  })();
  const handleChange = (e) => {
    const { name, value } = e.target;
    setConfig((prev) => ({ ...prev, [name]: Number(value) }));
  };

  const toggleAppliance = (appKey) => {
    setConfig((prev) => ({ ...prev, [appKey]: !prev[appKey] }));
  };

  const ApplianceBlock = ({ name, power, enabledKey, startKey, endKey }) => {
    const isEnabled = config[enabledKey];
    return (
      <div
        className={`appliance-card ${isEnabled ? "appliance-card--active" : ""}`}
      >
        <div className="appliance-card__head">
          <div className="appliance-card__name">
            {name}
            <span className="appliance-card__power">{power} kW</span>
          </div>
          <button
            className={`toggle ${isEnabled ? "toggle--on" : ""}`}
            onClick={() => toggleAppliance(enabledKey)}
          >
            <Power size={11} /> {isEnabled ? "ON" : "OFF"}
          </button>
        </div>

        <div
          className={`appliance-inputs ${!isEnabled ? "appliance-inputs--disabled" : ""}`}
        >
          <label className="field-label">
            Start After
            <input
              type="number"
              className="input-field"
              name={startKey}
              min="0"
              max="23"
              value={config[startKey]}
              onChange={handleChange}
              style={{ marginTop: 4 }}
            />
          </label>
          <label className="field-label">
            Finish By
            <input
              type="number"
              className="input-field"
              name={endKey}
              min="0"
              max="23"
              value={config[endKey]}
              onChange={handleChange}
              style={{ marginTop: 4 }}
            />
          </label>
        </div>
      </div>
    );
  };

  const azimuthLabel =
    config.azimuth === 0 ? "South" : config.azimuth > 0 ? "West" : "East";

  return (
    <aside className="sidebar">
      <div className="brand">
        <h2>HEMS Optimizer</h2>
        <p>PV Self-Consumption System</p>
      </div>

      <div className="control-section">
        <h3>
          <Database size={13} /> Data Source
        </h3>
        <div className="panel">
          <div className="pill-group">
            <button
              onClick={() => setDataMode("live")}
              className={`pill ${dataMode === "live" ? "pill--active-green" : ""}`}
            >
              <CloudSun size={13} /> Live
            </button>
          </div>

          {needsYearPicker && (
            <div style={{ marginTop: 14 }}>
              <label className="field-label">
                <span
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                    marginBottom: 6,
                  }}
                >
                  <Calendar size={12} /> Analog Year
                </span>
                <input
                  type="number"
                  className="input-field"
                  value={targetYear}
                  min={MIN_YEAR}
                  max={MAX_YEAR}
                  step="1"
                  onChange={(e) => {
                    const y = Number(e.target.value);
                    if (!Number.isNaN(y)) setTargetYear(y);
                  }}
                />
              </label>

              <div
                style={{
                  marginTop: 10,
                  padding: "8px 10px",
                  background: "var(--bg-deep)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "var(--r-sm)",
                  fontSize: "0.72rem",
                  color: "var(--text-muted)",
                }}
              >
                <span style={{ color: "var(--text-dim)" }}>Resolves to</span>
                <br />
                <span
                  style={{
                    color: "var(--text-main)",
                    fontWeight: 600,
                    fontSize: "0.78rem",
                  }}
                >
                  {previewDate}
                </span>
              </div>

              <span
                style={{
                  display: "block",
                  marginTop: 10,
                  fontSize: "0.68rem",
                  color: "var(--text-dim)",
                  lineHeight: 1.5,
                }}
              >
                Calendar day is locked to tomorrow — only the historical year
                varies. Sun geometry matches tomorrow; weather is sampled from
                the chosen year.
              </span>
            </div>
          )}
        </div>
      </div>

      <div className="control-section">
        <h3>
          <Sun size={13} /> Hardware Configuration
        </h3>
        <div
          className="panel"
          style={{ display: "flex", flexDirection: "column", gap: 16 }}
        >
          <label className="field-label">
            Roof Azimuth{" "}
            <span className="field-value">
              {config.azimuth}° {azimuthLabel}
            </span>
            <input
              type="range"
              name="azimuth"
              className="range"
              min="-90"
              max="90"
              step="15"
              value={config.azimuth}
              onChange={handleChange}
            />
          </label>
          <label className="field-label">
            Panel Tilt <span className="field-value">{config.tilt}°</span>
            <input
              type="range"
              name="tilt"
              className="range"
              min="0"
              max="90"
              step="5"
              value={config.tilt}
              onChange={handleChange}
            />
          </label>
        </div>
      </div>

      <div className="control-section">
        <h3>
          <Clock size={13} /> Appliance Constraints
        </h3>
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <ApplianceBlock
            name="Dishwasher"
            power="1.5"
            enabledKey="dwEnabled"
            startKey="dwStart"
            endKey="dwEnd"
          />
          <ApplianceBlock
            name="Washing Machine"
            power="2.0"
            enabledKey="wmEnabled"
            startKey="wmStart"
            endKey="wmEnd"
          />
          <ApplianceBlock
            name="Water Heater"
            power="3.0"
            enabledKey="whEnabled"
            startKey="whStart"
            endKey="whEnd"
          />
        </div>
      </div>

      <button
        onClick={handleOptimize}
        disabled={loading}
        className="run-button"
      >
        {loading ? (
          "Processing AI..."
        ) : (
          <>
            <Play size={16} fill="currentColor" /> Run AI Optimization
          </>
        )}
      </button>
    </aside>
  );
}
