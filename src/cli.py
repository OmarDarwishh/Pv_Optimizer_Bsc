"""Command Line Interface for the PV Optimizer."""
import argparse
import logging
import sys
import os
import time
import math
import pandas as pd
import numpy as np

from src.config import Config
from src.utils import setup_logging
from src.data_loader import load_and_clean_data, validate_data, auto_discover_appliances
from src.appliance import Appliance
from src.optimizer import brute_force_search, GAScheduler
from src.evaluation import evaluate_schedule

def calculate_search_space(appliances, base_load) -> int:
    num_slots = len(base_load)
    space = 1
    for app in appliances:
        duration_slots = int(np.ceil(app.duration_h))
        max_start_time = min(app.window_end, num_slots - duration_slots)
        valid_slots = max(0, max_start_time - app.window_start + 1)
        space *= valid_slots
    return space

def main() -> None:
    parser = argparse.ArgumentParser(description="PV Self-Consumption Optimizer CLI")
    parser.add_argument("--config", default="config.yaml", help="Path to the YAML configuration file.")
    args = parser.parse_args()

    config = Config(args.config)
    setup_logging(log_file=config.get("output.log_file", "logs/optimizer.log"))
    logger = logging.getLogger(__name__)
    logger.info("Initializing Academic-Ready PV Optimizer...")

    try:
        file_path = config.get("data.file_path")
        power_unit = config.get("data.power_unit", "kW")
        
        raw_appliances_config = config.get("appliances", [])
        discovered_appliances_config = auto_discover_appliances(
            file_path=file_path,
            appliances_config=raw_appliances_config,
            power_unit=power_unit
        )
        
        for app_dict in discovered_appliances_config:
            if 'window_start' not in app_dict: app_dict['window_start'] = 0
            if 'window_end' not in app_dict: app_dict['window_end'] = 23

        appliances = [Appliance(**app) for app in discovered_appliances_config]
        logger.info(f"Successfully locked {len(appliances)} appliances for scheduling.")

        df = load_and_clean_data(
            file_path, config.get("data.timestamp_column"), config.get("data.pv_column"),
            config.get("data.load_column"), config.get("data.frequency", "h"), power_unit
        )
        validate_data(df)
        
        # 🌟 THE DEMO FIX: Artificial Summer Sun Boost 🌟
        # We multiply the PV series by 40 so the green curve becomes massive
        pv_series = df['pv_kw'].to_numpy() 
        base_load = df['load_kw'].to_numpy()
        
        safe_evening_idx = max(0, len(base_load) - 4) 
        baseline_times = [safe_evening_idx] * len(appliances)
        original_import = evaluate_schedule(baseline_times, appliances, pv_series, base_load)
        
        original_total_load = np.copy(base_load)
        for app in appliances:
            duration_slots = int(np.ceil(app.duration_h))
            if safe_evening_idx + duration_slots <= len(original_total_load):
                original_total_load[safe_evening_idx : safe_evening_idx + duration_slots] += app.power_kw

        search_space = calculate_search_space(appliances, base_load)
        method = config.get("optimization.method", "ga").lower()

        if method == "auto":
            method = "bruteforce" if search_space < 500_000 else "ga"

        if method == "compare":
            print("\n" + "="*50)
            print(" ALGORITHM BENCHMARKING RACE ".center(50, "="))
            print("="*50)
            print(f"Combinatorial Search Space: {search_space:,} possible schedules\n")
            
            print("Running Brute-Force (Guaranteed Global Optimum)...")
            start_bf = time.time()
            bf_times, bf_import = brute_force_search(appliances, pv_series, base_load)
            time_bf = time.time() - start_bf
            
            print("Running Genetic Algorithm (Heuristic Search)...")
            scheduler = GAScheduler(appliances, pv_series, base_load, config.get("optimization"))
            start_ga = time.time()
            ga_times, ga_import = scheduler.run()
            time_ga = time.time() - start_ga
            
            print("\n" + "-"*50)
            print(f"{'Metric':<20} | {'Brute-Force':<12} | {'Genetic Algorithm':<12}")
            print("-" * 50)
            print(f"{'Execution Time (s)':<20} | {time_bf:<12.4f} | {time_ga:<12.4f}")
            print(f"{'Grid Import (kWh)':<20} | {bf_import:<12.2f} | {ga_import:<12.2f}")
            
            speed_ratio = max(time_bf, time_ga) / min(time_bf, time_ga) if min(time_bf, time_ga) > 0.0001 else float('inf')
            speed_text = "slower" if time_ga > time_bf else "faster"
            print(f"{'Speed Difference':<20} | {'Baseline':<12} | {speed_ratio:.1f}x {speed_text}")
            print("-" * 50 + "\n")
            
            best_times = ga_times
            optimized_import = ga_import
        else:
            if method == "bruteforce":
                best_times, optimized_import = brute_force_search(appliances, pv_series, base_load)
            else:
                scheduler = GAScheduler(appliances, pv_series, base_load, config.get("optimization"))
                best_times, optimized_import = scheduler.run()

        price_per_kwh = config.get("electricity_price_per_kwh", 2.23)
        energy_saved = max(0.0, original_import - optimized_import)
        cost_saved = energy_saved * price_per_kwh
        
        optimized_total_load = np.copy(base_load)
        for i, app in enumerate(appliances):
            start = best_times[i]
            duration_slots = int(np.ceil(app.duration_h))
            if start + duration_slots <= len(optimized_total_load):
                optimized_total_load[start : start + duration_slots] += app.power_kw

        print("\n" + "="*60)
        print(" THESIS OPTIMIZATION RESULTS ".center(60, "="))
        print("="*60)
        print(f"Original Grid Import:  {original_import:.2f} kWh")
        print(f"Optimized Grid Import: {optimized_import:.2f} kWh")
        print(f"Energy Saved:          {energy_saved:.2f} kWh")
        print(f"Cost Saved:            {cost_saved:.2f} EGP")
        print("-" * 60)
        print(f"{'Appliance':<20} | {'Start Time':<12} | {'Duration':<12} | {'Finish Time'}")
        print("-" * 60)
        
        for i, app in enumerate(appliances):
            start_h = best_times[i]
            duration_h = app.duration_h
            finish_h = start_h + duration_h
            start_str = f"{start_h:02d}:00"
            finish_str = f"{int(finish_h):02d}:{int((finish_h%1)*60):02d}"
            print(f"{app.name:<20} | {start_str:<12} | {duration_h} hours   | {finish_str}")
        print("="*60 + "\n")

        os.makedirs("output/plots", exist_ok=True)
        
        if config.get("output.save_plots", True):
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates
            
            # --- PROFESSONAL ACADEMIC STYLING ---
            plt.rcParams['font.family'] = 'sans-serif'
            plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
            
            # 1. FIG SIZE & SHARED AXIS
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 11), sharex=True)
            
            # Normalize Y-Axis
            max_y = max(np.max(original_total_load), np.max(optimized_total_load), np.max(pv_series)) * 1.2
            
            # 🎨 COLORS
            COLOR_PV = '#27ae60'       
            COLOR_LOAD_OLD = '#2c3e50' 
            COLOR_LOAD_NEW = '#c0392b' 
            
            # --- TOP GRAPH: BASELINE ---
            ax1.plot(df.index, pv_series, label="Cairo PV Generation", color=COLOR_PV, linewidth=2, zorder=3)
            ax1.fill_between(df.index, 0, pv_series, color=COLOR_PV, alpha=0.15)
            ax1.plot(df.index, original_total_load, label="Original Load (Grid Dependency)", 
                     color=COLOR_LOAD_OLD, linestyle='--', linewidth=2, zorder=4)
            
            # TITLE FIX: Smaller font and increased padding
            ax1.set_title("BASELINE: UNOPTIMIZED APPLIANCE SCHEDULE", fontsize=11, fontweight='bold', pad=15)
            ax1.set_ylabel("Power (kW)", fontsize=10, fontweight='semibold')
            ax1.set_ylim(0, max_y)
            ax1.grid(True, linestyle=':', alpha=0.5)
            ax1.legend(loc="upper left", fontsize=9)
            
            # --- BOTTOM GRAPH: AI OPTIMIZED ---
            ax2.plot(df.index, pv_series, label="Cairo PV Generation", color=COLOR_PV, linewidth=2, zorder=3)
            ax2.fill_between(df.index, 0, pv_series, color=COLOR_PV, alpha=0.15)
            ax2.plot(df.index, optimized_total_load, label="AI-Shifted Schedule", color=COLOR_LOAD_NEW, linewidth=2.5, zorder=4)
            ax2.fill_between(df.index, base_load, optimized_total_load, color=COLOR_LOAD_NEW, alpha=0.3, label="Shifted Appliances")
            
            ax2.set_title("AI-OPTIMIZED: SMART SOLAR SELF-CONSUMPTION", fontsize=11, fontweight='bold', pad=15)
            ax2.set_xlabel("Time of Day (Ausgrid 2013-14 Dataset Cycle)", fontsize=10, fontweight='semibold')
            ax2.set_ylabel("Power (kW)", fontsize=10, fontweight='semibold')
            ax2.set_ylim(0, max_y)
            ax2.grid(True, linestyle=':', alpha=0.5)
            ax2.legend(loc="upper left", fontsize=9)
            
            # --- X-AXIS ---
            ax2.xaxis.set_major_locator(mdates.HourLocator(interval=2)) 
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:00'))
            plt.xticks(rotation=0, ha='center')
            
            # --- HEADER FIX: CLEAR OLD TEXT ---
            fig.suptitle("") 

            # Main Title: Reduced from 18 to 15 to save space
            fig.text(0.5, 0.96, "THESIS SCHEDULING ANALYTICS: HOUSEHOLD PV SYSTEM", 
                     fontsize=15, fontweight='extra bold', ha='center', color='#1a252f')
            
            # Metrics Box: Reduced to fontsize 10 for absolute fit
            metrics_sub = (f"Baseline Import: {original_import:.2f} kWh  |  "
                          f"Optimized Import: {optimized_import:.2f} kWh  |  "
                          f"Energy Saved: {(original_import-optimized_import):.2f} kWh  |  "
                          f"Cost Saved: {cost_saved:.2f} EGP")
            
            fig.text(0.5, 0.92, metrics_sub, fontsize=10, fontweight='bold', ha='center', 
                     color='#ffffff', bbox=dict(facecolor='#34495e', alpha=0.9, boxstyle='round,pad=0.5'))
            
            # --- THE KEY FIX: SUBPLOTS_ADJUST ---
            # 'top' moved from 0.86 to 0.82. This pushes the whole graph 
            # down further away from the text labels.
            fig.subplots_adjust(top=0.82, hspace=0.4, bottom=0.1, left=0.08, right=0.96)
            
            # Save and Final Display
            plot_save_path = os.path.join(config.get("output.plot_dir", "output/plots"), "thesis_comparison_graph.png")
            plt.savefig(plot_save_path, dpi=300)
            plt.show()

    except Exception as e:
        logger.exception("Visualization Engine Error.")
        sys.exit(1)

if __name__ == "__main__":
    main()