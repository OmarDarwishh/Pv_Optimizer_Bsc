import React from "react";
import { Clock, Sun, Play } from "lucide-react";

export default function Sidebar({
  config,
  setConfig,
  handleOptimize,
  loading,
}) {
  // This helper updates the specific value in our config object
  const handleChange = (e) => {
    const { name, value } = e.target;
    setConfig((prev) => ({ ...prev, [name]: Number(value) }));
  };

  return (
    <aside className="sidebar">
      <div className="brand">
        <h2>HEMS Optimizer</h2>
        <p>PV Self-Consumption System</p>
      </div>

      {/* Hardware Sliders */}
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

      {/* Appliance Windows */}
      <div className="control-section">
        <h3 style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <Clock size={16} /> Appliance Constraints
        </h3>
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "16px",
            background: "#1e293b",
            padding: "16px",
            borderRadius: "8px",
          }}
        >
          <div>
            <p
              style={{
                fontSize: "0.85rem",
                color: "#f8fafc",
                marginBottom: "8px",
                fontWeight: "bold",
              }}
            >
              Dishwasher (1.5 kW)
            </p>
            <div style={{ display: "flex", gap: "10px" }}>
              <label style={{ fontSize: "0.75rem", color: "#94a3b8", flex: 1 }}>
                Start After:
                <input
                  type="number"
                  name="dwStart"
                  min="0"
                  max="23"
                  value={config.dwStart}
                  onChange={handleChange}
                  style={{
                    width: "100%",
                    padding: "4px",
                    background: "#0f172a",
                    color: "white",
                    border: "1px solid #334155",
                    borderRadius: "4px",
                  }}
                />
              </label>
              <label style={{ fontSize: "0.75rem", color: "#94a3b8", flex: 1 }}>
                Finish By:
                <input
                  type="number"
                  name="dwEnd"
                  min="0"
                  max="23"
                  value={config.dwEnd}
                  onChange={handleChange}
                  style={{
                    width: "100%",
                    padding: "4px",
                    background: "#0f172a",
                    color: "white",
                    border: "1px solid #334155",
                    borderRadius: "4px",
                  }}
                />
              </label>
            </div>
          </div>

          <div>
            <p
              style={{
                fontSize: "0.85rem",
                color: "#f8fafc",
                marginBottom: "8px",
                fontWeight: "bold",
              }}
            >
              Washing Machine (2.0 kW)
            </p>
            <div style={{ display: "flex", gap: "10px" }}>
              <label style={{ fontSize: "0.75rem", color: "#94a3b8", flex: 1 }}>
                Start After:
                <input
                  type="number"
                  name="wmStart"
                  min="0"
                  max="23"
                  value={config.wmStart}
                  onChange={handleChange}
                  style={{
                    width: "100%",
                    padding: "4px",
                    background: "#0f172a",
                    color: "white",
                    border: "1px solid #334155",
                    borderRadius: "4px",
                  }}
                />
              </label>
              <label style={{ fontSize: "0.75rem", color: "#94a3b8", flex: 1 }}>
                Finish By:
                <input
                  type="number"
                  name="wmEnd"
                  min="0"
                  max="23"
                  value={config.wmEnd}
                  onChange={handleChange}
                  style={{
                    width: "100%",
                    padding: "4px",
                    background: "#0f172a",
                    color: "white",
                    border: "1px solid #334155",
                    borderRadius: "4px",
                  }}
                />
              </label>
            </div>
          </div>
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
