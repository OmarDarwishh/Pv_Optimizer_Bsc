"""
Forward-looking PV generation forecast: pvlib clear-sky x Open-Meteo cloud forecast.

This module produces tomorrow's hour-by-hour PV generation profile by
combining a locally computed clear-sky baseline with a live cloud /
temperature / wind forecast. It does NOT query PVGIS (the previous
PVGIS-based pipeline had double-cloud-attenuation and DST bugs and
was replaced).

Pipeline:
  1. Compute clear-sky GHI/DNI/DHI locally with pvlib (Ineichen).
  2. Fetch tomorrow's cloud cover (low/mid/high), air temperature, and
     10 m wind speed for the configured lat/lon from Open-Meteo.
  3. Apply a layered Beer's-law cloud attenuation -- different cloud
     layers attenuate differently, so a single total-cloud-cover term
     systematically biases partly-cloudy days.
  4. Re-decompose attenuated GHI into DNI + DHI via Erbs.
  5. Run the same physics chain as the NASA endpoint:
     Perez transposition, wind-corrected PVsyst cell temperature,
     PVWatts DC with DC-side losses, PVWatts inverter with DC/AC clipping.

All hardware constants come from config.yaml -- see _load_pv_config()
in src/pv_physics_engine.py for the canonical loader; we re-implement
a small one here to avoid an import cycle.
"""
import os
import sys
import yaml
import requests
import numpy as np
import pandas as pd
import pvlib
from datetime import datetime, timedelta


def _load_pv_config(cfg: dict) -> dict:
    pv = cfg.get("pv_system", {}) or {}
    return {
        "loss_percent": float(pv.get("loss_percent", 14.0)),
        "gamma_pdc": float(pv.get("gamma_pdc", -0.0040)),
        "dc_ac_ratio": float(pv.get("dc_ac_ratio", 1.20)),
        "module_height_m": float(pv.get("module_height_m", 3.0)),
    }


def _wind_at_module_height(ws_10m: np.ndarray, h_module: float) -> np.ndarray:
    """ws(h) = ws(10) * (h/10)^0.143 -- neutral-atmosphere power law."""
    return np.asarray(ws_10m, dtype=float) * (max(h_module, 0.1) / 10.0) ** 0.143


def _multiband_cloud_attenuation(cc_low_pct: np.ndarray,
                                 cc_mid_pct: np.ndarray,
                                 cc_high_pct: np.ndarray) -> np.ndarray:
    """Layered Beer's-law GHI transmittance from low/mid/high cloud cover.

    Single-band Kasten-Czeplak (1980) treats every cloud equally, but cirrus
    transmits ~85% of GHI while stratus transmits ~30%. Open-Meteo exposes
    the three layers separately; we apply the Kasten-Czeplak functional
    form per layer with layer-specific maximum-attenuation coefficients
    (k_layer) and combine them multiplicatively (independent random media):

        T_layer = 1 - k_layer * (cc_layer/100)^3.4
        T_total = T_low * T_mid * T_high

    Coefficients come from radiative-transfer surveys of cloud
    transmittance (Davies & McKay 1989; Kasten-Czeplak 1980 base):
      k_low  = 0.75   (stratus / stratocumulus -- heaviest attenuation)
      k_mid  = 0.50   (altostratus / altocumulus)
      k_high = 0.20   (cirrus / cirrostratus -- light attenuation)
    """
    cc_low = np.clip(np.asarray(cc_low_pct,  dtype=float) / 100.0, 0.0, 1.0)
    cc_mid = np.clip(np.asarray(cc_mid_pct,  dtype=float) / 100.0, 0.0, 1.0)
    cc_hi  = np.clip(np.asarray(cc_high_pct, dtype=float) / 100.0, 0.0, 1.0)

    t_low  = 1.0 - 0.75 * np.power(cc_low, 3.4)
    t_mid  = 1.0 - 0.50 * np.power(cc_mid, 3.4)
    t_high = 1.0 - 0.20 * np.power(cc_hi,  3.4)

    return t_low * t_mid * t_high


