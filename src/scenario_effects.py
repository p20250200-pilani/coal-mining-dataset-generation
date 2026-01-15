"""
Scenario and correlation helpers for coal mine simulations.
"""


from __future__ import annotations

import math
from typing import Dict, Any, Optional

import numpy as np


class ScenarioEffects:
    """Apply scenario-specific adjustments to sensor readings."""

    GAS_SENSORS = ["CH4", "CO", "CO2", "H2S", "SO2", "NH3", "NO", "NO2"]
    PM_SENSORS = ["PM2.5", "PM10"]

    def __init__(
        self,
        features: Dict[str, Dict[str, Any]],
        scenario: str,
        config: Optional[Dict[str, Any]] = None,
        *,
        rng: Optional[np.random.Generator] = None,
        tick_minutes_override: Optional[float] = None,
    ) -> None:
        """Precompute bounds/baselines and load the requested scenario profile."""
        self.features = features
        self.scenario = scenario
        self.config = config or {}
        self.rng = rng or np.random.default_rng()
        self.tick = 0

        self.feature_bounds = {
            name: (
                float(min(r["safe"][0], r["unsafe"][0])),
                float(max(r["safe"][1], r["unsafe"][1])),
            )
            for name, r in features.items()
        }
        self.baselines = {
            name: float((r["safe"][0] + r["safe"][1]) / 2.0) for name, r in features.items()
        }

        base_profile = dict(self.config.get("normal", {}))
        profile = dict(base_profile)
        profile.update(self.config.get(scenario, {}))
        self.profile = profile
        self.tick_minutes = tick_minutes_override or profile.get("tick_minutes", 1.0)

    def _clamp(self, name: str, value: float) -> float:
        """Keep a feature value within the combined safe/unsafe bounds."""
        bounds = self.feature_bounds.get(name)
        if not bounds:
            return value
        return float(np.clip(value, bounds[0], bounds[1]))

    def apply(self, row: Dict[str, Any], tick: Optional[int] = None) -> Dict[str, Any]:
        """Apply the active scenario handler to a row for the current or provided tick."""
        active_tick = self.tick if tick is None else tick
        minutes = active_tick * self.tick_minutes
        handler = getattr(self, f"_apply_{self.scenario}", self._apply_normal)
        updated = handler(dict(row), minutes, active_tick)
        if tick is None:
            self.tick += 1
        return updated

    # Scenario handlers -------------------------------------------------
    def _apply_normal(self, row: Dict[str, Any], minutes: float, _: int) -> Dict[str, Any]:
        """Apply the baseline diurnal cycle for temperature and humidity."""
        diurnal_cfg = self.profile.get("diurnal", {})
        period = max(diurnal_cfg.get("period_minutes", 1440), 1.0)
        angle = 2.0 * math.pi * ((minutes % period) / period)

        temp_amp = diurnal_cfg.get("temperature_amplitude", 0.0)
        if "Temperature" in row and row["Temperature"] is not None:
            row["Temperature"] = self._clamp(
                "Temperature", row["Temperature"] + temp_amp * math.sin(angle)
            )

        humidity_amp = diurnal_cfg.get("humidity_amplitude", 0.0)
        humidity_phase = math.radians(diurnal_cfg.get("humidity_phase_deg", 90))
        if "Humidity" in row and row["Humidity"] is not None:
            row["Humidity"] = self._clamp(
                "Humidity",
                row["Humidity"] + humidity_amp * math.sin(angle + humidity_phase),
            )

        return row

    def _apply_ventilation_failure(
        self, row: Dict[str, Any], minutes: float, tick: int
    ) -> Dict[str, Any]:
        """Simulate ventilation loss by gradually increasing gases and heat."""
        row = self._apply_normal(row, minutes, tick)
        hours = minutes / 60.0
        rise_pct = self.profile.get("gas_rise_pct_per_hour", 0.05)
        for gas in self.GAS_SENSORS:
            if gas not in row or row[gas] is None:
                continue
            baseline = self.baselines.get(gas, row[gas])
            row[gas] = self._clamp(gas, row[gas] + baseline * rise_pct * hours)

        temp_rise = self.profile.get("temperature_rise_per_hour", 0.1)
        if "Temperature" in row and row["Temperature"] is not None:
            row["Temperature"] = self._clamp(
                "Temperature", row["Temperature"] + temp_rise * hours
            )

        humidity_rise = self.profile.get("humidity_rise_per_hour", 0.0)
        if "Humidity" in row and row["Humidity"] is not None:
            row["Humidity"] = self._clamp(
                "Humidity", row["Humidity"] + humidity_rise * hours
            )

        return row

    def _apply_methane_leak(self, row: Dict[str, Any], minutes: float, tick: int) -> Dict[str, Any]:
        """Model a methane spike along with secondary gas and particulate gains."""
        row = self._apply_normal(row, minutes, tick)
        rise_minutes = max(self.profile.get("ch4_rise_minutes", 15), 1)
        intensity = 1.0 - math.exp(-minutes / rise_minutes)
        spike_value = self.profile.get("ch4_spike_value", 3.0) * intensity

        if "CH4" in row and row["CH4"] is not None:
            row["CH4"] = self._clamp("CH4", row["CH4"] + spike_value)

        secondary_gain = self.profile.get("secondary_gas_gain", 0.05)
        for name in ["CO2", "CO"]:
            if name not in row or row[name] is None:
                continue
            baseline = self.baselines.get(name, row[name])
            row[name] = self._clamp(name, row[name] + baseline * secondary_gain * intensity)

        pm_gain = self.profile.get("pm_gain", 0.2)
        for pm in self.PM_SENSORS:
            if pm not in row or row[pm] is None:
                continue
            baseline = self.baselines.get(pm, row[pm])
            row[pm] = self._clamp(pm, row[pm] + baseline * pm_gain * intensity)

        return row

    def _apply_combustion(self, row: Dict[str, Any], minutes: float, tick: int) -> Dict[str, Any]:
        """Introduce combustion dynamics such as CO/CO2 spikes and heat/humidity shifts."""
        row = self._apply_normal(row, minutes, tick)
        rise_minutes = max(self.profile.get("co_rise_minutes", 10), 1)
        intensity = 1.0 - math.exp(-minutes / rise_minutes)

        co_spike = self.profile.get("co_spike_value", 120.0) * intensity
        if "CO" in row and row["CO"] is not None:
            row["CO"] = self._clamp("CO", row["CO"] + co_spike)

        co2_spike = self.profile.get("co2_spike_value", 1500.0) * (1.0 - math.exp(-minutes / (rise_minutes * 1.5)))
        if "CO2" in row and row["CO2"] is not None:
            row["CO2"] = self._clamp("CO2", row["CO2"] + co2_spike)

        pm_gain = self.profile.get("pm_gain_per_co", 0.4)
        co_value = row.get("CO")
        if co_value is not None and pm_gain != 0:
            baseline_co = self.baselines.get("CO", co_value)
            co_delta = max(0.0, co_value - baseline_co)
            for pm in self.PM_SENSORS:
                if pm not in row or row[pm] is None:
                    continue
                row[pm] = self._clamp(pm, row[pm] + pm_gain * co_delta)

        temp_rise = self.profile.get("temperature_rise_per_hour", 0.3)
        if "Temperature" in row and row["Temperature"] is not None:
            row["Temperature"] = self._clamp(
                "Temperature", row["Temperature"] + temp_rise * (minutes / 60.0)
            )

        humidity_drop = self.profile.get("humidity_drop_per_hour", 0.5)
        if "Humidity" in row and row["Humidity"] is not None:
            row["Humidity"] = self._clamp(
                "Humidity", row["Humidity"] - humidity_drop * (minutes / 60.0)
            )

        nox_gain = self.profile.get("nox_gain", 0.3)
        for gas in ["NO", "NO2"]:
            if gas in row and row[gas] is not None:
                baseline = self.baselines.get(gas, row[gas])
                row[gas] = self._clamp(gas, row[gas] + baseline * nox_gain * intensity)

        return row

    def _apply_dust_event(self, row: Dict[str, Any], minutes: float, tick: int) -> Dict[str, Any]:
        """Create periodic dust events that elevate particulates and related gases."""
        row = self._apply_normal(row, minutes, tick)
        duration = max(self.profile.get("pm_event_duration_minutes", 10), 1.0)
        period = max(self.profile.get("pm_event_period_minutes", 90), duration + 1.0)
        phase = minutes % period
        if phase <= duration:
            window = 1.0 - (phase / duration)
            pm_peak = self.profile.get("pm_peak", 400.0)
            for pm in self.PM_SENSORS:
                if pm in row and row[pm] is not None:
                    row[pm] = self._clamp(pm, row[pm] + pm_peak * window)

            co_spike = self.profile.get("co_spike", 25.0)
            if "CO" in row and row["CO"] is not None:
                row["CO"] = self._clamp("CO", row["CO"] + co_spike * window)

            nox_spike = self.profile.get("nox_spike", 10.0)
            for gas in ["NO", "NO2"]:
                if gas in row and row[gas] is not None:
                    row[gas] = self._clamp(gas, row[gas] + nox_spike * window)

            humidity_drop = self.profile.get("humidity_drop_during_event", 5.0)
            if "Humidity" in row and row["Humidity"] is not None:
                row["Humidity"] = self._clamp("Humidity", row["Humidity"] - humidity_drop * window)

            temp_bump = self.profile.get("temperature_bump_during_event", 1.0)
            if "Temperature" in row and row["Temperature"] is not None:
                row["Temperature"] = self._clamp(
                    "Temperature", row["Temperature"] + temp_bump * window
                )

        return row


