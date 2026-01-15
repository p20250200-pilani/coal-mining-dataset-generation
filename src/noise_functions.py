"""
Noise application functions for coal mine sensor simulator.
Implements various types of sensor noise and data quality issues.
"""

import numpy as np
import pandas as pd


def apply_gaussian_noise(values, std_dev):
    """Add Gaussian noise to sensor values."""
    noise = np.random.normal(0, std_dev, len(values))
    return values + noise


def apply_bias(values, bias_value):
    """Add systematic bias to sensor values."""
    return values + bias_value


def apply_drift(values, drift_rate, drift_type="random_walk", max_drift=None):
    """
    Apply sensor drift over time.
    
    Args:
        values: Array of sensor values
        drift_rate: Rate of drift
        drift_type: Type of drift ("random_walk", "sinusoidal", or "linear")
        max_drift: Maximum absolute drift value to clip to (None for no clipping)
    """
    if drift_type == "random_walk":
        drift = np.cumsum(np.random.normal(0, drift_rate, len(values)))
    elif drift_type == "sinusoidal":
        drift = drift_rate * np.sin(np.linspace(0, 4*np.pi, len(values)))
    else:  # linear
        drift = drift_rate * np.linspace(0, 1, len(values))
    
    # Clip drift to max_drift if specified
    if max_drift is not None:
        drift = np.clip(drift, -max_drift, max_drift)
    
    return values + drift


def apply_quantization(values, resolution):
    """Apply quantization to simulate sensor resolution limits."""
    return np.round(values / resolution) * resolution


def apply_outliers(values, probability, magnitude, std_dev):
    """
    Add outliers to sensor data.
    
    Args:
        values: Array of sensor values
        probability: Probability of outlier occurrence
        magnitude: Multiplier for outlier size (relative to std_dev)
        std_dev: Standard deviation for outlier generation
    """
    outlier_mask = np.random.random(len(values)) < probability
    outlier_noise = np.random.normal(0, magnitude * std_dev, len(values))
    values[outlier_mask] += outlier_noise[outlier_mask]
    return values


def apply_missing_data(values, probability, mechanism="MCAR", auxiliary_data=None):
    """
    Apply missing data based on mechanism type.
    
    Args:
        values: Array of sensor values
        probability: Base probability of missing data
        mechanism: Missing data mechanism ("MCAR", "MAR", "MNAR")
        auxiliary_data: Auxiliary feature for MAR mechanism
    
    Mechanisms:
        - MCAR (Missing Completely At Random): Random missing values
        - MAR (Missing At Random): Depends on auxiliary_data
        - MNAR (Missing Not At Random): Depends on the values themselves
    """
    if mechanism == "MCAR":
        missing_mask = np.random.random(len(values)) < probability
    
    elif mechanism == "MAR" and auxiliary_data is not None:
        # Missing depends on auxiliary data (e.g., high temperature increases missingness)
        aux_normalized = (auxiliary_data - np.nanmin(auxiliary_data)) / (np.nanmax(auxiliary_data) - np.nanmin(auxiliary_data) + 1e-10)
        adjusted_prob = probability * (1 + aux_normalized)
        missing_mask = np.random.random(len(values)) < adjusted_prob
    
    elif mechanism == "MNAR":
        # Missing depends on the value itself (e.g., extreme values more likely to be missing)
        val_normalized = np.abs((values - np.nanmean(values)) / (np.nanstd(values) + 1e-10))
        adjusted_prob = probability * (1 + val_normalized)
        missing_mask = np.random.random(len(values)) < adjusted_prob
    
    else:
        # Default to MCAR if mechanism not recognized or no auxiliary data for MAR
        missing_mask = np.random.random(len(values)) < probability
    
    values[missing_mask] = np.nan
    return values


def get_invalid_value_indices(values, probability):
    """
    Get indices where invalid values (string format) should be applied.
    Returns a boolean mask of indices to convert to strings.
    """
    invalid_mask = np.random.random(len(values)) < probability
    return invalid_mask


