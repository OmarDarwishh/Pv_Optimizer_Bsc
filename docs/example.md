# Example Walkthrough

This document explains the provided `example.csv` dataset and the expected results.

## The Scenario

We have a household with a rooftop PV system.

- **Baseline:** The homeowner usually turns on the Dishwasher (1.5 kW for 1 hr) and Washing Machine (2.0 kW for 1.5 hr) when they get home from work at 18:00.
- **The Problem:** At 18:00, the sun is setting, and PV generation is almost zero. This forces the house to draw expensive power from the grid.

## The Optimization

By running `pv-optimizer`, the Genetic Algorithm searches for the best time slots to run these appliances autonomously during the day.

### Expected Results

The console will output something similar to:

```text
========================================
       🏆 OPTIMIZATION RESULTS 🏆
========================================
Method Used:           GA
Original Grid Import:  10.20 kWh
Optimized Grid Import: 6.70 kWh
Total Monetary Savings:€0.98
Self-Consumption:      45.0% -> 68.5%
----------------------------------------
Optimal Appliance Start Times:
  ⚡ Dishwasher      : Hour 10:00 (was 18:00)
  ⚡ Washing Machine : Hour 12:00 (was 18:00)
========================================
```
