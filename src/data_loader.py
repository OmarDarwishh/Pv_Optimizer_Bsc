"""Universal ETL module for loading, cleaning, and discovering time-series energy data."""
import pandas as pd
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

def load_and_clean_data(
    file_path: str, 
    timestamp_col: str, 
    pv_col: str, 
    load_col: str, 
    freq: str = 'h',
    power_unit: str = 'kW'
) -> pd.DataFrame:
    """Universally loads and sanitizes household energy CSVs."""
    logger.info(f"Initiating Universal Data Mapper for: {file_path}")
    
    try:
        df = pd.read_csv(file_path, low_memory=False)
    except Exception as e:
        logger.error(f"Failed to read file {file_path}: {e}")
        raise

    required_cols = [timestamp_col, pv_col, load_col]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise KeyError(f"Missing required columns in CSV: {missing_cols}")

    sample_val = df[timestamp_col].dropna().iloc[0]
    try:
        if isinstance(sample_val, (int, float)) or (isinstance(sample_val, str) and sample_val.replace('.', '', 1).isdigit()):
            numeric_time = pd.to_numeric(df[timestamp_col], errors='coerce')
            df['timestamp'] = pd.to_datetime(numeric_time, unit='s')
        else:
            df['timestamp'] = pd.to_datetime(df[timestamp_col], errors='coerce')
    except Exception as e:
        raise ValueError(f"Unrecognized timestamp format in column '{timestamp_col}'.")

    df = df.dropna(subset=['timestamp'])
    df.set_index('timestamp', inplace=True)
    df.sort_index(inplace=True)
    df = df[~df.index.duplicated(keep='first')]

    df['pv_kw'] = pd.to_numeric(df[pv_col], errors='coerce')
    df['load_kw'] = pd.to_numeric(df[load_col], errors='coerce')
    clean_df = df[['pv_kw', 'load_kw']].copy()

    if power_unit.upper() == 'W':
        clean_df['pv_kw'] = clean_df['pv_kw'] / 1000.0
        clean_df['load_kw'] = clean_df['load_kw'] / 1000.0

    hourly_df = clean_df.resample(freq).mean()
    hourly_df = hourly_df.interpolate(method='linear', limit=2).fillna(0)
    hourly_df['pv_kw'] = hourly_df['pv_kw'].clip(lower=0.0)
    hourly_df['load_kw'] = hourly_df['load_kw'].clip(lower=0.0)

    return hourly_df

def validate_data(df: pd.DataFrame) -> None:
    """Hard validation to ensure the dataset is mathematically ready."""
    if df.empty:
        raise ValueError("Dataset is completely empty after cleaning.")
    if df.isna().any().any():
        raise ValueError("Critical failure: NaNs survived the cleaning pipeline.")

def _detect_sample_period_h(df: pd.DataFrame, timestamp_candidates=("timestamp", "time", "datetime")) -> float:
    """Infer sample period (hours) from the timestamp column.

    Falls back to 1.0 h if the column is missing or unparseable. Without
    this, the previous implementation assumed 1-minute data and divided
    by 60 to convert active samples -> hours, which silently mis-scaled
    durations on half-hourly Ausgrid CSVs (came out 30x too large) and
    on hourly CSVs (came out 60x too large).
    """
    for col in df.columns:
        if col.lower() in timestamp_candidates:
            try:
                ts = pd.to_datetime(df[col], errors="coerce").dropna()
                if len(ts) >= 2:
                    deltas = ts.diff().dropna()
                    median_delta = deltas.median()
                    return max(median_delta.total_seconds() / 3600.0, 1 / 3600.0)
            except Exception:
                continue
    logger.warning("Sample period could not be inferred; defaulting to 1.0 h.")
    return 1.0


def _bridge_interior_gaps(active: pd.Series, max_gap_steps: int) -> pd.Series:
    """Fill False runs of length <= max_gap_steps that are bounded by True on both sides.

    Unlike a one-sided rolling max (which extends the trailing edge of every
    cycle by ~max_gap_steps samples and inflates measured durations), this
    only bridges INTERIOR dips and never lengthens a cycle's tail.
    """
    if max_gap_steps <= 0 or active.empty:
        return active

    a = active.to_numpy().copy()
    n = len(a)
    i = 0
    while i < n:
        if not a[i]:
            j = i
            while j < n and not a[j]:
                j += 1
            gap_len = j - i
            has_left = i > 0 and a[i - 1]
            has_right = j < n and a[j] if j < n else False
            if has_left and has_right and gap_len <= max_gap_steps:
                a[i:j] = True
            i = j
        else:
            i += 1
    return pd.Series(a, index=active.index)


