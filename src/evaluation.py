"""Module for calculating energy metrics and evaluating optimization schedules."""
import numpy as np
from typing import List
from src.appliance import Appliance

def grid_import(load_series: np.ndarray, pv_series: np.ndarray) -> float:
    """
    Calculates total energy imported from the grid.

    Args:
        load_series (np.ndarray): Array of total household load in kW.
        pv_series (np.ndarray): Array of PV generation in kW.

    Returns:
        float: Total grid import in kWh.
    """
    net_load = load_series - pv_series
    return float(np.sum(np.maximum(net_load, 0.0)))

def self_consumption(pv_series: np.ndarray, load_series: np.ndarray) -> float:
    """
    Calculates the self-consumption ratio (consumed PV / total PV generated).

    Args:
        pv_series (np.ndarray): Array of PV generation in kW.
        load_series (np.ndarray): Array of total household load in kW.

    Returns:
        float: Self-consumption ratio [0.0 to 1.0].
    """
    total_pv = np.sum(pv_series)
    if total_pv <= 0.0:
        return 0.0
    consumed_pv = np.sum(np.minimum(pv_series, load_series))
    return float(consumed_pv / total_pv)

def self_sufficiency(pv_series: np.ndarray, load_series: np.ndarray) -> float:
    """
    Calculates the self-sufficiency ratio (consumed PV / total household load).

    Args:
        pv_series (np.ndarray): Array of PV generation in kW.
        load_series (np.ndarray): Array of total household load in kW.

    Returns:
        float: Self-sufficiency ratio [0.0 to 1.0].
    """
    total_load = np.sum(load_series)
    if total_load <= 0.0:
        return 1.0
    consumed_pv = np.sum(np.minimum(pv_series, load_series))
    return float(consumed_pv / total_load)

def savings(original_import: float, optimized_import: float, price_per_kwh: float) -> float:
    """
    Calculates monetary savings achieved by the optimization.

    Args:
        original_import (float): Grid import before optimization (kWh).
        optimized_import (float): Grid import after optimization (kWh).
        price_per_kwh (float): Cost of electricity per kWh.

    Returns:
        float: Total monetary savings.
    """
    return float((original_import - optimized_import) * price_per_kwh)

def evaluate_schedule(
    start_times: List[int], 
    appliances: List[Appliance], 
    pv_series: np.ndarray, 
    base_load: np.ndarray
) -> float:
    """
    Evaluates a specific schedule of appliance start times.

    Args:
        start_times (List[int]): Proposed start indices for each appliance.
        appliances (List[Appliance]): List of Appliance objects to schedule.
        pv_series (np.ndarray): Array of PV generation.
        base_load (np.ndarray): Array of non-shiftable household load.

    Returns:
        float: The total grid import in kWh. Returns infinity if the schedule 
               violates time boundaries (e.g., appliance runs past midnight).
    """
    total_load = np.copy(base_load)
    max_slots = len(total_load)
    
    for i, app in enumerate(appliances):
        start_idx = int(start_times[i])
        duration_slots = int(np.ceil(app.duration_h))
        
        # Hard constraint: Appliance must finish within the day
        if start_idx + duration_slots > max_slots:
            return float('inf')
            
        total_load[start_idx : start_idx + duration_slots] += app.power_kw
        
    return grid_import(total_load, pv_series)