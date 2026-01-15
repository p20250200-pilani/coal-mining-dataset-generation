"""
Configuration loader for coal mine sensor simulator.
Handles loading and validation of feature and noise configurations.
"""

import json
from pathlib import Path

# Default noise configuration template
DEFAULT_NOISE_CONFIG = {
    "CH4": {
        "gaussian_noise": {"enabled": True, "std_dev": 0.01},
        "bias": {"enabled": True, "value": 0.01},
        "drift": {"enabled": True, "rate": 0.002, "type": "random_walk", "max_drift": 0.5},
        "quantization": {"enabled": True, "resolution": 0.01},
        "outliers": {"enabled": True, "probability": 0.005, "magnitude": 4.0},
        "missing_data": {"enabled": True, "probability": 0.003, "mechanism": "MCAR", "auxiliary_feature": None},
        "invalid_values": {"enabled": True, "probability": 0.001}
    },
    "CO": {
        "gaussian_noise": {"enabled": True, "std_dev": 1.0},
        "bias": {"enabled": True, "value": 0.5},
        "drift": {"enabled": True, "rate": 0.01, "type": "random_walk", "max_drift": 5.0},
        "quantization": {"enabled": True, "resolution": 1.0},
        "outliers": {"enabled": True, "probability": 0.005, "magnitude": 4.0},
        "missing_data": {"enabled": True, "probability": 0.01, "mechanism": "MAR", "auxiliary_feature": "Temperature"},
        "invalid_values": {"enabled": True, "probability": 0.0015}
    },
    "CO2": {
        "gaussian_noise": {"enabled": True, "std_dev": 30.0},
        "bias": {"enabled": True, "value": 10.0},
        "drift": {"enabled": True, "rate": 0.5, "type": "random_walk", "max_drift": 50.0},
        "quantization": {"enabled": True, "resolution": 1.0},
        "outliers": {"enabled": True, "probability": 0.004, "magnitude": 3.0},
        "missing_data": {"enabled": True, "probability": 0.003, "mechanism": "MNAR", "auxiliary_feature": None},
        "invalid_values": {"enabled": True, "probability": 0.001}
    },
    "H2S": {
        "gaussian_noise": {"enabled": True, "std_dev": 0.2},
        "bias": {"enabled": True, "value": 0.1},
        "drift": {"enabled": True, "rate": 0.02, "type": "random_walk", "max_drift": 0.5},
        "quantization": {"enabled": True, "resolution": 0.1},
        "outliers": {"enabled": True, "probability": 0.004, "magnitude": 4.0},
        "missing_data": {"enabled": True, "probability": 0.003, "mechanism": "MCAR", "auxiliary_feature": None},
        "invalid_values": {"enabled": True, "probability": 0.001}
    },
    "SO2": {
        "gaussian_noise": {"enabled": True, "std_dev": 0.08},
        "bias": {"enabled": True, "value": 0.05},
        "drift": {"enabled": True, "rate": 0.01, "type": "random_walk", "max_drift": 0.05},
        "quantization": {"enabled": True, "resolution": 0.1},
        "outliers": {"enabled": True, "probability": 0.004, "magnitude": 4.0},
        "missing_data": {"enabled": True, "probability": 0.003, "mechanism": "MAR", "auxiliary_feature": "Humidity"},
        "invalid_values": {"enabled": True, "probability": 0.001}
    },
    "NH3": {
        "gaussian_noise": {"enabled": True, "std_dev": 0.6},
        "bias": {"enabled": True, "value": 0.25},
        "drift": {"enabled": True, "rate": 0.02, "type": "random_walk", "max_drift": 1.0},
        "quantization": {"enabled": True, "resolution": 0.5},
        "outliers": {"enabled": True, "probability": 0.004, "magnitude": 4.0},
        "missing_data": {"enabled": True, "probability": 0.003, "mechanism": "MNAR", "auxiliary_feature": None},
        "invalid_values": {"enabled": True, "probability": 0.001}
    },
    "NO": {
        "gaussian_noise": {"enabled": True, "std_dev": 0.6},
        "bias": {"enabled": True, "value": 0.25},
        "drift": {"enabled": True, "rate": 0.02, "type": "random_walk", "max_drift": 1.0},
        "quantization": {"enabled": True, "resolution": 0.5},
        "outliers": {"enabled": True, "probability": 0.004, "magnitude": 4.0},
        "missing_data": {"enabled": True, "probability": 0.003, "mechanism": "MCAR", "auxiliary_feature": None},
        "invalid_values": {"enabled": True, "probability": 0.001}
    },
    "NO2": {
        "gaussian_noise": {"enabled": True, "std_dev": 0.12},
        "bias": {"enabled": True, "value": 0.08},
        "drift": {"enabled": True, "rate": 0.01, "type": "random_walk", "max_drift": 0.3},
        "quantization": {"enabled": True, "resolution": 0.05},
        "outliers": {"enabled": True, "probability": 0.004, "magnitude": 4.0},
        "missing_data": {"enabled": True, "probability": 0.005, "mechanism": "MAR", "auxiliary_feature": "Temperature"},
        "invalid_values": {"enabled": True, "probability": 0.001}
    },
    "PM2.5": {
        "gaussian_noise": {"enabled": True, "std_dev": 3.0},
        "bias": {"enabled": True, "value": 1.0},
        "drift": {"enabled": True, "rate": 0.3, "type": "random_walk", "max_drift": 6.0},
        "quantization": {"enabled": True, "resolution": 1.0},
        "outliers": {"enabled": True, "probability": 0.02, "magnitude": 10.0},
        "missing_data": {"enabled": True, "probability": 0.01, "mechanism": "MNAR", "auxiliary_feature": None},
        "invalid_values": {"enabled": True, "probability": 0.002}
    },
    "PM10": {
        "gaussian_noise": {"enabled": True, "std_dev": 6.0},
        "bias": {"enabled": True, "value": 2.0},
        "drift": {"enabled": True, "rate": 0.5, "type": "random_walk", "max_drift": 10.0},
        "quantization": {"enabled": True, "resolution": 1.0},
        "outliers": {"enabled": True, "probability": 0.02, "magnitude": 10.0},
        "missing_data": {"enabled": True, "probability": 0.01, "mechanism": "MCAR", "auxiliary_feature": None},
        "invalid_values": {"enabled": True, "probability": 0.002}
    },
    "Temperature": {
        "gaussian_noise": {"enabled": True, "std_dev": 0.2},
        "bias": {"enabled": True, "value": 0.1},
        "drift": {"enabled": True, "rate": 0.01, "type": "random_walk", "max_drift": 0.8},
        "quantization": {"enabled": True, "resolution": 0.1},
        "outliers": {"enabled": True, "probability": 0.002, "magnitude": 2.0},
        "missing_data": {"enabled": True, "probability": 0.003, "mechanism": "MAR", "auxiliary_feature": "Humidity"},
        "invalid_values": {"enabled": True, "probability": 0.001}
    },
    "Humidity": {
        "gaussian_noise": {"enabled": True, "std_dev": 1.0},
        "bias": {"enabled": True, "value": 0.5},
        "drift": {"enabled": True, "rate": 0.02, "type": "random_walk", "max_drift": 1.0},
        "quantization": {"enabled": True, "resolution": 0.1},
        "outliers": {"enabled": True, "probability": 0.002, "magnitude": 2.0},
        "missing_data": {"enabled": True, "probability": 0.003, "mechanism": "MNAR", "auxiliary_feature": None},
        "invalid_values": {"enabled": True, "probability": 0.001}
    },
    "global": {
        "stuck_values": {
            "enabled": True,
            "probability": 0.001,
            "duration": 5
        }
    }
}