class CorrelationAdjuster:
    """Apply correlation rules to sensor readings."""

    def __init__(self, features: Dict[str, Dict[str, Any]], config: Optional[Dict[str, Any]] = None) -> None:
        """Store feature bounds/baselines and normalize the correlation config."""
        self.features = features
        self.config = config or {}
        self.feature_bounds = {
            name: (
                float(min(r["safe"][0], r["unsafe"][0])),
                float(max(r["safe"][1], r["unsafe"][1])),
            )
            for name, r in features.items()
        }
        self.baselines = {
            name: float((r["safe"][0] + r["safe"][1]) / 2.0) for name, r in features.items()
        }

    def _clamp(self, name: str, value: float) -> float:
        """Clamp correlation-adjusted values to the sensor's allowable range."""
        bounds = self.feature_bounds.get(name)
        if not bounds:
            return value
        return float(np.clip(value, bounds[0], bounds[1]))

    def apply(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Apply pairwise, humidity, and temperature rules to a reading row."""
        updated = dict(row)
        for rule in self.config.get("pairwise", []):
            source = rule.get("source")
            target = rule.get("target")
            if source not in updated or target not in updated:
                continue
            s_val = updated[source]
            t_val = updated[target]
            if s_val is None or t_val is None:
                continue

            mode = rule.get("mode", "linear")
            if mode == "ratio":
                ratio = rule.get("ratio", 0.5)
                blend = np.clip(rule.get("blend", 0.5), 0.0, 1.0)
                desired = s_val * ratio
                updated[target] = self._clamp(
                    target, blend * t_val + (1.0 - blend) * desired
                )
            else:
                coeff = rule.get("coeff", 0.0)
                baseline = self.baselines.get(source, s_val)
                # Normalize source delta to [0, 1] by dividing by source's full range
                s_bounds = self.feature_bounds.get(source, (baseline, baseline + 1e-9))
                s_range = s_bounds[1] - s_bounds[0]
                if abs(s_range) < 1e-9:
                    s_norm_delta = 0.0
                else:
                    s_norm_delta = (s_val - baseline) / s_range
                # Scale by target's range so effect magnitude is appropriate
                t_bounds = self.feature_bounds.get(target, (t_val, t_val + 1e-9))
                t_range = t_bounds[1] - t_bounds[0]
                delta = s_norm_delta * coeff * t_range
                updated[target] = self._clamp(target, t_val + delta)
        updated = self._apply_humidity_effect(updated)
        updated = self._apply_temperature_effect(updated)
        return updated

    def _apply_humidity_effect(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Increase configured targets when humidity passes a threshold."""
        cfg = self.config.get("humidity_effect")
        if not cfg or "Humidity" not in row or row["Humidity"] is None:
            return row
        threshold = cfg.get("threshold", 70.0)
        humidity = row["Humidity"]
        if humidity <= threshold:
            return row
        delta = humidity - threshold
        strength = cfg.get("strength", 0.1)
        for target in cfg.get("targets", []):
            if target in row and row[target] is not None:
                row[target] = self._clamp(target, row[target] + delta * strength)
        return row

    def _apply_temperature_effect(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Alter configured targets based on deviations from temperature baseline."""
        cfg = self.config.get("temperature_effect")
        if not cfg or "Temperature" not in row or row["Temperature"] is None:
            return row
        baseline = cfg.get("baseline", self.baselines.get("Temperature", row["Temperature"]))
        delta = row["Temperature"] - baseline
        strength = cfg.get("strength", -0.05)
        for target in cfg.get("targets", []):
            if target in row and row[target] is not None:
                row[target] = self._clamp(target, row[target] + delta * strength)
        return row

