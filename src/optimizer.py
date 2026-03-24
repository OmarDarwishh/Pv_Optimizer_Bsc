"""Module containing rigorous optimization algorithms (Brute-force and GA)."""
import itertools
import numpy as np
import pygad
import logging
import math
from typing import List, Tuple, Dict, Any
from src.evaluation import evaluate_schedule
from src.appliance import Appliance

logger = logging.getLogger(__name__)

def get_valid_start_times(appliances: List[Appliance], num_slots: int) -> List[List[int]]:
    """Calculates valid start times strictly within the allowed windows."""
    valid_starts = []
    for app in appliances:
        duration_slots = int(np.ceil(app.duration_h))
        # Ensure it starts within the window AND finishes before the day ends
        max_start_time = min(app.window_end, num_slots - duration_slots)
        
        if app.window_start > max_start_time:
             raise ValueError(f"Appliance {app.name} cannot fit within its designated time window.")
             
        valid_starts.append(list(range(app.window_start, max_start_time + 1)))
    return valid_starts

def brute_force_search(appliances: List[Appliance], pv_series: np.ndarray, base_load: np.ndarray) -> Tuple[List[int], float]:
    logger.info("Starting brute-force optimization...")
    num_slots = len(base_load)
    
    # 🌟 NEW: Restrict search space using time windows
    valid_starts = get_valid_start_times(appliances, num_slots)
    
    search_space_size = math.prod([len(vs) for vs in valid_starts])
    logger.info(f"Brute-force search space (constrained by windows): {search_space_size} combinations.")
    
    if search_space_size > 10_000_000:
        logger.error("Search space too large for brute-force. Switch to GA.")
        raise MemoryError("Combinatorial explosion: Use the Genetic Algorithm instead.")
        
    all_combinations = itertools.product(*valid_starts)
    
    best_import = float('inf')
    best_schedule = []
    
    for combo in all_combinations:
        current_import = evaluate_schedule(list(combo), appliances, pv_series, base_load)
        if current_import < best_import:
            best_import = current_import
            best_schedule = list(combo)
            
    logger.info("Brute-force optimization complete.")
    return best_schedule, best_import

class GAScheduler:
    """Genetic Algorithm implementation built on top of PyGAD."""
    
    def __init__(self, appliances: List[Appliance], pv_series: np.ndarray, base_load: np.ndarray, config_dict: Dict[str, Any]) -> None:
        self.appliances = appliances
        self.pv_series = pv_series
        self.base_load = base_load
        self.config = config_dict
        
        # 🌟 NEW: Restrict GA gene space using time windows
        self.gene_space = get_valid_start_times(appliances, len(base_load))

    def fitness_func(self, ga_instance: pygad.GA, solution: List[int], solution_idx: int) -> float:
        int_solution = [int(val) for val in solution]
        grid_imp = evaluate_schedule(int_solution, self.appliances, self.pv_series, self.base_load)
        
        if grid_imp == float('inf'):
            return -999999.0  # Heavy penalty for invalid/out-of-bounds schedules
        return -grid_imp 

    def run(self) -> Tuple[List[int], float]:
        logger.info("Starting Genetic Algorithm optimization...")
        ga_params = self.config.get("ga", {})
        
        num_genes = len(self.appliances)
        mutation_percent = ga_params.get("mutation_percent", 10)
        mutations = max(1, int(num_genes * mutation_percent / 100))
        
        ga_instance = pygad.GA(
            num_generations=ga_params.get("num_generations", 200),
            num_parents_mating=ga_params.get("keep_parents", 2) * 2,
            fitness_func=self.fitness_func,
            sol_per_pop=ga_params.get("population_size", 100),
            num_genes=num_genes,
            gene_space=self.gene_space,
            gene_type=int,
            mutation_num_genes=mutations,
            crossover_type=ga_params.get("crossover_type", "single_point"),
            parent_selection_type=ga_params.get("parent_selection", "tournament"),
            keep_parents=ga_params.get("keep_parents", 2),
            random_seed=ga_params.get("random_seed", None),
            suppress_warnings=True
        )
        
        ga_instance.run()
        solution, solution_fitness, _ = ga_instance.best_solution()
        
        logger.info("GA optimization complete.")
        return [int(val) for val in solution], -float(solution_fitness)