DEFAULT_SCENARIOS_CONFIG = {
    "normal": {
        "tick_minutes": 1.0,
        "diurnal": {
            "period_minutes": 1440,
            "temperature_amplitude": 2.5,
            "humidity_amplitude": 8.0,
            "humidity_phase_deg": 75
        }
    },
    "ventilation_failure": {
        "inherits": "normal",
        "gas_rise_pct_per_hour": 0.08,
        "temperature_rise_per_hour": 0.15,
        "humidity_rise_per_hour": -0.04
    },
    "methane_leak": {
        "inherits": "normal",
        "ch4_spike_value": 3.0,
        "ch4_rise_minutes": 20,
        "secondary_gas_gain": 0.08,
        "pm_gain": 0.25
    },
    "combustion": {
        "inherits": "normal",
        "co_spike_value": 150.0,
        "co_rise_minutes": 8,
        "co2_spike_value": 2500.0,
        "pm_gain_per_co": 0.6,
        "temperature_rise_per_hour": 0.4,
        "humidity_drop_per_hour": 0.8,
        "nox_gain": 0.45
    },
    "dust_event": {
        "inherits": "normal",
        "pm_peak": 450.0,
        "pm_event_duration_minutes": 12,
        "pm_event_period_minutes": 120,
        "co_spike": 30.0,
        "nox_spike": 15.0,
        "humidity_drop_during_event": 6.0,
        "temperature_bump_during_event": 0.8
    }
}

