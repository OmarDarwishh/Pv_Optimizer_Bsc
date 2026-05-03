# src/pv_physics_engine.py
"""
NASA POWER -> pvlib historical PV simulator.

Physics chain (each step matches the conventions used by PVGIS / NREL PVWatts):
  1. Fetch NASA POWER hourly GHI / DHI / T2M / WS10M for the requested date.
  2. Clean -999 fill values, interpolate to 15-minute resolution.
  3. Compute solar position; estimate DNI from GHI (DIRINT).
  4. Transpose to plane-of-array irradiance (Perez model).
  5. Apply DC-side system losses (soiling, mismatch, wiring, IAM, spectral,
     LID, nameplate, availability) BEFORE the DC model -- canonical PVWatts.
  6. Scale 10 m wind to module-level wind via power-law (alpha=0.143) so
     the PVsyst thermal model receives the wind speed it was calibrated on.
  7. PVsyst cell temperature -> PVWatts DC -> PVWatts inverter with
     DC/AC oversizing so that the inverter clips at AC nameplate.

All technology constants (gamma_pdc, loss_percent, dc_ac_ratio,
module_height_m) are read from config.yaml so the model can be re-tuned
for different hardware without code edits.
"""
import os
import requests
import pandas as pd
import numpy as np
import pvlib
import yaml


# Columns that should be clipped to >= 0 (irradiance only).
# T2M can legitimately be negative; clipping it to 0 was a bug that
# inflated cell-temperature derate on cold nights / high-latitude runs.
_IRRADIANCE_COLS = ("ghi", "dhi", "dni")


def _load_pv_config() -> dict:
    """Load `pv_system` block from config.yaml with sane fallbacks."""
    try:
        with open("config.yaml", "r") as f:
            cfg = yaml.safe_load(f) or {}
    except FileNotFoundError:
        cfg = {}
    pv = cfg.get("pv_system", {}) or {}
    return {
        "loss_percent": float(pv.get("loss_percent", 14.0)),
        "gamma_pdc": float(pv.get("gamma_pdc", -0.0040)),
        "dc_ac_ratio": float(pv.get("dc_ac_ratio", 1.20)),
        "module_height_m": float(pv.get("module_height_m", 3.0)),
    }


def _wind_at_module_height(ws_10m: pd.Series | np.ndarray, h_module: float) -> np.ndarray:
    """Scale wind speed from 10 m down to module height via neutral power-law.

    ws(h) = ws(10) * (h / 10) ** alpha,  alpha = 1/7 = 0.143

    NASA POWER's WS10M and Open-Meteo's windspeed_10m are both at 10 m.
    The PVsyst thermal model was calibrated against module-level wind
    (typically 1-3 m for residential rooftop). Feeding 10 m wind directly
    under-predicts cell temperature by ~2-4 degC and over-predicts energy
    yield by 1-3% on hot, breezy days.
    """
    return np.asarray(ws_10m, dtype=float) * (max(h_module, 0.1) / 10.0) ** 0.143