def fetch_and_fuse_dynamic_data():
    print("[*] Initializing forecast pipeline...")

    with open("config.yaml", "r") as file:
        config = yaml.safe_load(file)
    pv = config.get("pv_system", {})

    lat = pv.get("latitude", 30.0444)
    lon = pv.get("longitude", 31.2357)
    capacity_kw = pv.get("capacity_kw", 5.0)
    tilt = pv.get("tilt", 30)
    azimuth = pv.get("azimuth", 0)

    pv_cfg = _load_pv_config(config)

    output_path = config.get("data", {}).get("file_path", "data/raw/dynamic_cairo_target.csv")
    ausgrid_path = "data/raw/ausgrid_target_day.csv"

    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    print(f"[*] Target date: {tomorrow}")
    print(f"[*] Geometry from UI: tilt={tilt} deg, azimuth={azimuth} deg, capacity={capacity_kw} kW")

    # ---- 1. Clear-sky baseline (pvlib Ineichen, Cairo local time) ----
    print("[*] Computing clear-sky GHI/DNI/DHI via pvlib...")
    times = pd.date_range(start=f"{tomorrow} 00:00:00", periods=24, freq="h", tz="Africa/Cairo")
    location = pvlib.location.Location(latitude=lat, longitude=lon, tz="Africa/Cairo")
    clearsky = location.get_clearsky(times)
    solar_position = location.get_solarposition(times)

    # ---- 2. Live forecast: layered clouds + temperature + wind ----
    print("[*] Fetching cloud / temperature / wind forecast from Open-Meteo...")
    try:
        weather_res = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "hourly": "cloudcover,cloudcover_low,cloudcover_mid,cloudcover_high,temperature_2m,windspeed_10m",
                "timezone": "Africa/Cairo",
                "start_date": tomorrow,
                "end_date": tomorrow,
            },
            timeout=15,
        )
        weather_res.raise_for_status()
        h = weather_res.json()["hourly"]
    except Exception as e:
        print(f"[!] Open-Meteo API failed: {e}")
        sys.exit(1)

    cc_total = np.array(h["cloudcover"], dtype=float)
    cc_low = np.array(h.get("cloudcover_low",  cc_total), dtype=float)
    cc_mid = np.array(h.get("cloudcover_mid",  np.zeros_like(cc_total)), dtype=float)
    cc_high = np.array(h.get("cloudcover_high", np.zeros_like(cc_total)), dtype=float)
    temp_air = np.array(h["temperature_2m"], dtype=float)
    wind_10m = np.array(h["windspeed_10m"], dtype=float) / 3.6  # km/h -> m/s

    # ---- 3. Multi-band cloud attenuation ----
    print("[*] Applying layered Beer's-law cloud attenuation (low/mid/high)...")
    attenuation = _multiband_cloud_attenuation(cc_low, cc_mid, cc_high)
    ghi = clearsky["ghi"].values * attenuation

    # Erbs decomposition: redistributes attenuated GHI into direct + diffuse.
    erbs = pvlib.irradiance.erbs(ghi, solar_position["zenith"].values, times)
    dni = np.clip(erbs["dni"].fillna(0).values, 0.0, None)
    dhi = np.clip(erbs["dhi"].fillna(0).values, 0.0, None)

    # ---- 4. Plane-of-array transposition (Perez) ----
    print("[*] Running Perez transposition + thermal model...")
    dni_extra = pvlib.irradiance.get_extra_radiation(times)
    airmass = pvlib.atmosphere.get_relative_airmass(solar_position["apparent_zenith"])
    poa = pvlib.irradiance.get_total_irradiance(
        surface_tilt=tilt,
        surface_azimuth=azimuth,
        dni=dni,
        ghi=ghi,
        dhi=dhi,
        solar_zenith=solar_position["apparent_zenith"],
        solar_azimuth=solar_position["azimuth"],
        dni_extra=dni_extra,
        airmass=airmass,
        model="perez",
    )

    # ---- 5. Cell temperature with wind scaled to module height ----
    wind_module = _wind_at_module_height(wind_10m, pv_cfg["module_height_m"])
    cell_temp = pvlib.temperature.pvsyst_cell(
        poa_global=poa["poa_global"],
        temp_air=temp_air,
        wind_speed=wind_module,
    )

    # ---- 6. PVWatts DC with DC-side losses + inverter clipping ----
    pdc0_dc_watts = capacity_kw * 1000.0
    loss_factor = 1.0 - (pv_cfg["loss_percent"] / 100.0)
    effective_irradiance = poa["poa_global"] * loss_factor

    dc_power = pvlib.pvsystem.pvwatts_dc(
        effective_irradiance=effective_irradiance,
        temp_cell=cell_temp,
        pdc0=pdc0_dc_watts,
        gamma_pdc=pv_cfg["gamma_pdc"],
    )

    inv_pdc0_watts = pdc0_dc_watts / pv_cfg["dc_ac_ratio"]
    ac_power = pvlib.inverter.pvwatts(pdc=dc_power, pdc0=inv_pdc0_watts)
    pv_kw = (ac_power / 1000.0).clip(lower=0).fillna(0)

    # ---- 7. Merge with base load and save ----
    if not os.path.exists(ausgrid_path):
        print(f"[!] Missing base load file: {ausgrid_path}")
        sys.exit(1)
    df_load = pd.read_csv(ausgrid_path)
    timestamps = pd.date_range(start=f"{tomorrow} 00:00:00", periods=24, freq="h")
    final_df = pd.DataFrame({
        "timestamp": timestamps,
        "pv_kw": pv_kw.values,
        "load_kw": df_load["load_kw"].values,
    })
    final_df.to_csv(output_path, index=False)

    print("\n" + "=" * 60)
    print(f"[OK] Forecast saved: {output_path}")
    print(f"     Clear-sky peak GHI:   {clearsky['ghi'].max():.0f} W/m^2")
    print(f"     Forecast peak power:  {pv_kw.max():.2f} kW")
    print(f"     Mean cloud (lo/md/hi): {cc_low.mean():.0f}/{cc_mid.mean():.0f}/{cc_high.mean():.0f}%")
    print(f"     DC losses applied:    {pv_cfg['loss_percent']:.1f}%")
    print(f"     DC/AC ratio:          {pv_cfg['dc_ac_ratio']:.2f}")
    print(f"     gamma_pdc:            {pv_cfg['gamma_pdc']:.4f}/degC")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    fetch_and_fuse_dynamic_data()
