import React from "react";
import { Clock, Sun, Play, Power } from "lucide-react";

export default function Sidebar({
  config,
  setConfig,
  handleOptimize,
  loading,
}) {
  const handleChange = (e) => {
    const { name, value } = e.target;
    setConfig((prev) => ({ ...prev, [name]: Number(value) }));
  };

  // NEW: Helper function to toggle the enabled state
  const toggleAppliance = (appKey) => {
    setConfig((prev) => ({ ...prev, [appKey]: !prev[appKey] }));
  };

  // NEW: Reusable UI block for appliances with the ON/OFF switch
  const ApplianceBlock = ({ name, power, enabledKey, startKey, endKey }) => {
    const isEnabled = config[enabledKey];
    return (
      <div
        style={{
          background: "#1e293b",
          padding: "16px",
          borderRadius: "8px",
          borderLeft: isEnabled ? "4px solid #10b981" : "4px solid #334155",
          transition: "all 0.3s",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: "12px",
          }}
        >
          <p
            style={{
              fontSize: "0.85rem",
              color: isEnabled ? "#f8fafc" : "#94a3b8",
              fontWeight: "bold",
            }}
          >
            {name} ({power} kW)
          </p>
          <button
            onClick={() => toggleAppliance(enabledKey)}
            style={{
              background: isEnabled ? "#059669" : "transparent",
              border: isEnabled ? "none" : "1px solid #475569",
              color: isEnabled ? "#fff" : "#94a3b8",
              padding: "4px 10px",
              borderRadius: "12px",
              fontSize: "0.7rem",
              fontWeight: "bold",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "4px",
            }}
          >
            <Power size={12} /> {isEnabled ? "ON" : "OFF"}
          </button>
        </div>

        {/* Fades out and disables inputs when OFF */}
        <div
          style={{
            display: "flex",
            gap: "10px",
            opacity: isEnabled ? 1 : 0.4,
            pointerEvents: isEnabled ? "auto" : "none",
            transition: "opacity 0.3s",
          }}
        >
          <label style={{ fontSize: "0.75rem", color: "#94a3b8", flex: 1 }}>
            Start After:
            <input
              type="number"
              name={startKey}
              min="0"
              max="23"
              value={config[startKey]}
              onChange={handleChange}
              style={{
                width: "100%",
                padding: "4px",
                background: "#0f172a",
                color: "white",
                border: "1px solid #334155",
                borderRadius: "4px",
                marginTop: "4px",
              }}
            />
          </label>
          <label style={{ fontSize: "0.75rem", color: "#94a3b8", flex: 1 }}>
            Finish By:
            <input
              type="number"
              name={endKey}
              min="0"
              max="23"
              value={config[endKey]}
              onChange={handleChange}
              style={{
                width: "100%",
                padding: "4px",
                background: "#0f172a",
                color: "white",
                border: "1px solid #334155",
                borderRadius: "4px",
                marginTop: "4px",
              }}
            />
          </label>
        </div>
      </div>
    );
  };

  return (
    <aside className="sidebar">
      <div className="brand">
        <h2>HEMS Optimizer</h2>
        <p>PV Self-Consumption System</p>
      </div>

      <div className="control-section">
        <h3 style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <Sun size={16} /> Hardware Configuration
        </h3>
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "12px",
            background: "#1e293b",
            padding: "16px",
            borderRadius: "8px",
          }}
        >
          <label style={{ fontSize: "0.85rem", color: "#94a3b8" }}>
            Roof Azimuth ({config.azimuth}°{" "}
            {config.azimuth === 0
              ? "South"
              : config.azimuth > 0
                ? "West"
                : "East"}
            )
            <input
              type="range"
              name="azimuth"
              min="-90"
              max="90"
              step="15"
              value={config.azimuth}
              onChange={handleChange}
              style={{ width: "100%", marginTop: "8px" }}
            />
          </label>
          <label style={{ fontSize: "0.85rem", color: "#94a3b8" }}>
            Panel Tilt ({config.tilt}°)
            <input
              type="range"
              name="tilt"
              min="0"
              max="90"
              step="5"
              value={config.tilt}
              onChange={handleChange}
              style={{ width: "100%", marginTop: "8px" }}
            />
          </label>
        </div>
      </div>

      <div className="control-section">
        <h3 style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <Clock size={16} /> Appliance Constraints
        </h3>
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "16px",
          }}
        >
          {/* We now dynamically render all 3 appliances! */}
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
        style={{
          background: loading ? "#334155" : "#10b981",
          color: "#fff",
          border: "none",
          padding: "12px",
          borderRadius: "6px",
          fontWeight: "bold",
          cursor: loading ? "not-allowed" : "pointer",
          marginTop: "auto",
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          gap: "8px",
        }}
      >
        {loading ? (
          "Processing AI..."
        ) : (
          <>
            <Play size={18} /> Run AI Optimization
          </>
        )}
      </button>
    </aside>
  );
}
