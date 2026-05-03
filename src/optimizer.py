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


class InfeasibleScheduleError(ValueError):
    """Raised when one or more appliances cannot fit inside their allowed time window.

    Carries a list of structured error dicts (one per offending appliance) on
    the `.errors` attribute so the API layer can return them to the user.
    """

    def __init__(self, errors: List[Dict[str, Any]]):
        self.errors = errors
        names = ", ".join(e["appliance"] for e in errors)
        super().__init__(f"Infeasible schedule for: {names}")


def validate_appliance_constraints(appliances: List[Appliance],
                                   num_slots: int = 24) -> List[Dict[str, Any]]:
    """Check every appliance's (window_start, window_end, duration_h) triple.

    Returns a list of structured error dicts -- empty list means all feasible.
    Collecting all errors at once (instead of failing on the first) lets the
    UI show every problem in a single response so the user can fix them in
    one round-trip.

    `num_slots` is the simulation horizon (typically 24 for a daily run).
    The effective window is clamped to `[window_start, min(window_end, num_slots)]`
    -- so a 0-24 window on a 24-hour day is unrestricted, while a 0-24 window
    on a hypothetical 12-hour test run is silently treated as 0-12.

    A schedule is feasible iff the clamped window is at least as wide as the
    cycle duration (in slots).
    """
    errors: List[Dict[str, Any]] = []
    for app in appliances:
        duration_slots = int(np.ceil(app.duration_h))
        effective_end = min(app.window_end, num_slots)
        window_width = effective_end - app.window_start

        if duration_slots > window_width:
            errors.append({
                "appliance": app.name,
                "window_start": app.window_start,
                "window_end": app.window_end,
                "duration_h": app.duration_h,
                "available_h": max(0, window_width),
                "message": (
                    f"{app.name} needs {app.duration_h:g} hour(s) to run, but the "
                    f"selected window {app.window_start:02d}:00-{app.window_end:02d}:00 "
                    f"only allows {max(0, window_width)} hour(s). "
                    f"Widen the window or shorten the cycle."
                ),
            })

    return errors


def get_valid_start_times(appliances: List[Appliance], num_slots: int) -> List[List[int]]:
    """Build the per-appliance list of allowed start hours.

    `window_end` is interpreted as "the appliance must FINISH by this hour":
    a cycle of `ceil(duration_h)` slots starting at hour `s` occupies
    [s, s+duration_slots) and must satisfy `s + duration_slots <= window_end`.

    Hard-fails with `InfeasibleScheduleError` if any appliance's window is
    too narrow for its duration. Callers should normally run
    `validate_appliance_constraints` first to catch this with all errors
    collected, but we keep this internal check as a defense-in-depth so
    the GA's gene_space can never be malformed.
    """
    errors = validate_appliance_constraints(appliances, num_slots)
    if errors:
        raise InfeasibleScheduleError(errors)

    valid_starts: List[List[int]] = []
    for app in appliances:
        duration_slots = int(np.ceil(app.duration_h))
        max_start = min(app.window_end, num_slots) - duration_slots
        valid_starts.append(list(range(app.window_start, max_start + 1)))
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