"""Universal ETL module for loading, cleaning, and discovering time-series energy data."""
import pandas as pd
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

def load_and_clean_data(
    file_path: str, 
    timestamp_col: str, 
    pv_col: str, 
    load_col: str, 
    freq: str = 'h',
    power_unit: str = 'kW'
) -> pd.DataFrame:
    """Universally loads and sanitizes household energy CSVs."""
    logger.info(f"Initiating Universal Data Mapper for: {file_path}")
    
    try:
        df = pd.read_csv(file_path, low_memory=False)
    except Exception as e:
        logger.error(f"Failed to read file {file_path}: {e}")
        raise

    required_cols = [timestamp_col, pv_col, load_col]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise KeyError(f"Missing required columns in CSV: {missing_cols}")

    sample_val = df[timestamp_col].dropna().iloc[0]
    try:
        if isinstance(sample_val, (int, float)) or (isinstance(sample_val, str) and sample_val.replace('.', '', 1).isdigit()):
            numeric_time = pd.to_numeric(df[timestamp_col], errors='coerce')
            df['timestamp'] = pd.to_datetime(numeric_time, unit='s')
        else:
            df['timestamp'] = pd.to_datetime(df[timestamp_col], errors='coerce')
    except Exception as e:
        raise ValueError(f"Unrecognized timestamp format in column '{timestamp_col}'.")

    df = df.dropna(subset=['timestamp'])
    df.set_index('timestamp', inplace=True)
    df.sort_index(inplace=True)
    df = df[~df.index.duplicated(keep='first')]

    df['pv_kw'] = pd.to_numeric(df[pv_col], errors='coerce')
    df['load_kw'] = pd.to_numeric(df[load_col], errors='coerce')
    clean_df = df[['pv_kw', 'load_kw']].copy()

    if power_unit.upper() == 'W':
        clean_df['pv_kw'] = clean_df['pv_kw'] / 1000.0
        clean_df['load_kw'] = clean_df['load_kw'] / 1000.0

    hourly_df = clean_df.resample(freq).mean()
    hourly_df = hourly_df.interpolate(method='linear', limit=2).fillna(0)
    hourly_df['pv_kw'] = hourly_df['pv_kw'].clip(lower=0.0)
    hourly_df['load_kw'] = hourly_df['load_kw'].clip(lower=0.0)

    return hourly_df

def validate_data(df: pd.DataFrame) -> None:
    """Hard validation to ensure the dataset is mathematically ready."""
    if df.empty:
        raise ValueError("Dataset is completely empty after cleaning.")
    if df.isna().any().any():
        raise ValueError("Critical failure: NaNs survived the cleaning pipeline.")

def auto_discover_appliances(
    file_path: str, 
    appliances_config: List[Dict], 
    power_unit: str = 'kW',
    threshold_kw: float = 0.5  # FIX: Increased from 0.2 to 0.5 to aggressively kill phantom power
) -> List[Dict]:
    """Scans the raw CSV to dynamically calculate real-world appliance power and duration."""
    logger.info("Scanning dataset for auto-discovery of appliance hardware parameters...")
    
    try:
        df = pd.read_csv(file_path, low_memory=False)
    except Exception:
        logger.warning("Auto-discovery failed to open CSV. Using YAML defaults.")
        return appliances_config

    updated_appliances = []

    for app in appliances_config:
        app_name = app.get("name")
        matching_cols = [col for col in df.columns if app_name.lower() in col.lower()]
        
        if not matching_cols:
            logger.info(f"  - {app_name}: No sensor data found. Using YAML defaults ({app['power_kw']}kW, {app['duration_h']}h).")
            updated_appliances.append(app)
            continue
            
        target_col = matching_cols[0]
        app_data = pd.to_numeric(df[target_col], errors='coerce').dropna()
        
        if power_unit.upper() == 'W':
            app_data = app_data / 1000.0
            
        active_periods = app_data[app_data > threshold_kw]
        
        if active_periods.empty:
            logger.info(f"  - {app_name}: Did not run heavily in this dataset. Using YAML defaults.")
            updated_appliances.append(app)
            continue
            
        avg_power = round(float(active_periods.mean()), 2)
        
        # Estimate duration based on total active rows
        estimated_duration_h = round(len(active_periods) / 60.0, 2)
        
        # 🌟 REALITY CHECK FILTER 🌟
        # If high-frequency sensor data inflates the time, cap standard appliances at 3.0 hours max
        max_allowed_h = 3.0
        if estimated_duration_h > max_allowed_h:
            logger.warning(f"  - {app_name}: Sensor reported {estimated_duration_h}h. Capping to {max_allowed_h}h (Sensor Noise Filter applied).")
            estimated_duration_h = max_allowed_h

        estimated_duration_h = max(0.25, estimated_duration_h) 

        logger.info(f"  - {app_name} [AUTO-DETECTED]: Overriding YAML -> Power: {avg_power} kW, Duration: {estimated_duration_h} h")
        
        app["power_kw"] = avg_power
        app["duration_h"] = estimated_duration_h
        updated_appliances.append(app)
        
    return updated_appliances