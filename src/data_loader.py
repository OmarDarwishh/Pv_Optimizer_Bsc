"""ETL module for loading and cleaning time-series energy data."""
import pandas as pd
import logging

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
    except Exception:
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
