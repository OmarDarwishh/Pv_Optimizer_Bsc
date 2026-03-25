"""
Dynamic PV & Live Weather Integration Module
Fetches clear-sky irradiance (PVGIS) and live cloud-cover forecasts (Open-Meteo) 
to generate an ultra-realistic, weather-attenuated solar curve for tomorrow.
"""
import requests
import pandas as pd
import numpy as np
import os
import sys
import yaml
from datetime import datetime, timedelta

def fetch_and_fuse_dynamic_data():
    print("🌍 Initializing AI Weather & Solar Orchestrator...")

    # --- 1. LOAD HARDWARE CONFIGURATION ---
    try:
        with open("config.yaml", "r") as file:
            config = yaml.safe_load(file)
            pv_settings = config.get("pv_system", {})
    except Exception as e:
        print(f"❌ Error reading config.yaml: {e}")
        sys.exit(1)

    LATITUDE = pv_settings.get("latitude", 30.0333)
    LONGITUDE = pv_settings.get("longitude", 31.4833)
    SYSTEM_CAPACITY_KW = pv_settings.get("capacity_kw", 5.0)
    
    output_path = config.get("data", {}).get("file_path", "data/raw/dynamic_cairo_target.csv")
    ausgrid_path = "data/raw/ausgrid_target_day.csv"

    now = datetime.now()
    tomorrow = now + timedelta(days=1)
    target_date_str = tomorrow.strftime('%Y-%m-%d')
    
    print(f"📅 Target Optimization Date: {target_date_str}")

    # --- 2. FETCH CLEAR-SKY PHYSICS (PVGIS API) ---
    print("📡 Contacting European Commission (PVGIS) for Astronomical Baseline...")
    pvgis_url = "https://re.jrc.ec.europa.eu/api/v5_2/seriescalc"
    pvgis_params = {
        'lat': LATITUDE, 'lon': LONGITUDE, 'pvcalculation': 1,  
        'peakpower': SYSTEM_CAPACITY_KW, 'loss': pv_settings.get("loss_percent", 14),          
        'angle': pv_settings.get("tilt_angle", 30), 'aspect': pv_settings.get("azimuth", 0),     
        'outputformat': 'json', 'startyear': 2020, 'endyear': 2020
    }

    try:
        pvgis_res = requests.get(pvgis_url, params=pvgis_params)
        pvgis_res.raise_for_status()
        pvgis_data = pvgis_res.json()
    except Exception as e:
        print(f"❌ PVGIS API Failed: {e}")
        sys.exit(1)

    df_pv = pd.DataFrame(pvgis_data['outputs']['hourly'])
    df_pv['time'] = pd.to_datetime(df_pv['time'], format='%Y%m%d:%H%M')
    target_pv_day = df_pv[(df_pv['time'].dt.month == tomorrow.month) & (df_pv['time'].dt.day == tomorrow.day)]
    
    # Base clear-sky power (shifted to Cairo Local Time)
    pv_kw_clear_sky = np.roll((target_pv_day['P'] / 1000.0).values, 2)

    # --- 3. FETCH LIVE WEATHER FORECAST (OPEN-METEO API) ---
    print("☁️ Contacting Open-Meteo for Live Cloud Cover Forecast...")
    weather_url = "https://api.open-meteo.com/v1/forecast"
    weather_params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "hourly": "cloudcover",            # We only want the cloud percentage
        "timezone": "Africa/Cairo",        # Forces exact local time alignment
        "start_date": target_date_str,
        "end_date": target_date_str
    }

    try:
        weather_res = requests.get(weather_url, params=weather_params)
        weather_res.raise_for_status()
        weather_data = weather_res.json()
    except Exception as e:
        print(f"❌ Open-Meteo API Failed: {e}")
        sys.exit(1)

    # Array of 24 values (0 to 100%) representing hourly cloud cover
    cloud_cover_percent = np.array(weather_data['hourly']['cloudcover'])

    # --- 4. THE DATA FUSION (PHYSICS + WEATHER) ---
    print("🧠 Fusing Astronomical Data with Live Meteorological Forecast...")
    
    # Thesis Math: If cloud cover is 100%, solar generation drops by 75% (leaving 25% ambient light).
    # If cloud cover is 0%, solar generation remains at 100% of clear-sky capability.
    attenuation_factor = 1.0 - (cloud_cover_percent / 100.0) * 0.75
    
    # The final, realistic generation curve
    pv_kw_real = pv_kw_clear_sky * attenuation_factor

    # --- 5. MERGE WITH APPLIANCE LOAD & SAVE ---
    if not os.path.exists(ausgrid_path):
        print(f"❌ Error: Missing base load file {ausgrid_path}.")
        sys.exit(1)

    df_load = pd.read_csv(ausgrid_path)
    timestamps = pd.date_range(start=f"{target_date_str} 00:00:00", periods=24, freq='h')
    
    final_df = pd.DataFrame({
        'timestamp': timestamps,
        'pv_kw': pv_kw_real,
        'load_kw': df_load['load_kw'].values
    })

    final_df.to_csv(output_path, index=False)
    
    print("\n" + "="*50)
    print(f"✅ FINAL DATASET READY: {output_path}")
    print(f"🌤️  Clear-Sky Peak: {pv_kw_clear_sky.max():.2f} kW")
    print(f"🌧️  Weather-Attenuated Peak: {pv_kw_real.max():.2f} kW")
    print("="*50 + "\n")

if __name__ == "__main__":
    fetch_and_fuse_dynamic_data()