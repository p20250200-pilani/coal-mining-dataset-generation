"""
Stateful streaming simulator for coal mine sensors.
Generates one row (or small batches) per tick while maintaining drift and
global stuck state across ticks.
"""

from __future__ import annotations

import time
import json
from typing import Dict, Any, Iterable, Optional

import numpy as np

from .scenario_effects import ScenarioEffects, CorrelationAdjuster


class StatefulSensorSimulator:
    """Stateful simulator maintaining per-feature drift and global stuck state."""

    def __init__(
        self,
        features: Dict[str, Dict[str, tuple]],
        noise_config: Dict[str, Any],
        *,
        random_state: Optional[int] = None,
        scenario: str = "normal",
        scenario_config: Optional[Dict[str, Any]] = None,
        correlation_config: Optional[Dict[str, Any]] = None,
        tick_minutes: Optional[float] = None,
    ) -> None:
        """Initialise RNG, per-feature state, and optional scenario/correlation helpers."""
        self.features = features
        self.noise_config = noise_config
        self.rng = np.random.default_rng(random_state)
        self.per_feature = {name: {"drift": 0.0, "last_value": None} for name in features}
        self.stuck_remaining = 0
        self.stuck_row: Optional[Dict[str, Any]] = None
        self.tick = 0

        self.scenario_effects: Optional[ScenarioEffects] = None
        if scenario_config is not None:
            self.scenario_effects = ScenarioEffects(
                features,
                scenario,
                scenario_config,
                rng=self.rng,
                tick_minutes_override=tick_minutes,
            )

        self.correlation_adjuster: Optional[CorrelationAdjuster] = None
        if correlation_config is not None:
            self.correlation_adjuster = CorrelationAdjuster(features, correlation_config)

    def _step_feature(self, name: str) -> float:
        """Generate one feature reading with per-feature noise and drift applied."""
        ranges = self.features[name]
        use_safe = self.rng.random() < 0.8
        base = float(self.rng.uniform(*(ranges["safe"] if use_safe else ranges["unsafe"])) )

        cfg = self.noise_config.get(name, {})

        # Bias
        bias_cfg = cfg.get("bias", {})
        if bias_cfg.get("enabled", False):
            base += float(bias_cfg.get("value", 0.0))

        # Drift as random walk
        drift_cfg = cfg.get("drift", {})
        if drift_cfg.get("enabled", False):
            current_drift = float(self.per_feature[name]["drift"])  # type: ignore[index]
            step = float(self.rng.normal(0.0, float(drift_cfg.get("rate", 0.0))))
            current_drift += step
            max_drift = drift_cfg.get("max_drift")
            if max_drift is not None:
                current_drift = float(np.clip(current_drift, -float(max_drift), float(max_drift)))
            self.per_feature[name]["drift"] = current_drift
            base += current_drift

        # Gaussian noise
        gauss_cfg = cfg.get("gaussian_noise", {})
        if gauss_cfg.get("enabled", False):
            base += float(self.rng.normal(0.0, float(gauss_cfg.get("std_dev", 1.0))))

        # Outliers
        out_cfg = cfg.get("outliers", {})
        if out_cfg.get("enabled", False):
            if self.rng.random() < float(out_cfg.get("probability", 0.0)):
                std = float(gauss_cfg.get("std_dev", 1.0))
                base += float(self.rng.normal(0.0, float(out_cfg.get("magnitude", 1.0)) * std))

        # Clip to full valid range
        min_v = float(min(ranges["safe"][0], ranges["unsafe"][0]))
        max_v = float(max(ranges["safe"][1], ranges["unsafe"][1]))
        base = float(np.clip(base, min_v, max_v))

        # Quantization
        q_cfg = cfg.get("quantization", {})
        if q_cfg.get("enabled", False):
            res = float(q_cfg.get("resolution", 1.0))
            if res > 0:
                base = float(np.round(base / res) * res)

        self.per_feature[name]["last_value"] = base
        return base

    def _apply_missing_and_invalid(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Inject missing values and string invalids according to each feature's config."""
        updated = dict(row)
        for feat, cfg in self.noise_config.items():
            if feat == "global":
                continue

            # Missingness
            miss_cfg = cfg.get("missing_data", {})
            if miss_cfg.get("enabled", False):
                mech = miss_cfg.get("mechanism", "MCAR")
                p = float(miss_cfg.get("probability", 0.0))
                is_missing = False
                if mech == "MCAR":
                    is_missing = self.rng.random() < p
                elif mech == "MAR":
                    aux_name = miss_cfg.get("auxiliary_feature")
                    aux_val = updated.get(aux_name) if aux_name else None
                    if isinstance(aux_val, (int, float)):
                        vals = [v for v in updated.values() if isinstance(v, (int, float))]
                        if len(vals) >= 2:
                            vmin = min(vals)
                            vmax = max(vals)
                            norm = 0.0 if vmax - vmin <= 1e-9 else (float(aux_val) - vmin) / (vmax - vmin)
                            is_missing = self.rng.random() < p * (1.0 + norm)
                        else:
                            is_missing = self.rng.random() < p
                    else:
                        is_missing = self.rng.random() < p
                else:  # MNAR or default
                    is_missing = self.rng.random() < p

                if is_missing:
                    updated[feat] = None

            # Invalid string values
            inv_cfg = cfg.get("invalid_values", {})
            if inv_cfg.get("enabled", False) and updated.get(feat) is not None:
                if self.rng.random() < float(inv_cfg.get("probability", 0.0)):
                    updated[feat] = str(updated[feat])

        return updated

    def next_row(self) -> Dict[str, Any]:
        """Produce the next simulated reading row, preserving stuck sequences."""
        # Return a stuck row if within stuck duration
        if self.stuck_remaining > 0 and self.stuck_row is not None:
            self.stuck_remaining -= 1
            return dict(self.stuck_row)

        # Generate a fresh row
        row = {feat: self._step_feature(feat) for feat in self.features}

        if self.scenario_effects:
            row = self.scenario_effects.apply(row, tick=self.tick)

        if self.correlation_adjuster:
            row = self.correlation_adjuster.apply(row)

        self.tick += 1

        row = self._apply_missing_and_invalid(row)

        # Possibly enter global stuck state starting next tick
        g_cfg = self.noise_config.get("global", {}).get("stuck_values", {})
        if g_cfg.get("enabled", False):
            prob = float(g_cfg.get("probability", 0.0))
            if self.rng.random() < prob:
                duration = int(g_cfg.get("duration", 1))
                self.stuck_row = dict(row)
                self.stuck_remaining = max(0, duration - 1)

        return row
