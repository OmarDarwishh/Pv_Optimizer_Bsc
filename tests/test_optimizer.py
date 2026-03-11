import numpy as np
from src.appliance import Appliance
from src.optimizer import brute_force_search, GAScheduler

def test_brute_force_search():
    pv = np.array([0.0, 2.0, 0.0])
    base = np.array([0.0, 0.0, 0.0])
    app = Appliance("Test", power_kw=1.5, duration_h=1.0)
    
    # Best slot is obviously index 1 (where PV is 2.0)
    best_schedule, best_import = brute_force_search([app], pv, base)
    
    assert best_schedule == [1]
    assert best_import == 0.0

def test_ga_scheduler():
    pv = np.array([0.0, 2.0, 0.0, 0.0])
    base = np.array([0.0, 0.0, 0.0, 0.0])
    app = Appliance("Test", power_kw=1.5, duration_h=1.0)
    
    # Using a deterministic random_seed so the test passes reliably every single time
    config = {
        "ga": {
            "num_generations": 10, 
            "population_size": 20, 
            "keep_parents": 2,
            "random_seed": 42
        }
    }
    
    ga = GAScheduler([app], pv, base, config)
    best_schedule, best_import = ga.run()
    
    assert best_schedule == [1]
    assert best_import == 0.0