# app.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import traceback
import yaml
import os
import sys
import numpy as np
import pandas as pd

# Add the root directory to Python's path so it can find your 'src' folder
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import your actual thesis modules
from scripts.fetch_forecast_data import fetch_and_fuse_dynamic_data
from src.pv_physics_engine import fetch_and_simulate_nasa_power
from src.config import Config
from src.data_loader import load_and_clean_data
from src.appliance import Appliance
from src.optimizer import GAScheduler, InfeasibleScheduleError, validate_appliance_constraints
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
    enabled: bool
    window_start: int
    window_end: int

class Appliances(BaseModel):
    dishwasher: AppConfig
    washing_machine: AppConfig
    water_heater: AppConfig

class PVSystem(BaseModel):
    azimuth: int
    tilt: int
    capacity_kw: float

class OptimizationPayload(BaseModel):
    pv_system: PVSystem
    appliances: Appliances

# NEW PAYLOAD FOR NASA SIMULATION (Includes Date)
class SimulationPayload(OptimizationPayload):
    target_date: str = "20230615" # Default to a mid-summer day for testing

def calculate_egypt_daily_cost(daily_kwh: float, tariff_cfg: dict | None = None) -> float:
    """Cumulative-marginal Egyptian residential tariff.

    Each bracket charges its rate ONLY on the kWh that fall inside its
    [previous_limit, limit_kwh] window. The previous implementation mixed
    cumulative and flat-on-total brackets, which produced large
    discontinuities (e.g. a +260 EGP jump at 351 kWh). This is the
    standard EEHC residential schedule interpretation.

    Brackets are read from config.yaml (`electricity_tariff.brackets`)
    so rates can be updated when EEHC publishes a new schedule without
    code changes. The final bracket carries `limit_kwh: null` (unbounded).
    """
    if tariff_cfg is None:
        with open("config.yaml", "r") as f:
            tariff_cfg = yaml.safe_load(f).get("electricity_tariff", {})

    brackets = tariff_cfg.get("brackets", [])
    if not brackets:
        raise ValueError("electricity_tariff.brackets missing from config.yaml")

    monthly_kwh = max(0.0, daily_kwh) * 30.0
    cost = 0.0
    prev_limit = 0.0
    remaining = monthly_kwh

    for bracket in brackets:
        if remaining <= 0:
            break
        limit = bracket.get("limit_kwh")
        rate = float(bracket["rate"])
        if limit is None:
            cost += remaining * rate
            remaining = 0.0
            break
        bracket_size = float(limit) - prev_limit
        kwh_in_bracket = min(remaining, bracket_size)
        cost += kwh_in_bracket * rate
        remaining -= kwh_in_bracket
        prev_limit = float(limit)

    return cost / 30.0

def update_config_from_payload(payload):
    with open("config.yaml", "r") as file:
        config_data = yaml.safe_load(file)
        
    config_data["pv_system"]["azimuth"] = payload.pv_system.azimuth
    config_data["pv_system"]["tilt"] = payload.pv_system.tilt
    config_data["pv_system"]["capacity_kw"] = payload.pv_system.capacity_kw
    
    strict_appliances = []
    if payload.appliances.dishwasher.enabled:
        strict_appliances.append({
            "name": "Dishwasher", "power_kw": 1.5, "duration_h": 2.0,
            "window_start": payload.appliances.dishwasher.window_start,
            "window_end": payload.appliances.dishwasher.window_end
        })
    if payload.appliances.washing_machine.enabled:
        strict_appliances.append({
            "name": "Washing Machine", "power_kw": 2.0, "duration_h": 1.5,
            "window_start": payload.appliances.washing_machine.window_start,
            "window_end": payload.appliances.washing_machine.window_end
        })
    if payload.appliances.water_heater.enabled:
        strict_appliances.append({
            "name": "Water Heater", "power_kw": 3.0, "duration_h": 3.0,
            "window_start": payload.appliances.water_heater.window_start,
            "window_end": payload.appliances.water_heater.window_end
        })
            
    config_data["appliances"] = strict_appliances
            
    with open("config.yaml", "w") as file:
        yaml.dump(config_data, file, default_flow_style=False)

