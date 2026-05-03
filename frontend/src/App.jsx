import React, { useState } from "react";
import axios from "axios";
import Sidebar from "./components/Sidebar";
import MainArea from "./components/MainArea";
import "./App.css";

function App() {
  // NEW STATE: Added 'enabled' flags and the Water Heater defaults
  const [config, setConfig] = useState({
    azimuth: 0,
    tilt: 30,
    capacity: 5.0,
    dwEnabled: true,
    dwStart: 10,
    dwEnd: 16,
    wmEnabled: true,
    wmStart: 9,
    wmEnd: 15,
    whEnabled: true,
    whStart: 0,
    whEnd: 12,
  });

  const [loading, setLoading] = useState(false);
  const [backendData, setBackendData] = useState(null);

  // "live"     → PVGIS + Open-Meteo day-ahead forecast
  // "nasa"     → NASA POWER + pvlib historical simulation
  // "compare"  → run BOTH in parallel and overlay the two PV curves for validation
  const [dataMode, setDataMode] = useState("live");

  // Historical Analog Day: month/day is always "tomorrow" (computed at submit time).
  // Only the year is user-selectable — defaults to last year.
  const [targetYear, setTargetYear] = useState(
    () => new Date().getFullYear() - 1,
  );

  // Compute tomorrow's calendar day overlaid on the chosen year → "YYYYMMDD" for NASA.
  const buildAnalogDate = () => {
    const d = new Date();
    d.setDate(d.getDate() + 1); // tomorrow's month/day
    d.setFullYear(targetYear); // overlay the selected past year
    return d.toISOString().slice(0, 10).replace(/-/g, "");
  };

  const handleOptimize = async () => {
    setLoading(true);

    const payload = {
      pv_system: {
        azimuth: config.azimuth,
        tilt: config.tilt,
        capacity_kw: config.capacity,
      },
      appliances: {
        dishwasher: {
          enabled: config.dwEnabled,
          window_start: config.dwStart,
          window_end: config.dwEnd,
        },
        washing_machine: {
          enabled: config.wmEnabled,
          window_start: config.wmStart,
          window_end: config.wmEnd,
        },
        water_heater: {
          enabled: config.whEnabled,
          window_start: config.whStart,
          window_end: config.whEnd,
        },
      },
    };

    const LIVE_URL = "http://localhost:8000/api/optimize/live";
    const NASA_URL = "http://localhost:8000/api/optimize/simulate";

    try {
      if (dataMode === "compare") {
        // Fire both endpoints in parallel, then merge: Live provides the primary
        // result (KPIs, schedules, base_load); NASA's PV curve is attached as an overlay.
        const nasaPayload = { ...payload, target_date: buildAnalogDate() };
        const [liveRes, nasaRes] = await Promise.all([
          axios.post(LIVE_URL, payload),
          axios.post(NASA_URL, nasaPayload),
        ]);

        const merged = {
          ...liveRes.data,
          charts: {
            ...liveRes.data.charts,
            pv_compare: nasaRes.data.charts.pv_generation,
          },
          compare: {
            live_kpis: liveRes.data.kpis,
            nasa_kpis: nasaRes.data.kpis,
          },
        };
        setBackendData(merged);
      } else if (dataMode === "nasa") {
        payload.target_date = buildAnalogDate();
        const response = await axios.post(NASA_URL, payload);
        setBackendData(response.data);
      } else {
        const response = await axios.post(LIVE_URL, payload);
        setBackendData(response.data);
      }
    } catch (error) {
      console.error("Backend call failed:", error);
      const detail =
        error.response?.data?.detail ||
        error.response?.statusText ||
        error.message ||
        "Unknown error";
      alert(
        error.response
          ? `Backend returned ${error.response.status}: ${detail}`
          : `Failed to reach Python backend (${detail}). Is uvicorn running on :8000?`,
      );
    }

    setLoading(false);
  };

  return (
    <div className="dashboard-layout">
      <Sidebar
        config={config}
        setConfig={setConfig}
        handleOptimize={handleOptimize}
        loading={loading}
        dataMode={dataMode}
        setDataMode={setDataMode}
        targetYear={targetYear}
        setTargetYear={setTargetYear}
      />
      <MainArea results={backendData} />
    </div>
  );
}

export default App;
