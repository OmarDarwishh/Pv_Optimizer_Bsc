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
from src.evaluation import evaluate_schedule, savings, self_consumption

def calculate_search_space(appliances, base_load) -> int:
    """Calculates the total combinatorial search space O(S^N)."""
    num_slots = len(base_load)
    space = 1
    for app in appliances:
        max_start = num_slots - int(np.ceil(app.duration_h))
        space *= (max_start + 1) if max_start >= 0 else 0
    return space

def main() -> None:
    parser = argparse.ArgumentParser(description="PV Self-Consumption Optimizer CLI")
    parser.add_argument("--config", default="config.yaml", help="Path to the YAML configuration file.")
    args = parser.parse_args()

    config = Config(args.config)
    setup_logging(log_file=config.get("output.log_file", "logs/optimizer.log"))
    logger = logging.getLogger(__name__)
    logger.info("Initializing Production-Ready PV Optimizer...")

    try:
        file_path = config.get("data.file_path")
        power_unit = config.get("data.power_unit", "kW")
        
        # Phase 8: Auto-Discovery
        raw_appliances_config = config.get("appliances", [])
        discovered_appliances_config = auto_discover_appliances(
            file_path=file_path,
            appliances_config=raw_appliances_config,
            power_unit=power_unit
        )
        
        appliances = [Appliance(**app) for app in discovered_appliances_config]
        logger.info(f"Successfully locked {len(appliances)} appliances for scheduling.")

        # Load and clean data
        df = load_and_clean_data(
            file_path,
            config.get("data.timestamp_column"),
            config.get("data.pv_column"),
            config.get("data.load_column"),
            config.get("data.frequency", "h"),
            power_unit
        )
        validate_data(df)
        
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

        # PHASE 9: Smart Routing & Benchmarking
        search_space = calculate_search_space(appliances, base_load)
        method = config.get("optimization.method", "ga").lower()

        if method == "auto":
            if search_space < 500_000:
                logger.info(f"Search space small ({search_space:,}). Auto-routing to BRUTE-FORCE.")
                method = "bruteforce"
            else:
                logger.info(f"Search space massive ({search_space:,}). Auto-routing to GENETIC ALGORITHM.")
                method = "ga"

        if method == "compare":
            print("\n" + "="*50)
            print(" ALGORITHM BENCHMARKING RACE ".center(50, "="))
            print("="*50)
            print(f"Combinatorial Search Space: {search_space:,} possible schedules\n")
            
            # Race Brute-Force
            print("Running Brute-Force (Guaranteed Global Optimum)...")
            start_bf = time.time()
            bf_times, bf_import = brute_force_search(appliances, pv_series, base_load)
            time_bf = time.time() - start_bf
            
            # Race GA
            print("Running Genetic Algorithm (Heuristic Search)...")
            scheduler = GAScheduler(appliances, pv_series, base_load, config.get("optimization"))
            start_ga = time.time()
            ga_times, ga_import = scheduler.run()
            time_ga = time.time() - start_ga
            
            # Output Comparison Table for Thesis
            print("\n" + "-"*50)
            print(f"{'Metric':<20} | {'Brute-Force':<12} | {'Genetic Algorithm':<12}")
            print("-" * 50)
            print(f"{'Execution Time (s)':<20} | {time_bf:<12.4f} | {time_ga:<12.4f}")
            print(f"{'Grid Import (kWh)':<20} | {bf_import:<12.2f} | {ga_import:<12.2f}")
            
            # Math safe speed calculation
            if min(time_bf, time_ga) > 0.0001:
                speed_ratio = max(time_bf, time_ga) / min(time_bf, time_ga)
            else:
                speed_ratio = float('inf') # Handles near-instant execution
                
            speed_text = "slower" if time_ga > time_bf else "faster"
            print(f"{'Speed Difference':<20} | {'Baseline':<12} | {speed_ratio:.1f}x {speed_text}")
            print("-" * 50 + "\n")
            
            logger.info("Benchmarking complete. Exiting program.")
            sys.exit(0)

        # Standard Execution Path
        if method == "bruteforce":
            best_times, optimized_import = brute_force_search(appliances, pv_series, base_load)
        else:
            scheduler = GAScheduler(appliances, pv_series, base_load, config.get("optimization"))
            best_times, optimized_import = scheduler.run()
            
        price_per_kwh = config.get("electricity_price_per_kwh", 0.28)
        money_saved = savings(original_import, optimized_import, price_per_kwh)
        
        optimized_total_load = np.copy(base_load)
        for i, app in enumerate(appliances):
            start = best_times[i]
            duration_slots = int(np.ceil(app.duration_h))
            if start + duration_slots <= len(optimized_total_load):
                optimized_total_load[start : start + duration_slots] += app.power_kw

        sc_original = self_consumption(pv_series, original_total_load)
        sc_optimized = self_consumption(pv_series, optimized_total_load)

        print("\n" + "="*40)
        print(" OPTIMIZATION RESULTS ".center(40, "="))
        print("="*40)
        print(f"Method Used:           {method.upper()}")
        print(f"Original Grid Import:  {original_import:.2f} kWh")
        print(f"Optimized Grid Import: {optimized_import:.2f} kWh")
        print(f"Total Monetary Savings:€{money_saved:.2f}")
        print(f"Self-Consumption:      {sc_original*100:.1f}% -> {sc_optimized*100:.1f}%")
        print("-" * 40)
        print("Optimal Appliance Start Times:")
        for i, app in enumerate(appliances):
            print(f"  * {app.name:<16} ({app.power_kw}kW): Hour {best_times[i]:02d}:00 (was {safe_evening_idx:02d}:00)")
        print("="*40 + "\n")

        os.makedirs("output", exist_ok=True)
        
        results_df = pd.DataFrame({
            "Appliance": [app.name for app in appliances],
            "Power_kW": [app.power_kw for app in appliances],
            "Duration_h": [app.duration_h for app in appliances],
            "Baseline_Start": baseline_times,
            "Optimized_Start": best_times
        })
        results_file = config.get("output.results_file", "output/results.csv")
        results_df.to_csv(results_file, index=False)

        if config.get("output.save_plots", True):
            from src.plotting import plot_schedule
            
            plot_dir = config.get("output.plot_dir", "output/plots")
            plot_format = config.get("output.plot_format", "png")
            plot_save_path = os.path.join(plot_dir, "load_comparison")
            
            plot_schedule(
                timestamps=df.index,
                pv_series=pv_series,
                original_load=original_total_load,
                optimized_load=optimized_total_load,
                save_path=plot_save_path,
                plot_format=plot_format
            )

    except Exception as e:
        logger.exception("A fatal error occurred during the optimization sequence.")
        sys.exit(1)

if __name__ == "__main__":
    main()