def apply_noise_to_feature(values, feature_name, noise_config, features, df_full=None):
    """
    Apply all configured noise types to a feature.
    
    Args:
        values: Array of sensor values
        feature_name: Name of the feature
        noise_config: Noise configuration dictionary
        features: Feature configuration dictionary
        df_full: Full dataframe for auxiliary feature access (for MAR)
    
    Returns:
        tuple: (noisy_values, invalid_indices)
    """
    cfg = noise_config.get(feature_name, {})
    ranges = features[feature_name]
    min_val = min(ranges["safe"][0], ranges["unsafe"][0])
    max_val = max(ranges["safe"][1], ranges["unsafe"][1])

    # Apply various noise types
    if cfg.get("gaussian_noise", {}).get("enabled", False):
        values = apply_gaussian_noise(values, cfg["gaussian_noise"]["std_dev"])
    
    if cfg.get("bias", {}).get("enabled", False):
        values = apply_bias(values, cfg["bias"]["value"])
    
    if cfg.get("drift", {}).get("enabled", False):
        values = apply_drift(values, cfg["drift"]["rate"], cfg["drift"].get("type", "random_walk"), cfg["drift"].get("max_drift"))

    # Clip to valid range
    values = np.clip(values, min_val, max_val)

    if cfg.get("quantization", {}).get("enabled", False):
        values = apply_quantization(values, cfg["quantization"]["resolution"])
    
    if cfg.get("outliers", {}).get("enabled", False):
        values = apply_outliers(values.copy(), cfg["outliers"]["probability"], 
                               cfg["outliers"]["magnitude"], 
                               cfg.get("gaussian_noise", {}).get("std_dev", 1.0))
        values = np.clip(values, min_val, max_val)
    
    # Apply missing data
    if cfg.get("missing_data", {}).get("enabled", False):
        mechanism = cfg["missing_data"].get("mechanism", "MCAR")
        auxiliary_feature = cfg["missing_data"].get("auxiliary_feature", None)
        
        # Get auxiliary data if MAR and auxiliary feature is specified
        auxiliary_data = None
        if mechanism == "MAR" and auxiliary_feature and df_full is not None:
            if auxiliary_feature in df_full.columns:
                auxiliary_data = df_full[auxiliary_feature].values
            else:
                print(f"Warning: Auxiliary feature '{auxiliary_feature}' not found for {feature_name}. Using MCAR instead.")
        
        values = apply_missing_data(
            values.copy(), 
            cfg["missing_data"]["probability"],
            mechanism=mechanism,
            auxiliary_data=auxiliary_data
        )
    
    # Get invalid value indices (will be applied after dataframe creation)
    invalid_indices = None
    if cfg.get("invalid_values", {}).get("enabled", False):
        invalid_indices = get_invalid_value_indices(
            values.copy(),
            cfg["invalid_values"]["probability"]
        )
    
    return values, invalid_indices


def apply_global_stuck_values(df, probability, duration):
    """
    Apply stuck values to entire rows (all sensors stuck at once).
    
    Args:
        df: DataFrame with sensor data
        probability: Probability of stuck value occurrence
        duration: Number of consecutive rows to keep stuck
    
    Returns:
        DataFrame with stuck values applied
    """
    df_stuck = df.copy()
    i = 0
    while i < len(df_stuck):
        if np.random.random() < probability:
            # Get the current row values
            stuck_row = df_stuck.iloc[i].copy()
            stuck_length = min(duration, len(df_stuck) - i)
            
            # Replicate this row for the duration
            for j in range(stuck_length):
                df_stuck.iloc[i + j] = stuck_row
            
            i += stuck_length
        else:
            i += 1
    
    return df_stuck


def apply_string_invalid_values(df, invalid_indices_dict):
    """
    Convert numeric values to string format for invalid entries.
    This simulates sensor errors that return string representations.
    
    Args:
        df: DataFrame with sensor data
        invalid_indices_dict: Dictionary mapping features to boolean masks
    
    Returns:
        DataFrame with invalid values converted to strings
    """
    df_mixed = df.copy()
    
    for feature, invalid_mask in invalid_indices_dict.items():
        if invalid_mask is not None and invalid_mask.any():
            # Convert to object dtype to allow mixed types
            df_mixed[feature] = df_mixed[feature].astype(object)
            # Convert invalid entries to strings
            df_mixed.loc[invalid_mask, feature] = df_mixed.loc[invalid_mask, feature].apply(
                lambda x: str(x) if pd.notna(x) else x
            )
    
    return df_mixed