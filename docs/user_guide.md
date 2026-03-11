# User Guide: PV Optimizer

## Installation Requirements

- Python 3.9 or higher.
- Standard data science stack (`pandas`, `numpy`, `matplotlib`).

## Configuration (`config.yaml`)

The engine is entirely driven by the `config.yaml` file. You do not need to modify the Python code to run different experiments.

### Key Sections:

1. **`data`**: Define your input CSV file, column names, and time frequency.
2. **`appliances`**: Add as many appliances as you want. Define their name, power consumption in kW, and duration in hours.
3. **`optimization`**: Switch between `ga` (Genetic Algorithm, recommended for >3 appliances) or `bruteforce` (guarantees mathematical optimum but scales poorly).

## Running the Tool

The package installs a global command line tool:

```bash
pv-optimizer
```

```

```
