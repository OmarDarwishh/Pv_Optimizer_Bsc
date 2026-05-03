"""Forecast-error sensitivity test.

Runs the GA once to lock the "perfect day" schedule, then re-evaluates that
*same* schedule against PV arrays scaled to 1.00, 0.85, and 0.70 — i.e. the
forecast over-estimated solar output by 0%, 15%, and 30% respectively.
"""
import os
import sys
import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import Config
from src.data_loader import load_and_clean_data
from src.appliance import Appliance
from src.optimizer import GAScheduler
from src.evaluation import evaluate_schedule
from app import calculate_egypt_daily_cost


def main():
    config = Config("config.yaml")

    df = load_and_clean_data(
        config.get("data.file_path"),
        config.get("data.timestamp_column"),
        config.get("data.pv_column"),
        config.get("data.load_column"),
        config.get("data.frequency", "h"),
        config.get("data.power_unit", "kW"),
    )

    pv_series = df["pv_kw"].to_numpy()[:24]
    base_load = df["load_kw"].to_numpy()[:24]

    raw_appliances = config.get("appliances", [])
    for d in raw_appliances:
        d["window_start"] = 0
        d["window_end"] = 24
    appliances = [Appliance(**a) for a in raw_appliances]

    print("=" * 70)
    print("STEP 1: Run GA on the perfect (forecast) PV profile to lock schedule")
    print("=" * 70)

    scheduler = GAScheduler(appliances, pv_series, base_load, config.get("optimization"))
    locked_times, optimized_import = scheduler.run()

    print(f"\nLocked schedule (start hour for each appliance):")
    for app, t in zip(appliances, locked_times):
        end = t + int(np.ceil(app.duration_h))
        print(f"  - {app.name:<18s} start={t:02d}:00  end={end:02d}:00  "
              f"(power={app.power_kw} kW, dur={app.duration_h} h)")

    print(f"\nGA-reported optimized grid import (perfect PV): {optimized_import:.4f} kWh")

    print("\n" + "=" * 70)
    print("STEP 2: Re-evaluate the LOCKED schedule under PV forecast errors")
    print("=" * 70)

    scenarios = [
        ("0%  Error (Baseline / Perfect Forecast)", 1.00),
        ("15% Error (Forecast over-estimated PV)",  0.85),
        ("30% Error (Forecast severely over-estimated PV)", 0.70),
    ]

    results = []
    for label, factor in scenarios:
        pv_scaled = pv_series * factor
        grid_kwh = evaluate_schedule(locked_times, appliances, pv_scaled, base_load)
        cost_egp = calculate_egypt_daily_cost(grid_kwh)
        results.append((label, factor, grid_kwh, cost_egp))

    print(f"\n{'Scenario':<55s} {'PV factor':>10s} {'Grid (kWh)':>12s} {'Cost (EGP)':>12s}")
    print("-" * 95)
    for label, factor, grid_kwh, cost_egp in results:
        print(f"{label:<55s} {factor:>10.2f} {grid_kwh:>12.2f} {cost_egp:>12.2f}")

    print("\n" + "=" * 70)
    print("THESIS-READY NUMBERS")
    print("=" * 70)
    base_grid = results[0][2]
    base_cost = results[0][3]
    for label, factor, grid_kwh, cost_egp in results:
        delta_grid = grid_kwh - base_grid
        delta_cost = cost_egp - base_cost
        err_pct = int(round((1.0 - factor) * 100))
        print(f"  {err_pct:>2d}% Error: Grid Import = {grid_kwh:.2f} kWh, "
              f"Cost = {cost_egp:.2f} EGP   "
              f"(d_grid = {delta_grid:+.2f} kWh, d_cost = {delta_cost:+.2f} EGP)")


if __name__ == "__main__":
    main()
