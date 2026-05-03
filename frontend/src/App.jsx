import React, { useState, useEffect } from "react";
import axios from "axios";
import { AlertTriangle, AlertCircle, X, Clock } from "lucide-react";
import Sidebar from "./components/Sidebar";
import MainArea from "./components/MainArea";
import "./App.css";

const pad2 = (n) => String(n).padStart(2, "0");

// Translate any thrown axios error into a structured object that the
// <Toast/> component can render — instead of dumping `[object Object]`
// into a browser alert.
function buildToastFromError(error) {
  // Network failure: no response object at all
  if (!error.response) {
    return {
      severity: "error",
      title: "Can't reach the optimizer",
      message:
        "The Python backend isn't responding. Make sure uvicorn is running on port 8000, then try again.",
    };
  }

  const status = error.response.status;
  const detail = error.response.data?.detail;

  // Structured infeasibility (HTTP 422 from /api/optimize/*)
  if (
    status === 422 &&
    typeof detail === "object" &&
    detail?.code === "infeasible_schedule" &&
    Array.isArray(detail.errors)
  ) {
    return {
      severity: "warning",
      title: "Time windows need adjustment",
      message:
        detail.errors.length > 1
          ? `${detail.errors.length} appliances can't fit inside their selected time windows. Please widen the windows or shorten the cycles, then try again.`
          : "One appliance can't fit inside its selected time window. Please widen the window or shorten the cycle, then try again.",
      items: detail.errors.map((e) => ({
        appliance: e.appliance,
        window: `${pad2(e.window_start)}:00 – ${pad2(e.window_end)}:00`,
        needed: e.duration_h,
        available: e.available_h,
      })),
    };
  }

  // Generic backend error with string detail
  const msg =
    typeof detail === "string"
      ? detail
      : error.response.statusText || "An unexpected error occurred.";
  return {
    severity: "error",
    title: `Backend error (${status})`,
    message: msg,
  };
}

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
  const [toast, setToast] = useState(null);

  const closeToast = () => setToast(null);

  // Allow Esc to dismiss the toast.
  useEffect(() => {
    if (!toast) return undefined;
    const onKey = (e) => {
      if (e.key === "Escape") closeToast();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [toast]);

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
      setToast(buildToastFromError(error));
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
      {toast && <Toast toast={toast} onClose={closeToast} />}
    </div>
  );
}

function Toast({ toast, onClose }) {
  const Icon = toast.severity === "warning" ? AlertTriangle : AlertCircle;
  return (
    <div
      className="toast-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="toast-title"
      onClick={onClose}
    >
      <div
        className={`toast-modal toast-modal--${toast.severity}`}
        onClick={(e) => e.stopPropagation()}
      >
        <button
          className="toast-modal__close"
          aria-label="Close"
          onClick={onClose}
        >
          <X size={18} />
        </button>

        <div className="toast-modal__head">
          <div className="toast-modal__icon">
            <Icon size={22} />
          </div>
          <div className="toast-modal__title-block">
            <h3 id="toast-title" className="toast-modal__title">
              {toast.title}
            </h3>
            <p className="toast-modal__message">{toast.message}</p>
          </div>
        </div>

        {toast.items && toast.items.length > 0 && (
          <ul className="toast-modal__list">
            {toast.items.map((item, idx) => (
              <li key={idx} className="toast-modal__item">
                <span className="toast-modal__item-name">{item.appliance}</span>
                <span className="toast-modal__item-detail">
                  <Clock size={13} aria-hidden="true" />
                  Window&nbsp;<strong>{item.window}</strong>&nbsp;allows{" "}
                  <strong>{item.available}h</strong> — needs{" "}
                  <strong>{item.needed}h</strong>
                </span>
              </li>
            ))}
          </ul>
        )}

        <div className="toast-modal__footer">
          <button className="toast-modal__action" onClick={onClose}>
            Got it
          </button>
        </div>
      </div>
    </div>
  );
}

export default App;
