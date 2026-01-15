"""
Coal Mine Sensor Simulator
A modular system for generating realistic coal mine sensor data with configurable noise.
"""

from .config_loader import (
    load_features_config,
    load_noise_config,
    create_default_noise_config,
    validate_noise_config,
    load_scenarios_config,
    load_correlations_config
)

from .dataset_generator import (
    generate_dataset,
    save_dataset,
    print_dataset_summary,
    count_string_values
)

from .visualization import (
    plot_dataset,
    plot_comparison,
    plot_time_series,
    plot_correlation_matrix,
    plot_missing_data_pattern
)

__all__ = [
    # Config functions
    'load_features_config',
    'load_noise_config',
    'create_default_noise_config',
    'validate_noise_config',
    'load_scenarios_config',
    'load_correlations_config',
    
    # Generator functions
    'generate_dataset',
    'save_dataset',
    'print_dataset_summary',
    'count_string_values',
    
    # Visualization functions
    'plot_dataset',
    'plot_comparison',
    'plot_time_series',
    'plot_correlation_matrix',
    'plot_missing_data_pattern'
]

__version__ = '1.0.0'