def run_core_algorithm(pv_series, base_load, timestamps):
    """Shared GA optimizer pipeline for both forecast and historical endpoints.

    Raises HTTPException(422) when any appliance's time window is too narrow
    for its duration. The error body lists every offending appliance so the
    UI can show all problems at once.
    """
    config = Config("config.yaml")

    raw_appliances = config.get("appliances", [])
    for d in raw_appliances:
        if 'window_start' not in d: d['window_start'] = 0
        if 'window_end' not in d: d['window_end'] = 24
    appliances = [Appliance(**a) for a in raw_appliances]

    # Pre-flight feasibility check. If a user sets e.g. a 3-hour Dishwasher
    # but a 7-9 AM window, we surface that as a structured 422 BEFORE
    # spending any time on the optimizer.
    constraint_errors = validate_appliance_constraints(appliances, num_slots=len(base_load))
    if constraint_errors:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "infeasible_schedule",
                "message": "One or more appliance windows are too narrow for the configured cycle duration.",
                "errors": constraint_errors,
            },
        )

    safe_evening_idx = max(0, len(base_load) - 4)
    baseline_times = [safe_evening_idx] * len(appliances)
    original_import = evaluate_schedule(baseline_times, appliances, pv_series, base_load)

    try:
        scheduler = GAScheduler(appliances, pv_series, base_load, config.get("optimization"))
        best_times, optimized_import = scheduler.run()
    except InfeasibleScheduleError as exc:
        # Defense in depth -- should already have been caught above.
        raise HTTPException(
            status_code=422,
            detail={
                "code": "infeasible_schedule",
                "message": str(exc),
                "errors": exc.errors,
            },
        )

    original_daily_cost = calculate_egypt_daily_cost(original_import)
    optimized_daily_cost = calculate_egypt_daily_cost(optimized_import)
    cost_saved = max(0.0, original_daily_cost - optimized_daily_cost)

    optimized_total_load = np.copy(base_load)
    appliance_schedules = [] 
    
    for i, app_obj in enumerate(appliances):
        start_idx = best_times[i]
        duration_slots = int(np.ceil(app_obj.duration_h))
        end_idx = min(start_idx + duration_slots, len(timestamps) - 1)
        
        if start_idx + duration_slots <= len(optimized_total_load):
            optimized_total_load[start_idx : start_idx + duration_slots] += app_obj.power_kw
            
        appliance_schedules.append({
            "name": app_obj.name,
            "start": timestamps[start_idx],
            "end": timestamps[end_idx]
        })

    total_pv = pv_series.sum()
    base_pv_consumed = np.minimum(pv_series, base_load).sum()
    base_sc = (base_pv_consumed / total_pv) * 100 if total_pv > 0 else 0

    opt_pv_consumed = np.minimum(pv_series, optimized_total_load).sum()
    opt_sc = (opt_pv_consumed / total_pv) * 100 if total_pv > 0 else 0

    return {
        "status": "success",
        "kpis": {
            "original_import": round(original_import, 2),
            "optimized_import": round(optimized_import, 2),
            "cost_saved": round(cost_saved, 2),
            "self_consumption": round(opt_sc, 1),
            "base_sc": round(base_sc, 1)
        },
        "schedules": appliance_schedules,
        "charts": {
            "timestamps": timestamps,
            "pv_generation": pv_series.round(2).tolist(),
            "base_load": base_load.round(2).tolist(),
            "load_profile": optimized_total_load.round(2).tolist()
        }
    }


# ==========================================
# ROUTE 1: DAY-AHEAD FORECAST (pvlib clear-sky x Open-Meteo clouds)
# ==========================================
@app.post("/api/optimize/live")
async def run_forecast_optimization(payload: OptimizationPayload):
    print("\n--- DAY-AHEAD CLEAR-SKY + OPEN-METEO FORECAST TRIGGERED ---")
    update_config_from_payload(payload)
    
    fetch_and_fuse_dynamic_data()
    
    config = Config("config.yaml")
    df = load_and_clean_data(
        config.get("data.file_path"), config.get("data.timestamp_column"), 
        config.get("data.pv_column"), config.get("data.load_column"), 
        config.get("data.frequency", "h"), config.get("data.power_unit", "kW")
    )
    
    pv_series = df['pv_kw'].to_numpy()
    base_load = df['load_kw'].to_numpy()
    timestamps = [f"{i:02d}:00" for i in range(24)]
    
    return run_core_algorithm(pv_series, base_load, timestamps)


# ==========================================
# ROUTE 2: THE HISTORICAL SIMULATOR (NASA)
# ==========================================
@app.post("/api/optimize/simulate")
async def run_nasa_simulation(payload: SimulationPayload):
    print(f"\n--- HISTORICAL NASA SIMULATION TRIGGERED ({payload.target_date}) ---")
    try:
        update_config_from_payload(payload)
        config = Config("config.yaml")

        # 1. Fetch 15-min Data from NASA (lat/lon from config — same geometry as forecast path)
        df_15min = fetch_and_simulate_nasa_power(
            lat=config.get("pv_system.latitude", 30.0444),
            lon=config.get("pv_system.longitude", 31.2357),
            capacity_kw=payload.pv_system.capacity_kw,
            tilt=payload.pv_system.tilt, azimuth=payload.pv_system.azimuth,
            start_date=payload.target_date, end_date=payload.target_date
        )

        # 2. Resample to 1-Hour averages to match base_load array size perfectly
        df_hourly = df_15min.resample('1h').mean()
        pv_series = df_hourly['ac_power_kw'].fillna(0).to_numpy()[:24]

        # 3. Load the standard Base Load
        df_base = load_and_clean_data(
            config.get("data.file_path"), config.get("data.timestamp_column"),
            config.get("data.pv_column"), config.get("data.load_column"),
            config.get("data.frequency", "h"), config.get("data.power_unit", "kW")
        )
        base_load = df_base['load_kw'].to_numpy()[:24]
        timestamps = [f"{i:02d}:00" for i in range(24)]

        # 4. Pass the NASA solar data to the same Genetic Algorithm
        return run_core_algorithm(pv_series, base_load, timestamps)
    except HTTPException:
        # Pass structured API errors (e.g. 422 infeasibility) through unchanged.
        raise
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"NASA simulation failed: {exc}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)