"""Extracts a feature-rich, single-day minutely dataset for the optimizer."""
import pandas as pd
import os

def create_target_day():
    print("Extracting a feature-rich, single-day dataset from HomeC...")
    input_path = "data/raw/HomeC.csv"
    output_path = "data/raw/target_day.csv"
    
    if not os.path.exists(input_path):
        print(f"Error: Could not find {input_path}")
        return

    # Load and clean timestamps
    df = pd.read_csv(input_path, low_memory=False)
    df['time'] = pd.to_numeric(df['time'], errors='coerce')
    df = df.dropna(subset=['time'])
    df['timestamp'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('timestamp', inplace=True)
    df.sort_index(inplace=True)
    df = df[~df.index.duplicated(keep='first')]

    # Ensure PV is numeric to find a sunny day
    df['gen [kW]'] = pd.to_numeric(df['gen [kW]'], errors='coerce').fillna(0)
    daily_max = df['gen [kW]'].resample('D').max()
    sunny_days = daily_max[daily_max > 1.5]
    
    target_date = sunny_days.index[0].strftime('%Y-%m-%d') if not sunny_days.empty else df.index[0].strftime('%Y-%m-%d')
    print(f"Selected Date: {target_date}")

    # Extract just that day
    day_df = df.loc[target_date].copy()

    # Rename ONLY the core columns so Universal Loader catches them easily
    day_df.rename(columns={'gen [kW]': 'pv_kw', 'use [kW]': 'load_kw'}, inplace=True)

    # Save the MINUTELY data (with all 30+ appliance columns completely intact!)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    day_df.to_csv(output_path, date_format='%Y-%m-%d %H:%M:%S')
    print(f"✅ Rich minutely dataset saved to {output_path}")

if __name__ == "__main__":
    create_target_day()