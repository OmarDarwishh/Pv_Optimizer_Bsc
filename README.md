PV Self-Consumption Optimizer using Smart Appliance Scheduling
📌 Project Overview
This repository contains a dynamic, dual-API Smart Home Energy Management System (HEMS) designed to maximize household solar self-consumption. By orchestrating astronomical solar physics, live meteorological forecasts, and combinatorial optimization algorithms, the system intelligently schedules heavy appliance loads to align with localized solar generation windows.

This project was developed as a comprehensive thesis for a B.Sc. in Computer Engineering, demonstrating advanced systems design, data fusion, and algorithmic benchmarking.

✨ Core Architecture & Features
Dual-API Environmental Orchestration:

PVGIS Integration: Calculates precise Plane of Array (POA) clear-sky irradiance based on user-defined hardware parameters (Latitude, Longitude, Panel Capacity, Tilt, and Azimuth).

Open-Meteo Integration: Fetches live, localized 24-hour cloud cover forecasts to mathematically attenuate the clear-sky baseline, generating an ultra-realistic, weather-adjusted solar curve.

Dynamic Constraint-Based Scheduling:

Users define appliance power profiles, durations, and strict operational time windows via a decoupled config.yaml interface.

Algorithmic Routing & Benchmarking:

The engine calculates the combinatorial search space in real-time.

Brute-Force Engine: Automatically deployed for constrained spaces (<500k combinations) to guarantee the Global Optimum in milliseconds.

Genetic Algorithm (GA): A heuristic solver deployed for massive search spaces to find near-optimal local minimums without resource exhaustion.

Economic Penalty Avoidance:

Encodes the official 2024/2025 Egyptian Ministry of Electricity tiered tariff system. The optimizer actively schedules loads to prevent households from crossing critical monthly consumption thresholds (e.g., the 650 kWh "Reset to Zero" penalty trap), preserving government subsidies.

🚀 Quick Start

1. Clone and Install

Bash
git clone https://github.com/yourusername/Pv_Optimizer_Vol1.git
cd Pv_Optimizer_Vol1
pip install -r requirements.txt 2. Configure Hardware & Appliances
Edit config.yaml to set your specific roof geometry and appliance constraints:

YAML
pv_system:
capacity_kw: 5.0
tilt_angle: 30
azimuth: 0 # South
appliances:

- name: "Washing Machine"
  power_kw: 2.0
  duration_h: 1.5
  window_start: 9
  window_end: 15

3. Run the Dual-API Orchestrator
   Fetch tomorrow's astronomy and weather forecast:

Bash
python scripts/fetch_pvgis_data.py 4. Execute the Optimizer

Bash
pv-optimizer
📊 Output Analytics
The system generates terminal-based algorithmic benchmarking and a high-resolution Matplotlib visualization comparing the baseline grid dependency against the AI-shifted schedule, detailing Self-Consumption (SC) and Self-Sufficiency (SS) KPIs.
