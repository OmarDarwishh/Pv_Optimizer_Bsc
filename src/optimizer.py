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

def brute_force_search(
    appliances: List[Appliance], 
    pv_series: np.ndarray, 
    base_load: np.ndarray
) -> Tuple[List[int], float]:
    """
    Evaluates all possible appliance start combinations to find the absolute optimum.
    
    Args:
        appliances (List[Appliance]): Appliances to schedule.
        pv_series (np.ndarray): PV generation array.
        base_load (np.ndarray): Base household load array.
        
    Returns:
        Tuple[List[int], float]: Best start times and the resulting grid import.
        
    Raises:
        MemoryError: If the search space exceeds 10 million combinations.
    """
    logger.info("Starting brute-force optimization...")
    num_slots = len(base_load)
    valid_starts = []
    
    for app in appliances:
        max_start = num_slots - int(np.ceil(app.duration_h))
        if max_start < 0:
            raise ValueError(f"Appliance {app.name} duration exceeds total time slots.")
        valid_starts.append(range(max_start + 1))
        
    # Calculate search space size
    search_space_size = math.prod([len(vs) for vs in valid_starts])
    logger.info(f"Brute-force search space: {search_space_size} combinations.")
    
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
    """
    Genetic Algorithm implementation for optimizing appliance schedules.
    Built on top of PyGAD for high-performance heuristic search.
    """
    
    def __init__(
        self, 
        appliances: List[Appliance], 
        pv_series: np.ndarray, 
        base_load: np.ndarray, 
        config_dict: Dict[str, Any]
    ) -> None:
        self.appliances = appliances
        self.pv_series = pv_series
        self.base_load = base_load
        self.config = config_dict
        
        # Calculate valid gene space (start times) for each appliance dynamically
        self.gene_space = []
        num_slots = len(base_load)
        for app in appliances:
            max_start = num_slots - int(np.ceil(app.duration_h))
            if max_start < 0:
                raise ValueError(f"Appliance {app.name} duration exceeds total time slots.")
            self.gene_space.append(list(range(max_start + 1)))

    def fitness_func(self, ga_instance: pygad.GA, solution: List[int], solution_idx: int) -> float:
        """
        Fitness function for the Genetic Algorithm.
        PyGAD maximizes fitness, so we return the negative of the grid import.
        """
        # Convert NumPy types to standard Python ints for the evaluation function
        int_solution = [int(val) for val in solution]
        grid_imp = evaluate_schedule(int_solution, self.appliances, self.pv_series, self.base_load)
        
        if grid_imp == float('inf'):
            return -999999.0  # Heavy penalty for invalid/out-of-bounds schedules
        return -grid_imp 

    def run(self) -> Tuple[List[int], float]:
        """
        Executes the Genetic Algorithm based on the provided configuration.
        
        Returns:
            Tuple[List[int], float]: Best start times and the resulting grid import.
        """
        logger.info("Starting Genetic Algorithm optimization...")
        ga_params = self.config.get("ga", {})
        
        num_genes = len(self.appliances)
        mutation_percent = ga_params.get("mutation_percent", 10)
        
        # Calculate strict number of mutations to prevent the 0-mutation stall issue
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