DEFAULT_CORRELATIONS_CONFIG = {
    "pairwise": [
        {"source": "PM10", "target": "PM2.5", "mode": "ratio", "ratio": 0.65, "blend": 0.7},
        {"source": "PM2.5", "target": "CO", "coeff": 0.25},
        {"source": "PM2.5", "target": "SO2", "coeff": 0.18},
        {"source": "PM2.5", "target": "NO2", "coeff": 0.2},
        {"source": "PM2.5", "target": "NO", "coeff": 0.18},
        {"source": "NO", "target": "NO2", "coeff": 0.85}
    ],
    "humidity_effect": {
        "threshold": 72.0,
        "strength": 0.12,
        "targets": ["PM2.5", "PM10", "CO", "SO2", "NO", "NO2"]
    },
    "temperature_effect": {
        "baseline": 28.0,
        "strength": -0.08,
        "targets": ["PM2.5", "PM10", "CO", "SO2", "NO", "NO2"]
    }
}


def load_features_config(filepath="config/features.json"):
    """Load feature configuration from JSON file."""
    with open(filepath, 'r') as f:
        features = json.load(f)
    
    # Convert lists back to tuples for consistency with original code
    for feature, config in features.items():
        config["safe"] = tuple(config["safe"])
        config["unsafe"] = tuple(config["unsafe"])
    
    return features


def create_default_noise_config(filepath="config/noise_config.json"):
    """Create default noise configuration file."""
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w') as f:
        json.dump(DEFAULT_NOISE_CONFIG, f, indent=4)
    print(f"Default noise configuration saved to {filepath}")


def load_noise_config(filepath="config/noise_config.json"):
    """Load noise configuration from JSON file."""
    if not Path(filepath).exists():
        print(f"Config file not found. Creating default config at {filepath}")
        create_default_noise_config(filepath)
    
    with open(filepath, 'r') as f:
        return json.load(f)


def load_scenarios_config(filepath="config/scenarios.json"):
    """Load scenario configuration from JSON file."""
    path = Path(filepath)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(DEFAULT_SCENARIOS_CONFIG, f, indent=4)
        print(f"Default scenario configuration saved to {filepath}")
    with open(path, 'r') as f:
        return json.load(f)


def load_correlations_config(filepath="config/correlations.json"):
    """Load correlation configuration from JSON file."""
    path = Path(filepath)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(DEFAULT_CORRELATIONS_CONFIG, f, indent=4)
        print(f"Default correlation configuration saved to {filepath}")
    with open(path, 'r') as f:
        return json.load(f)


def validate_noise_config(noise_config, features):
    """Validate that noise config matches available features."""
    for feature in features.keys():
        if feature not in noise_config:
            print(f"Warning: No noise configuration found for feature '{feature}'")
    
    for feature in noise_config.keys():
        if feature != "global" and feature not in features:
            print(f"Warning: Noise configuration exists for unknown feature '{feature}'")
    
    return True