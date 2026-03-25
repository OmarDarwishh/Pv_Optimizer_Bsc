import React, { useState } from "react";
import axios from "axios"; // IMPORT AXIOS HERE
import Sidebar from "./components/Sidebar";
import MainArea from "./components/MainArea";
import "./App.css";

function App() {
  const [config, setConfig] = useState({
    azimuth: 0,
    tilt: 30,
    capacity: 5.0,
    dwStart: 10,
    dwEnd: 16,
    wmStart: 9,
    wmEnd: 15,
  });

  const [loading, setLoading] = useState(false);

  // NEW STATE: We need somewhere to store the data Python sends back
  const [backendData, setBackendData] = useState(null);

  const handleOptimize = async () => {
    setLoading(true);

    const payload = {
      pv_system: {
        azimuth: config.azimuth,
        tilt: config.tilt,
        capacity_kw: config.capacity,
      },
      appliances: {
        dishwasher: { window_start: config.dwStart, window_end: config.dwEnd },
        washing_machine: {
          window_start: config.wmStart,
          window_end: config.wmEnd,
        },
      },
    };

    try {
      // THE BRIDGE: Shoot the payload to Python over Port 8000
      const response = await axios.post(
        "http://localhost:8000/api/optimize",
        payload,
      );

      console.log("Python replied with:", response.data);
      setBackendData(response.data); // Save the results!
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
      {/* We pass the data down to the MainArea to be displayed */}
      <MainArea results={backendData} />
    </div>
  );
}

export default App;
