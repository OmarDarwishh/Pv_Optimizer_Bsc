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

  const handleOptimize = async () => {
    setLoading(true);

    // NEW PAYLOAD: Sends the 'enabled' toggles directly to Python
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

    try {
      const response = await axios.post(
        "http://localhost:8000/api/optimize",
        payload,
      );

      console.log("Python replied with:", response.data);
      setBackendData(response.data);
    } catch (error) {
      console.error("Connection failed! Is the Python server running?", error);
      alert("Failed to connect to Python backend.");
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
      />
      <MainArea results={backendData} />
    </div>
  );
}

export default App;
