# app.py
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import yaml
import os
import sys
import numpy as np
import pandas as pd

# Add the root directory to Python's path so it can find your 'src' folder
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import your actual thesis modules!
from scripts.fetch_pvgis_data import fetch_and_fuse_dynamic_data
from src.config import Config
from src.data_loader import load_and_clean_data, auto_discover_appliances
from src.appliance import Appliance
from src.optimizer import GAScheduler
from src.evaluation import evaluate_schedule

app = FastAPI(title="PV Optimizer AI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AppConfig(BaseModel):
    window_start: int
    window_end: int

class Appliances(BaseModel):
    dishwasher: AppConfig
    washing_machine: AppConfig

class PVSystem(BaseModel):
    azimuth: int
    tilt: int
    capacity_kw: float

class OptimizationPayload(BaseModel):
    pv_system: PVSystem
    appliances: Appliances

# --- THESIS FEATURE: EGYPTIAN TIERED PRICING ---
def calculate_egypt_daily_cost(daily_kwh: float) -> float:
    monthly_kwh = daily_kwh * 30
    cost = 0.0
    if monthly_kwh <= 50:
        cost = monthly_kwh * 0.68
    elif monthly_kwh <= 100:
        cost = (50 * 0.68) + ((monthly_kwh - 50) * 0.78)
    elif monthly_kwh <= 200:
        cost = monthly_kwh * 0.95
    elif monthly_kwh <= 350:
        cost = (200 * 0.95) + ((monthly_kwh - 200) * 1.55)
    elif monthly_kwh <= 650:
        cost = (200 * 0.95) + (150 * 1.55) + ((monthly_kwh - 350) * 1.95)
    elif monthly_kwh <= 1000:
        cost = monthly_kwh * 2.10
    else:
        cost = monthly_kwh * 2.23
    return cost / 30.0 

@app.post("/api/optimize")
async def run_optimization(payload: OptimizationPayload):
    print("\n--- 🟢 REAL AI OPTIMIZATION TRIGGERED ---")
    
    # 1. UPDATE CONFIG WITH UI SLIDERS
    with open("config.yaml", "r") as file:
        config_data = yaml.safe_load(file)
        
    config_data["pv_system"]["azimuth"] = payload.pv_system.azimuth
    config_data["pv_system"]["tilt"] = payload.pv_system.tilt
    config_data["pv_system"]["capacity_kw"] = payload.pv_system.capacity_kw
    
    for app_data in config_data["appliances"]:
        if app_data["name"] == "Dishwasher":
            app_data["window_start"] = payload.appliances.dishwasher.window_start
            app_data["window_end"] = payload.appliances.dishwasher.window_end
        elif app_data["name"] == "Washing Machine":
            app_data["window_start"] = payload.appliances.washing_machine.window_start
            app_data["window_end"] = payload.appliances.washing_machine.window_end
            
    with open("config.yaml", "w") as file:
        yaml.dump(config_data, file, default_flow_style=False)

    # 2. FETCH LIVE WEATHER & PV PHYSICS
    print("Fetching live PVGIS and Open-Meteo data...")
    fetch_and_fuse_dynamic_data()

    # 3. RUN THE REAL THESIS ENGINE
    print("Executing Genetic Algorithm Optimizer...")
    config = Config("config.yaml")
    file_path = config.get("data.file_path")
    power_unit = config.get("data.power_unit", "kW")

    # Load Data
    raw_appliances = config.get("appliances", [])
    discovered = auto_discover_appliances(file_path, raw_appliances, power_unit)
    for d in discovered:
        if 'window_start' not in d: d['window_start'] = 0
        if 'window_end' not in d: d['window_end'] = 23
    appliances = [Appliance(**a) for a in discovered]

    df = load_and_clean_data(
        file_path, config.get("data.timestamp_column"), config.get("data.pv_column"),
        config.get("data.load_column"), config.get("data.frequency", "h"), power_unit
    )
    
    pv_series = df['pv_kw'].to_numpy()
    base_load = df['load_kw'].to_numpy()

    # Baseline calculations
    safe_evening_idx = max(0, len(base_load) - 4)
    baseline_times = [safe_evening_idx] * len(appliances)
    original_import = evaluate_schedule(baseline_times, appliances, pv_series, base_load)

    # Run PyGAD Genetic Algorithm
    scheduler = GAScheduler(appliances, pv_series, base_load, config.get("optimization"))
    best_times, optimized_import = scheduler.run()

    # Economic Evaluation
    original_daily_cost = calculate_egypt_daily_cost(original_import)
    optimized_daily_cost = calculate_egypt_daily_cost(optimized_import)
    cost_saved = max(0.0, original_daily_cost - optimized_daily_cost)

    # Build the Optimized Load Array for the Chart
    optimized_total_load = np.copy(base_load)
    for i, app_obj in enumerate(appliances):
        start = best_times[i]
        duration_slots = int(np.ceil(app_obj.duration_h))
        if start + duration_slots <= len(optimized_total_load):
            optimized_total_load[start : start + duration_slots] += app_obj.power_kw

    # Calculate Self-Consumption KPI
    total_pv = pv_series.sum()
    opt_pv_consumed = np.minimum(pv_series, optimized_total_load).sum()
    opt_sc = (opt_pv_consumed / total_pv) * 100 if total_pv > 0 else 0

    # Extract clean timestamps from pandas index
    try:
        timestamps = pd.to_datetime(df.index).dt.strftime('%H:00').tolist()
    except:
        timestamps = [f"{i:02d}:00" for i in range(24)]

    print("Optimization Complete! Sending real data to React.")

    # 4. SEND REAL DATA TO REACT
    return {
        "status": "success",
        "kpis": {
            "original_import": round(original_import, 2),
            "optimized_import": round(optimized_import, 2),
            "cost_saved": round(cost_saved, 2),
            "self_consumption": round(opt_sc, 1)
        },
        "charts": {
            "timestamps": timestamps,
            "pv_generation": pv_series.round(2).tolist(),
            "load_profile": optimized_total_load.round(2).tolist()
        }
    }