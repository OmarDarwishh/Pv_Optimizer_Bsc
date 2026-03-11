"""Module for generating high-quality, publication-ready visualizations."""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import os
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)

def plot_schedule(
    timestamps: pd.DatetimeIndex, 
    pv_series: np.ndarray, 
    original_load: np.ndarray, 
    optimized_load: np.ndarray, 
    save_path: Optional[str] = None, 
    plot_format: str = 'png'
) -> None:
    """
    Plots the PV generation curve alongside the original and optimized load profiles.
    
    Args:
        timestamps (pd.DatetimeIndex): The time index for the x-axis.
        pv_series (np.ndarray): Array of PV generation values (kW).
        original_load (np.ndarray): Array of the baseline household load (kW).
        optimized_load (np.ndarray): Array of the optimized household load (kW).
        save_path (Optional[str]): Path (without extension) to save the figure.
        plot_format (str): Format to save the figure (e.g., 'png', 'pdf').
    """
    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
    # Set a clean, academic style
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Plot PV Generation (Green)
    ax.plot(timestamps, pv_series, label="PV Generation", color='#2ca02c', linewidth=2)
    ax.fill_between(timestamps, 0, pv_series, color='#2ca02c', alpha=0.15)
    
    # Plot Original Load (Blue, Dashed)
    ax.plot(timestamps, original_load, label="Original Load", color='#1f77b4', linestyle='--', linewidth=1.5)
    
    # Plot Optimized Load (Red, Solid)
    ax.plot(timestamps, optimized_load, label="Optimized Load", color='#d62728', linewidth=2)
    
    # Highlight the remaining grid import (where optimized load exceeds PV)
    ax.fill_between(
        timestamps, 
        pv_series, 
        optimized_load, 
        where=(optimized_load > pv_series), 
        color='#d62728', 
        alpha=0.25, 
        label="Grid Import (Optimized)"
    )
    
    # Formatting
    ax.set_title("Household Load Profile: Baseline vs. Optimized Schedule", fontsize=14, fontweight='bold', pad=15)
    ax.set_xlabel("Time of Day", fontsize=12, labelpad=10)
    ax.set_ylabel("Power (kW)", fontsize=12, labelpad=10)
    ax.legend(loc="upper right", frameon=True, shadow=True)
    
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    if save_path:
        full_path = f"{save_path}.{plot_format}"
        # Save at 300 DPI for thesis print quality
        plt.savefig(full_path, format=plot_format, dpi=300, bbox_inches='tight')
        logger.info(f"Plot saved successfully to {full_path}")
    
    plt.close(fig)