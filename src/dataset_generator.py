"""
Dataset generator for coal mine sensor simulator.
Main logic for generating clean and noisy sensor datasets.
"""

import numpy as np
import pandas as pd
import csv
from pathlib import Path
from .noise_functions import (
    apply_noise_to_feature,
    apply_global_stuck_values,
    apply_string_invalid_values
)
from .scenario_effects import ScenarioEffects, CorrelationAdjuster


def generate_dataset(
    features,
    n_samples=1000,
    random_state=None,
    noise_config=None,
    apply_noise=True,
    *,
    scenario="normal",
    scenario_config=None,
    correlation_config=None
):
    """
    Generate coal mine sensor dataset with optional noise.
    
    Args:
        features: Feature configuration dictionary
        n_samples: Number of samples to generate
        random_state: Random seed for reproducibility
        noise_config: Noise configuration dictionary
        apply_noise: Whether to apply noise to the dataset
        scenario: Scenario name or type (str), default "normal"
        scenario_config: Configuration for scenario effects (dict), optional
        correlation_config: Configuration for feature correlations (dict), optional
    Returns:
        DataFrame with generated sensor data
    """
    if random_state is not None:
        np.random.seed(random_state)
    
    if noise_config is None:
        noise_config = {}
    
    data = {}

    # Generate base data
    for feature, ranges in features.items():
        # 80% in safe range, 20% in unsafe range
        n_in = int(0.8 * n_samples)
        n_out = n_samples - n_in
        
        safe_vals = np.random.uniform(ranges["safe"][0], ranges["safe"][1], n_in)
        unsafe_vals = np.random.uniform(ranges["unsafe"][0], ranges["unsafe"][1], n_out)
        
        values = np.concatenate([safe_vals, unsafe_vals])
        np.random.shuffle(values)
        data[feature] = values

    df = pd.DataFrame(data)

    scenario_effects = None
    if scenario_config is not None:
        scenario_effects = ScenarioEffects(
            features,
            scenario,
            scenario_config,
            rng=np.random.default_rng(random_state),
        )

    correlation_adjuster = None
    if correlation_config is not None:
        correlation_adjuster = CorrelationAdjuster(features, correlation_config)

    if scenario_effects or correlation_adjuster:
        col_positions = {col: idx for idx, col in enumerate(df.columns)}
        values = df.values
        for idx in range(len(df)):
            row = {col: values[idx, col_positions[col]] for col in df.columns}
            if scenario_effects:
                row = scenario_effects.apply(row)
            if correlation_adjuster:
                row = correlation_adjuster.apply(row)
            for col, pos in col_positions.items():
                values[idx, pos] = row[col]

    # Track invalid indices for each feature
    invalid_indices_dict = {}

    # Apply noise to features
    if apply_noise:
        for feature in features.keys():
            values, invalid_indices = apply_noise_to_feature(
                df[feature].values, 
                feature, 
                noise_config,
                features,
                df_full=df  # Pass full dataframe for auxiliary feature access
            )
            df[feature] = values
            invalid_indices_dict[feature] = invalid_indices
        
        # Apply global stuck values to entire rows
        global_cfg = noise_config.get("global", {})
        if global_cfg.get("stuck_values", {}).get("enabled", False):
            df = apply_global_stuck_values(
                df,
                global_cfg["stuck_values"]["probability"],
                global_cfg["stuck_values"]["duration"]
            )
        
        # Apply string invalid values
        df = apply_string_invalid_values(df, invalid_indices_dict)

    return df


def save_dataset(df, filepath, preserve_strings=False):
    """
    Save dataset to CSV file.
    
    Args:
        df: DataFrame to save
        filepath: Output file path
        preserve_strings: If True, use quoting to preserve string values
    """
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    
    if preserve_strings:
        df.to_csv(filepath, index=False, quoting=csv.QUOTE_NONNUMERIC)
    else:
        df.to_csv(filepath, index=False)
    
    print(f"Dataset saved to {filepath}")


def count_string_values(df):
    """
    Count string values (invalid sensor readings) per feature.
    
    Args:
        df: DataFrame to analyze
    
    Returns:
        Series with count of string values per column
    """
    string_counts = {}
    for col in df.columns:
        string_counts[col] = df[col].apply(lambda x: isinstance(x, str)).sum()
    return pd.Series(string_counts)


def print_dataset_summary(df, dataset_name="Dataset"):
    """
    Print summary statistics for a dataset.
    
    Args:
        df: DataFrame to summarize
        dataset_name: Name to display in summary
    """
    print(f"\n{'='*60}")
    print(f"{dataset_name} Summary")
    print(f"{'='*60}")
    print(f"\nShape: {df.shape[0]} rows × {df.shape[1]} columns")
    
    print(f"\nFirst 20 rows:")
    print(df.head(20))
    
    print(f"\nStatistics (numeric values only):")
    # Convert to numeric for statistics, coercing strings to NaN
    df_numeric = df.apply(pd.to_numeric, errors='coerce')
    print(df_numeric.describe())
    
    print(f"\nMissing values per feature:")
    print(df.isnull().sum())
    
    # Check for string values
    string_counts = count_string_values(df)
    if string_counts.sum() > 0:
        print(f"\nString/Invalid values per feature:")
        print(string_counts)
    
    print(f"\n{'='*60}\n")