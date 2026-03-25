"""
Dynamic PV Integration Module
Fetches localized solar irradiance based on dynamic YAML hardware configurations.
"""
import requests
import pandas as pd
import numpy as np
import os
import sys
import yaml
from datetime import datetime, timedelta

def fetch_and_fuse_dynamic_data():
    print("🌍 Initializing Predictive Solar Engine...")

    # --- 1. LOAD DYNAMIC HARDWARE CONFIGURATION ---
    try:
        with open("config.yaml", "r") as file:
            config = yaml.safe_load(file)
            pv_settings = config.get("pv_system", {})
    except Exception as e:
        print(f"❌ Error reading config.yaml: {e}")
        sys.exit(1)

    # Extract parameters, with fallbacks just in case
    LATITUDE = pv_settings.get("latitude", 30.0333)
    LONGITUDE = pv_settings.get("longitude", 31.4833)
    SYSTEM_CAPACITY_KW = pv_settings.get("capacity_kw", 5.0)
    LOSS = pv_settings.get("loss_percent", 14)
    TILT = pv_settings.get("tilt_angle", 30)
    AZIMUTH = pv_settings.get("azimuth", 0)

    output_path = config.get("data", {}).get("file_path", "data/raw/dynamic_cairo_target.csv")
    ausgrid_path = "data/raw/ausgrid_target_day.csv"

    # --- 2. DYNAMIC TIME HORIZON ---
    now = datetime.now()
    tomorrow = now + timedelta(days=1)
    target_month = tomorrow.month
    target_day = tomorrow.day
    
    print(f"📅 Target Optimization Date: {tomorrow.strftime('%B %d, %Y')}")
    print(f"⚙️  Hardware: {SYSTEM_CAPACITY_KW}kWp | Tilt: {TILT}° | Azimuth: {AZIMUTH}°")

    # --- 3. API REQUEST TO PVGIS ---
    url = "https://re.jrc.ec.europa.eu/api/v5_2/seriescalc"
    
    params = {
        'lat': LATITUDE,
        'lon': LONGITUDE,
        'pvcalculation': 1,  
        'peakpower': SYSTEM_CAPACITY_KW,
        'loss': LOSS,          
        'angle': TILT,         
        'aspect': AZIMUTH,     # Dynamically passes the roof direction
        'outputformat': 'json',
        'startyear': 2020,   
        'endyear': 2020
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ API Connection Failed: {e}")
        sys.exit(1)

    # --- 4. PROCESS PV DATA ---
    hourly_data = data['outputs']['hourly']
    df_pv = pd.DataFrame(hourly_data)
    
    if 'P' not in df_pv.columns:
        print(f"❌ API Error: 'P' (Power) column missing.")
        sys.exit(1)
        
    df_pv['time'] = pd.to_datetime(df_pv['time'], format='%Y%m%d:%H%M')
    
    df_pv['month'] = df_pv['time'].dt.month
    df_pv['day'] = df_pv['time'].dt.day
    target_pv_day = df_pv[(df_pv['month'] == target_month) & (df_pv['day'] == target_day)].copy()
    
    pv_kw_utc = (target_pv_day['P'] / 1000.0).values
    pv_kw_local = np.roll(pv_kw_utc, 2)

    # --- 5. FUSE WITH AUTHENTIC LOAD ---
    if not os.path.exists(ausgrid_path):
        print(f"❌ Error: Missing base load file {ausgrid_path}.")
        sys.exit(1)

    df_load = pd.read_csv(ausgrid_path)
    base_load_kw = df_load['load_kw'].values

    start_timestamp = f"{tomorrow.strftime('%Y-%m-%d')} 00:00:00"
    timestamps = pd.date_range(start=start_timestamp, periods=24, freq='h')
    
    final_df = pd.DataFrame({
        'timestamp': timestamps,
        'pv_kw': pv_kw_local,
        'load_kw': base_load_kw
    })

    final_df.to_csv(output_path, index=False)
    print(f"✅ Success! Predictive dataset ready at: {output_path}")

if __name__ == "__main__":
    fetch_and_fuse_dynamic_data()