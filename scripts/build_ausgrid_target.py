import pandas as pd
import numpy as np
import os
import sys

def build_ausgrid_dataset():
    print("🚀 Initializing Ausgrid Data Extraction...")
    
    input_path = "data/raw/ausgrid_data.csv"
    output_path = "data/raw/ausgrid_target_day.csv"

    if not os.path.exists(input_path):
        print(f"❌ Error: {input_path} not found.")
        sys.exit(1)

    print("Reading Ausgrid database... (skipping disclaimer row)")
    try:
        # 1. FIX: Skip the first row so we get the real headers
        df = pd.read_csv(input_path, low_memory=False, skiprows=1)
        
        # Normalize column names
        df.columns = [c.strip().lower() for c in df.columns]
        
        # 2. Find the ID column
        id_col = None
        for col in ['customer', 'id', 'nmi']:
            if col in df.columns:
                id_col = col
                break
        
        if not id_col:
            print(f"❌ Error: ID column missing. Found: {list(df.columns[:10])}...")
            sys.exit(1)

        print(f"Using ID column: '{id_col}'")

        # 3. Filter for first customer
        first_cust = df[id_col].iloc[0]
        df_c1 = df[df[id_col] == first_cust].copy()
        
        # 4. Find Category Column
        cat_col = None
        for col in ['consumption category', 'category', 'type']:
            if col in df.columns:
                cat_col = col
                break
        
        if not cat_col:
            print("❌ Error: Could not find Category column.")
            sys.exit(1)

        # Split Base Load (GC) and Solar (GG)
        gc_df = df_c1[df_c1[cat_col].str.contains('GC', na=False)].copy()
        gg_df = df_c1[df_c1[cat_col].str.contains('GG', na=False)].copy()

        if gc_df.empty or gg_df.empty:
            print("❌ Error: Could not find both Load (GC) and Solar (GG) data.")
            sys.exit(1)

        # 5. Extract time columns (usually 0:30 to 0:00)
        # These are the columns after 'date' (usually index 5 onwards)
        time_cols = [c for c in df.columns if (':' in c or c.isdigit())]
        
        if len(time_cols) < 48:
            # Fallback: take the 48 columns after the 'date' column
            date_idx = df.columns.get_loc('date')
            time_cols = df.columns[date_idx + 1 : date_idx + 49]

        print(f"Extracting 48 half-hour columns...")

        # 6. Find the sunniest day
        gg_df['daily_total_pv'] = gg_df[time_cols].apply(pd.to_numeric, errors='coerce').sum(axis=1)
        best_day_row = gg_df.sort_values(by='daily_total_pv', ascending=False).iloc[0]
        best_date = best_day_row['date']
        
        print(f"🎯 Peak Solar Day Found: {best_date}")

        # 7. Extract 48 half-hour values
        pv_half_hourly = gg_df[gg_df['date'] == best_date][time_cols].values[0].astype(float)
        load_half_hourly = gc_df[gc_df['date'] == best_date][time_cols].values[0].astype(float)

        # 8. Convert 48 half-hours (kWh) into 24 hourly values (kW)
        pv_hourly_kw = pv_half_hourly.reshape(24, 2).sum(axis=1)
        load_hourly_kw = load_half_hourly.reshape(24, 2).sum(axis=1)

        # 9. Final Clean Dataframe
        timestamps = pd.date_range(start="2026-01-01 00:00:00", periods=24, freq='h')
        final_df = pd.DataFrame({
            'timestamp': timestamps,
            'pv_kw': pv_hourly_kw,
            'load_kw': load_hourly_kw
        })

        final_df.to_csv(output_path, index=False)
        print(f"✅ Success! Ausgrid target day saved to: {output_path}")

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    build_ausgrid_dataset()