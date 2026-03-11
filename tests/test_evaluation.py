import numpy as np
from src.evaluation import grid_import, self_consumption, self_sufficiency, savings, evaluate_schedule
from src.appliance import Appliance

def test_grid_import():
    load = np.array([2.0, 1.0, 3.0])
    pv = np.array([1.0, 2.0, 0.0])
    # Hour 1: 1.0 import, Hour 2: 0.0 import, Hour 3: 3.0 import = 4.0 total
    assert grid_import(load, pv) == 4.0

def test_evaluate_schedule():
    pv = np.array([1.0, 1.0, 1.0, 1.0])
    base_load = np.array([0.0, 0.0, 0.0, 0.0])
    app = Appliance("Test", power_kw=2.0, duration_h=1.0)
    
    # Run appliance at hour 0. Total load = 2.0. Net load = 1.0. 
    result = evaluate_schedule([0], [app], pv, base_load)
    assert result == 1.0

def test_evaluate_schedule_out_of_bounds():
    pv = np.array([1.0, 1.0])
    base_load = np.array([0.0, 0.0])
    app = Appliance("Test", power_kw=1.0, duration_h=2.0)
    
    # Trying to start a 2h appliance at index 1 goes out of bounds
    assert evaluate_schedule([1], [app], pv, base_load) == float('inf')