"""Tests for the data loader module."""

import pytest
import pandas as pd
from src.data_loader import load_and_clean_data, validate_data

def test_load_valid_data(tmp_path):
    """Test loading a perfectly formatted CSV."""
    csv_file = tmp_path / "valid.csv"
    csv_file.write_text(
        "timestamp,pv,load\n"
        "2026-01-01 00:00:00,0.0,0.5\n"
        "2026-01-01 01:00:00,0.0,0.6\n"
        "2026-01-01 02:00:00,0.0,0.4\n"
    )
    
    df = load_and_clean_data(str(csv_file), "timestamp", "pv", "load", freq="h")
    
    assert len(df) == 3
    assert list(df.columns) == ["pv_kw", "load_kw"]
    assert df.index.freq == "h"

def test_missing_rows_interpolation(tmp_path):
    """Test if missing hours are properly interpolated."""
    csv_file = tmp_path / "gap.csv"
    # Notice 01:00:00 is missing
    csv_file.write_text(
        "time,pv_gen,home_load\n"
        "2026-01-01 00:00:00,0.0,1.0\n"
        "2026-01-01 02:00:00,0.0,3.0\n"
    )
    
    df = load_and_clean_data(str(csv_file), "time", "pv_gen", "home_load")
    
    assert len(df) == 3  # Should have recreated the missing 01:00 row
    # Interpolation between 1.0 and 3.0 should give exactly 2.0
    assert df.loc["2026-01-01 01:00:00", "load_kw"] == 2.0

def test_negative_clipping(tmp_path):
    """Test that negative values are clipped to zero."""
    csv_file = tmp_path / "negative.csv"
    csv_file.write_text(
        "time,pv,load\n"
        "2026-01-01 00:00:00,-1.5,-0.5\n"
    )
    
    df = load_and_clean_data(str(csv_file), "time", "pv", "load")
    assert df.iloc[0]["pv_kw"] == 0.0
    assert df.iloc[0]["load_kw"] == 0.0

def test_missing_columns(tmp_path):
    """Test that a KeyError is raised if a column is missing."""
    csv_file = tmp_path / "missing_col.csv"
    csv_file.write_text("time,pv\n2026-01-01 00:00:00,1.0\n")
    
    with pytest.raises(KeyError):
        load_and_clean_data(str(csv_file), "time", "pv", "load")

def test_empty_file(tmp_path):
    """Test that a ValueError is raised for empty files."""
    csv_file = tmp_path / "empty.csv"
    csv_file.write_text("")
    
    with pytest.raises(ValueError):
        load_and_clean_data(str(csv_file), "time", "pv", "load")

def test_validation():
    """Test the validation function."""
    df_valid = pd.DataFrame({"pv_kw": [1.0, 5.0], "load_kw": [2.0, 3.0]})
    # Should not raise any errors
    validate_data(df_valid)
    
    df_invalid = pd.DataFrame({"pv_kw": [1.0, None], "load_kw": [2.0, 3.0]})
    with pytest.raises(ValueError):
        validate_data(df_invalid)