def fetch_and_simulate_nasa_power(lat: float, lon: float, capacity_kw: float, tilt: int, azimuth: int, start_date: str, end_date: str):
    print(f"[*] Requesting live historical data from NASA POWER API for {start_date} to {end_date}...")

    pv_cfg = _load_pv_config()

    # 1. NASA POWER API Configuration
    url = "https://power.larc.nasa.gov/api/temporal/hourly/point"
    params = {
        "parameters": "ALLSKY_SFC_SW_DWN,ALLSKY_SFC_SW_DIFF,T2M,WS10M",
        "community": "RE",
        "longitude": lon,
        "latitude": lat,
        "start": start_date,
        "end": end_date,
        "format": "JSON",
    }

    response = requests.get(url, params=params, timeout=30)
    if response.status_code != 200:
        raise ValueError(
            f"NASA POWER rejected the request ({response.status_code}). "
            f"The hourly archive trails real-time by ~3-5 days, so recent or future dates are unavailable."
        )

    data = response.json()["properties"]["parameter"]
    df = pd.DataFrame(data)

    # Guard: -999 is NASA's "missing value" sentinel. If every irradiance
    # sample is -999 the date is in the future / too recent for the archive.
    if "ALLSKY_SFC_SW_DWN" in df.columns and (df["ALLSKY_SFC_SW_DWN"] == -999).all():
        raise ValueError(
            f"NASA POWER has no data for {start_date}. "
            f"The hourly archive trails real-time by ~3-5 days -- please pick an earlier date."
        )

    df.index = pd.to_datetime(df.index, format="%Y%m%d%H")
    df.index = df.index.tz_localize("UTC").tz_convert("Africa/Cairo")

    df = df.rename(columns={
        "ALLSKY_SFC_SW_DWN": "ghi",
        "ALLSKY_SFC_SW_DIFF": "dhi",
        "T2M": "temp_air",
        "WS10M": "wind_speed_10m",
    })

    # 2. Sub-hourly interpolation (15-min). Drop -999 fills first so
    # they don't smear into valid samples.
    print("[*] Interpolating NASA data to 15-minute resolution...")
    df = df.replace(-999, np.nan)
    df_15min = df.resample("15min").interpolate(method="linear")
    df_15min = df_15min.ffill().bfill()

    # Clip irradiance only (NOT temperature). The previous
    # `df_15min[df_15min < 0] = 0` zeroed out negative T2M values -- a bug.
    for col in _IRRADIANCE_COLS:
        if col in df_15min.columns:
            df_15min[col] = df_15min[col].clip(lower=0.0)

    # 3. Solar geometry + DNI estimation
    print("[*] Executing pvlib thermal & astronomical simulation...")
    location = pvlib.location.Location(latitude=lat, longitude=lon, tz="Africa/Cairo")
    solar_position = location.get_solarposition(times=df_15min.index)

    dni = pvlib.irradiance.dirint(df_15min["ghi"], solar_position["zenith"], df_15min.index)
    df_15min["dni"] = dni.fillna(0).clip(lower=0.0)

    dni_extra = pvlib.irradiance.get_extra_radiation(df_15min.index)
    airmass = pvlib.atmosphere.get_relative_airmass(solar_position["apparent_zenith"])

    # 4. Plane of array (POA) via Perez transposition -- matches PVGIS internals.
    poa_irradiance = pvlib.irradiance.get_total_irradiance(
        surface_tilt=tilt,
        surface_azimuth=azimuth,
        dni=df_15min["dni"],
        ghi=df_15min["ghi"],
        dhi=df_15min["dhi"],
        solar_zenith=solar_position["apparent_zenith"],
        solar_azimuth=solar_position["azimuth"],
        dni_extra=dni_extra,
        airmass=airmass,
        model="perez",
    )

    # 5. Cell temperature -- correct wind level first.
    wind_module = _wind_at_module_height(df_15min["wind_speed_10m"], pv_cfg["module_height_m"])
    cell_temperature = pvlib.temperature.pvsyst_cell(
        poa_global=poa_irradiance["poa_global"],
        temp_air=df_15min["temp_air"],
        wind_speed=wind_module,
    )

    # 6. PVWatts DC + inverter chain.
    # System losses are applied as an EFFECTIVE-IRRADIANCE reduction
    # BEFORE the DC model -- this is the canonical PVWatts formulation.
    # Previously we multiplied AC by (1 - loss_pct), which is dimensionally
    # the wrong stage and biases the temperature derate.
    pdc0_dc_watts = capacity_kw * 1000.0
    loss_factor = 1.0 - (pv_cfg["loss_percent"] / 100.0)
    effective_irradiance = poa_irradiance["poa_global"] * loss_factor

    dc_power = pvlib.pvsystem.pvwatts_dc(
        effective_irradiance=effective_irradiance,
        temp_cell=cell_temperature,
        pdc0=pdc0_dc_watts,
        gamma_pdc=pv_cfg["gamma_pdc"],
    )

    # Inverter clipping: DC array nameplate exceeds AC inverter rating
    # by `dc_ac_ratio`. pvlib.inverter.pvwatts treats `pdc0` as the
    # DC input that produces AC nameplate -- so passing the AC-side
    # rating naturally clips peak hours.
    inv_pdc0_watts = pdc0_dc_watts / pv_cfg["dc_ac_ratio"]
    ac_power = pvlib.inverter.pvwatts(pdc=dc_power, pdc0=inv_pdc0_watts)

    df_15min["ac_power_kw"] = (ac_power / 1000.0).clip(lower=0)

    print(
        f"[OK] NASA simulation complete (Perez, "
        f"{pv_cfg['loss_percent']:.1f}% DC losses, "
        f"DC/AC={pv_cfg['dc_ac_ratio']:.2f}, "
        f"gamma_pdc={pv_cfg['gamma_pdc']:.4f}/degC)."
    )
    return df_15min


if __name__ == "__main__":
    result = fetch_and_simulate_nasa_power(30.0444, 31.2357, 5.0, 30, 180, "20230601", "20230602")
    print(result["ac_power_kw"].head(20))