def _detect_appliance_runs(power_series: pd.Series,
                           sample_period_h: float,
                           min_run_h: float = 0.25,
                           gap_bridge_minutes: float = 5.0) -> pd.DataFrame:
    """Cluster contiguous active samples into individual appliance "runs".

    Returns a DataFrame with one row per detected cycle:
        - mean_power_kw : average power during the cycle
        - duration_h    : wall-clock duration of the cycle

    Threshold is adaptive: 30% of the MEDIAN of the non-zero signal. This
    handles sparse appliance traces (most samples are 0; only a few pulses
    above zero) where a global percentile would resolve to zero. Floors at
    50 W to ignore standby/phantom noise.

    `gap_bridge_minutes` bridges INTERIOR sub-threshold dips of up to that
    duration -- specified in minutes (not steps), so the bridge adapts to
    sample resolution: at 1-min data this bridges 5 short samples, at
    30-min data it bridges nothing (correctly: a 30-min zero IS a real gap).
    """
    if power_series.empty:
        return pd.DataFrame(columns=["mean_power_kw", "duration_h"])

    nonzero = power_series[power_series > 0.01]
    if nonzero.empty:
        return pd.DataFrame(columns=["mean_power_kw", "duration_h"])

    typical_active_kw = float(nonzero.quantile(0.50))
    threshold = max(0.05, typical_active_kw * 0.30)
    active = power_series > threshold

    gap_tolerance_steps = int(gap_bridge_minutes / max(sample_period_h * 60.0, 1e-6))
    active = _bridge_interior_gaps(active, gap_tolerance_steps)

    if not active.any():
        return pd.DataFrame(columns=["mean_power_kw", "duration_h"])

    # Run id increments on every active->inactive transition.
    run_id = (active != active.shift(fill_value=False)).cumsum()
    runs = (
        power_series[active]
        .groupby(run_id[active])
        .agg(mean_power_kw="mean", n_samples="size")
    )
    runs["duration_h"] = runs["n_samples"] * sample_period_h
    runs = runs[runs["duration_h"] >= min_run_h]
    return runs[["mean_power_kw", "duration_h"]]


def auto_discover_appliances(
    file_path: str,
    appliances_config: List[Dict],
    power_unit: str = 'kW',
    min_run_h: float = 0.25,
) -> List[Dict]:
    """Discover real-world appliance power and cycle duration from sensor CSV.

    For each configured appliance with a matching sensor column:
      1. Detect the sample period from the timestamp column.
      2. Apply an adaptive (95th-percentile-derived) power threshold.
      3. Cluster contiguous active samples into individual cycles.
      4. Use the MEDIAN cycle's power and duration -- robust to a single
         abnormally long run (e.g. user left appliance on overnight) and
         to one-off short noise spikes.

    Compared to the previous version this drops three magic numbers
    (`threshold_kw=0.5`, `/60.0` sample-rate assumption, `max_allowed_h=3.0`
    duration cap) and replaces each with a data-driven equivalent.
    Falls back to the YAML defaults if no usable sensor data exists.
    """
    logger.info("Scanning dataset for auto-discovery of appliance hardware parameters...")

    try:
        df = pd.read_csv(file_path, low_memory=False)
    except Exception:
        logger.warning("Auto-discovery failed to open CSV. Using YAML defaults.")
        return appliances_config

    sample_period_h = _detect_sample_period_h(df)
    logger.info(f"  Detected sample period: {sample_period_h * 60:.1f} min")

    updated_appliances = []

    def _normalize(s: str) -> str:
        # Normalize spaces / underscores / case so "Washing Machine" matches
        # any of: washing_machine, washingmachine, Washing Machine_kW, etc.
        return "".join(ch for ch in s.lower() if ch.isalnum())

    for app in appliances_config:
        app_name = app.get("name")
        norm_app = _normalize(app_name)
        matching_cols = [col for col in df.columns if norm_app in _normalize(col)]

        if not matching_cols:
            logger.info(f"  - {app_name}: No sensor data found. Using YAML defaults "
                        f"({app['power_kw']}kW, {app['duration_h']}h).")
            updated_appliances.append(app)
            continue

        target_col = matching_cols[0]
        app_data = pd.to_numeric(df[target_col], errors='coerce').dropna()

        if power_unit.upper() == 'W':
            app_data = app_data / 1000.0

        runs = _detect_appliance_runs(app_data, sample_period_h, min_run_h=min_run_h)

        if runs.empty:
            logger.info(f"  - {app_name}: No clear cycles detected. Using YAML defaults.")
            updated_appliances.append(app)
            continue

        avg_power = round(float(runs["mean_power_kw"].median()), 2)
        cycle_duration_h = round(float(runs["duration_h"].median()), 2)
        cycle_duration_h = max(min_run_h, cycle_duration_h)

        logger.info(
            f"  - {app_name} [AUTO-DETECTED]: {len(runs)} cycle(s) -> "
            f"power={avg_power} kW, duration={cycle_duration_h} h "
            f"(YAML had {app['power_kw']} kW / {app['duration_h']} h)"
        )

        app["power_kw"] = avg_power
        app["duration_h"] = cycle_duration_h
        updated_appliances.append(app)

    return updated_appliances