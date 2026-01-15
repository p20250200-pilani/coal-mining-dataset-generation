# Coal Mine Sensor Simulator

A modular Python system for generating realistic coal mine sensor data with configurable noise patterns, environmental scenarios, and data quality issues.

---

## Table of Contents

### Part 1: User Guide
- [Quick Start](#quick-start)
- [Configuration Guide](#configuration-guide)
- [Usage Examples](#usage-examples)
- [Output Files](#output-files)
- [Customization Tips](#customization-tips)

### Part 2: Developer Reference
- [Architecture Overview](#architecture-overview)
- [Complete API Reference](#complete-api-reference)
- [Code Structure](#code-structure)
- [Extension Guide](#extension-guide)

---

# Part 1: User Guide

This section is for users who want to run the simulator and customize it through configuration files without modifying code.

## Quick Start

### Installation

1. Clone or download the repository
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configuration files are auto-generated on first run if they don't exist:
   - `config/noise_config.json` - Auto-generated with defaults
   - `config/scenarios.json` - Auto-generated with defaults
   - `config/correlations.json` - Auto-generated with defaults
   - `config/features.json` - Must be created manually (see Configuration Guide)

### Basic Usage

**Batch Generation** - Generate datasets with a single command:

```bash
python batch_generator.py --scenario combustion --n-samples 5000
```

This will:
1. Load configurations from `config/`
2. Generate 5,000 samples of clean data
3. Generate 5,000 samples of noisy data
4. Save datasets to `data/clean/` and `data/noisy/`
5. Display statistics and visualizations

**Streaming Generation** - Continuous real-time data generation:

```bash
python stream_to_csv.py --scenario methane_leak --output data/stream/coal_mine_stream.csv --interval 1.0
```

The streaming generator maintains state across ticks, preserving sensor drift and stuck value sequences for realistic continuous operation.

## Configuration Guide

All customization is done through JSON configuration files in the `config/` directory.

### Feature Configuration (`config/features.json`)

Defines sensor types, safe/unsafe ranges, and units. This file must be created manually.

**Example:**
```json
{
    "CH4": {
        "safe": [0, 1.25],
        "unsafe": [1.25, 5],
        "unit": "%vol"
    },
    "CO": {
        "safe": [0, 50],
        "unsafe": [50, 200],
        "unit": "ppm"
    }
}
```

**Available Sensors:** CH4, CO, CO2, H2S, SO2, NH3, NO, NO2, PM2.5, PM10, Temperature, Humidity

### Noise Configuration (`config/noise_config.json`)

Auto-generated on first run. Customize noise parameters for each sensor:

```json
{
    "CH4": {
        "gaussian_noise": {"enabled": true, "std_dev": 0.01},
        "bias": {"enabled": true, "value": 0.01},
        "drift": {"enabled": true, "rate": 0.002, "type": "random_walk", "max_drift": 0.5},
        "quantization": {"enabled": true, "resolution": 0.01},
        "outliers": {"enabled": true, "probability": 0.005, "magnitude": 4.0},
        "missing_data": {
            "enabled": true,
            "probability": 0.003,
            "mechanism": "MCAR",
            "auxiliary_feature": null
        },
        "invalid_values": {"enabled": true, "probability": 0.001}
    },
    "global": {
        "stuck_values": {
            "enabled": true,
            "probability": 0.001,
            "duration": 5
        }
    }
}
```

**Noise Types:**
- `gaussian_noise`: Random Gaussian noise with specified standard deviation
- `bias`: Systematic offset added to all readings
- `drift`: Sensor drift over time (random_walk, sinusoidal, or linear) with optional `max_drift` clipping
- `quantization`: Simulates sensor resolution limits by rounding to specified resolution
- `outliers`: Extreme values with specified probability and magnitude
- `missing_data`: Missing values using MCAR, MAR, or MNAR mechanisms
- `invalid_values`: Converts readings to string format to simulate sensor errors
- `stuck_values`: Global sensor failures where all readings freeze for a duration

**Missing Data Mechanisms:**
- **MCAR (Missing Completely At Random)**: Random missingness
- **MAR (Missing At Random)**: Depends on another feature (e.g., high temperature increases missingness)
- **MNAR (Missing Not At Random)**: Depends on the value itself (e.g., extreme values more likely missing)

### Scenario Configuration (`config/scenarios.json`)

Auto-generated on first run. Defines high-level environmental situations. Each scenario inherits defaults from `normal` and then overrides specific dynamics:

**Available Scenarios:**

- **normal**: Baseline with slow diurnal temperature/humidity cycles
- **ventilation_failure**: Gradual rise in all gases, small temperature increase, humidity stagnation
- **methane_leak**: Rapid CH₄ spike with secondary CO₂/PM increases
- **combustion**: Fast CO rise, slower CO₂ build-up, PM tied to CO, temperature up, humidity down, NOₓ increases
- **dust_event**: Periodic pulses where PM/CO/NOₓ spike, humidity dips, temperature bumps

**Example:**
```json
{
    "normal": {
        "tick_minutes": 1.0,
        "diurnal": {
            "period_minutes": 1440,
            "temperature_amplitude": 2.5,
            "humidity_amplitude": 8.0,
            "humidity_phase_deg": 75
        }
    },
    "methane_leak": {
        "inherits": "normal",
        "ch4_spike_value": 3.0,
        "ch4_rise_minutes": 20,
        "secondary_gas_gain": 0.08,
        "pm_gain": 0.25
    }
}
```

**Creating Custom Scenarios:** Add a new key with `"inherits": "normal"` and override specific parameters. See existing scenarios for parameter examples.

### Correlation Configuration (`config/correlations.json`)

Auto-generated on first run. Controls statistical relationships between sensors:

**Correlation Types:**

- **pairwise**: Linear or ratio-based adjustments between specific sensors
  - `mode: "linear"`: Linear correlation with coefficient
  - `mode: "ratio"`: Enforce ratio relationship (e.g., PM2.5 as 65% of PM10)
- **humidity_effect**: When humidity exceeds threshold, pollutants rise to reflect poor dispersion
- **temperature_effect**: Warmer air reduces pollutant concentrations to mimic improved dispersion

**Example:**
```json
{
    "pairwise": [
        {
            "source": "PM10",
            "target": "PM2.5",
            "mode": "ratio",
            "ratio": 0.65,
            "blend": 0.7
        },
        {
            "source": "NO",
            "target": "NO2",
            "coeff": 0.85
        }
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
```

## Usage Examples

### Batch Generation

**Basic usage:**
```bash
python batch_generator.py
```

**With custom scenario and sample count:**
```bash
python batch_generator.py --scenario combustion --n-samples 10000 --random-state 42
```

**All batch generator options:**
```bash
python batch_generator.py \
  --n-samples 5000 \
  --random-state 42 \
  --scenario normal \
  --features config/features.json \
  --noise-config config/noise_config.json \
  --scenario-config config/scenarios.json \
  --correlation-config config/correlations.json \
  --clean-output data/clean/coal_mine_data_clean.csv \
  --noisy-output data/noisy/coal_mine_data_noisy.csv
```

### Streaming Generation

**Basic streaming:**
```bash
python stream_to_csv.py --scenario methane_leak --output data/stream/coal_mine_stream.csv
```

**Full streaming example with all options:**
```bash
python stream_to_csv.py \
  --features config/features.json \
  --noise-config config/noise_config.json \
  --scenario-config config/scenarios.json \
  --correlation-config config/correlations.json \
  --scenario methane_leak \
  --output data/stream/coal_mine_stream.csv \
  --interval 1.0 \
  --batch-size 1 \
  --random-state 42 \
  --duration -1 \
  --max-bytes 104857600
```

**Streaming Options:**
- `--interval`: Seconds between ticks (default: 1.0)
- `--batch-size`: Rows per tick (default: 1)
- `--duration`: Seconds to run (-1 = forever, default: -1)
- `--max-bytes`: Rotate file when exceeding size in bytes (0 = disabled, default: 0)
- `--random-state`: Random seed for reproducibility

**Note:** The streaming generator maintains state across ticks:
- Sensor drift accumulates over time
- Stuck values persist for the configured duration
- Scenario effects progress based on elapsed time

Press `Ctrl+C` to stop gracefully.

## Output Files

**Batch Generation:**
- `data/clean/coal_mine_data_clean.csv` - Clean sensor data (no noise applied)
- `data/noisy/coal_mine_data_noisy.csv` - Noisy sensor data with quality issues

**Streaming Generation:**
- `data/stream/coal_mine_stream.csv` - Continuous stream of sensor data with timestamps
- If `--max-bytes` is set, files are rotated with timestamp suffix when size limit is reached

## Customization Tips

### Without Modifying Code

1. **Add/Remove Sensors**: Edit `config/features.json` to add new sensor definitions or remove existing ones
2. **Adjust Noise Levels**: Edit `config/noise_config.json` to change noise parameters for each sensor
3. **Create Custom Scenarios**: Add new entries to `config/scenarios.json` with `"inherits": "normal"`
4. **Modify Correlations**: Edit `config/correlations.json` to change sensor relationships
5. **Change Sample Size**: Use `--n-samples` command-line argument
6. **Change Random Seed**: Use `--random-state` command-line argument

### Configuration File Locations

All config files are in the `config/` directory:
- `features.json` - Sensor definitions (must create manually)
- `noise_config.json` - Noise parameters (auto-generated)
- `scenarios.json` - Scenario definitions (auto-generated)
- `correlations.json` - Correlation rules (auto-generated)

---

# Part 2: Developer Reference

This section is for developers who want to understand the codebase architecture, extend functionality, or modify the implementation.

## Architecture Overview

The simulator is organized into modular components:

```
coal_mine_sensor_simulator/
│
├── config/                          # Configuration files
│   ├── features.json                # Sensor feature definitions
│   ├── noise_config.json            # Noise configuration
│   ├── scenarios.json               # Scenario definitions
│   └── correlations.json            # Correlation rules
│
├── src/                             # Core source code
│   ├── __init__.py                 # Package exports
│   ├── config_loader.py            # Configuration loading and validation
│   ├── dataset_generator.py        # Batch dataset generation
│   ├── noise_functions.py          # Noise application functions
│   ├── scenario_effects.py         # Scenario and correlation logic
│   ├── streaming_simulator.py      # Stateful streaming simulator
│   └── visualization.py            # Plotting functions
│
├── data/                            # Output directories
│   ├── clean/                       # Clean datasets
│   ├── noisy/                       # Noisy datasets
│   └── stream/                      # Streaming data
│
├── batch_generator.py               # Batch generation entry point
├── stream_to_csv.py                 # Streaming generation entry point
├── requirements.txt                 # Python dependencies
└── README.md                        # This file
```

### Component Responsibilities

- **config_loader.py**: Loads and validates JSON configurations, auto-generates defaults
- **dataset_generator.py**: Generates batch datasets with scenario and correlation effects
- **noise_functions.py**: Applies various noise types to sensor data
- **scenario_effects.py**: Implements scenario dynamics and correlation adjustments
- **streaming_simulator.py**: Stateful simulator maintaining drift and stuck state across ticks
- **visualization.py**: Plotting and analysis functions

## Complete API Reference

### Configuration Functions (`src.config_loader`)

#### `load_features_config(filepath="config/features.json")`

Load feature configuration from JSON file defining sensor types, safe/unsafe ranges, and units.

**Parameters:**
- `filepath` (str): Path to features configuration file

**Returns:**
- `dict`: Dictionary with feature configurations (safe/unsafe ranges converted to tuples)

**Example:**
```python
from src import load_features_config
features = load_features_config("config/features.json")
```

#### `load_noise_config(filepath="config/noise_config.json")`

Load noise configuration from JSON file. Creates default config if file doesn't exist.

**Parameters:**
- `filepath` (str): Path to noise configuration file

**Returns:**
- `dict`: Dictionary with noise parameters for each feature

**Example:**
```python
from src import load_noise_config
noise_config = load_noise_config()
```

#### `create_default_noise_config(filepath="config/noise_config.json")`

Create default noise configuration file with predefined parameters for all sensors.

**Parameters:**
- `filepath` (str): Path where to save the configuration file

**Example:**
```python
from src import create_default_noise_config
create_default_noise_config("config/custom_noise.json")
```

#### `validate_noise_config(noise_config, features)`

Validate that noise configuration matches available features and warn about mismatches.

**Parameters:**
- `noise_config` (dict): Dictionary with noise configurations
- `features` (dict): Dictionary with feature configurations

**Returns:**
- `bool`: Always returns True (warnings printed to console)

**Example:**
```python
from src import validate_noise_config, load_features_config, load_noise_config
features = load_features_config()
noise_config = load_noise_config()
validate_noise_config(noise_config, features)
```

#### `load_scenarios_config(filepath="config/scenarios.json")`

Load scenario configuration from JSON file. Creates default config if file doesn't exist.

**Parameters:**
- `filepath` (str): Path to scenario configuration file

**Returns:**
- `dict`: Dictionary with scenario definitions

**Example:**
```python
from src import load_scenarios_config
scenarios = load_scenarios_config()
```

#### `load_correlations_config(filepath="config/correlations.json")`

Load correlation configuration from JSON file. Creates default config if file doesn't exist.

**Parameters:**
- `filepath` (str): Path to correlation configuration file

**Returns:**
- `dict`: Dictionary with correlation rules

**Example:**
```python
from src import load_correlations_config
correlations = load_correlations_config()
```

### Dataset Generation Functions (`src.dataset_generator`)

#### `generate_dataset(features, n_samples=1000, random_state=None, noise_config=None, apply_noise=True, *, scenario="normal", scenario_config=None, correlation_config=None)`

Generate coal mine sensor dataset with optional noise application, scenario effects, and correlations.

**Parameters:**
- `features` (dict): Feature configuration dictionary
- `n_samples` (int): Number of samples to generate (default: 1000)
- `random_state` (int, optional): Random seed for reproducibility
- `noise_config` (dict, optional): Noise configuration dictionary
- `apply_noise` (bool): Whether to apply noise to the dataset (default: True)
- `scenario` (str): Scenario key describing macro-behavior (default: "normal")
- `scenario_config` (dict, optional): Scenario configuration dictionary
- `correlation_config` (dict, optional): Correlation configuration dictionary

**Returns:**
- `pandas.DataFrame`: DataFrame with generated sensor data

**Example:**
```python
from src import load_features_config, load_noise_config, load_scenarios_config, load_correlations_config, generate_dataset

features = load_features_config()
noise_config = load_noise_config()
scenarios = load_scenarios_config()
correlations = load_correlations_config()

df = generate_dataset(
    features=features,
    n_samples=10000,
    random_state=42,
    noise_config=noise_config,
    apply_noise=True,
    scenario="combustion",
    scenario_config=scenarios,
    correlation_config=correlations
)
```

#### `save_dataset(df, filepath, preserve_strings=False)`

Save dataset to CSV file with optional string value preservation.

**Parameters:**
- `df` (pandas.DataFrame): DataFrame to save
- `filepath` (str): Output file path
- `preserve_strings` (bool): If True, use quoting to preserve string values (default: False)

**Example:**
```python
from src import save_dataset
save_dataset(df, "data/output.csv", preserve_strings=True)
```

#### `print_dataset_summary(df, dataset_name="Dataset")`

Print comprehensive summary statistics for a dataset including shape, statistics, missing values, and invalid readings.

**Parameters:**
- `df` (pandas.DataFrame): DataFrame to summarize
- `dataset_name` (str): Name to display in summary (default: "Dataset")

**Example:**
```python
from src import print_dataset_summary
print_dataset_summary(df, "Noisy Dataset Analysis")
```

#### `count_string_values(df)`

Count string values (invalid sensor readings) per feature.

**Parameters:**
- `df` (pandas.DataFrame): DataFrame to analyze

**Returns:**
- `pandas.Series`: Series with count of string values per column

**Example:**
```python
from src import count_string_values
invalid_counts = count_string_values(df)
print(invalid_counts)
```

### Noise Application Functions (`src.noise_functions`)

#### `apply_gaussian_noise(values, std_dev)`

Add Gaussian noise to sensor values.

**Parameters:**
- `values` (numpy.ndarray): Array of sensor values
- `std_dev` (float): Standard deviation of noise

**Returns:**
- `numpy.ndarray`: Array with noise applied

#### `apply_bias(values, bias_value)`

Add systematic bias to sensor values.

**Parameters:**
- `values` (numpy.ndarray): Array of sensor values
- `bias_value` (float): Bias amount to add

**Returns:**
- `numpy.ndarray`: Array with bias applied

#### `apply_drift(values, drift_rate, drift_type="random_walk", max_drift=None)`

Apply sensor drift over time with configurable clipping.

**Parameters:**
- `values` (numpy.ndarray): Array of sensor values
- `drift_rate` (float): Rate of drift
- `drift_type` (str): Type of drift ("random_walk", "sinusoidal", "linear")
- `max_drift` (float, optional): Maximum absolute drift value to clip to (None for no clipping)

**Returns:**
- `numpy.ndarray`: Array with drift applied

#### `apply_quantization(values, resolution)`

Apply quantization to simulate sensor resolution limits.

**Parameters:**
- `values` (numpy.ndarray): Array of sensor values
- `resolution` (float): Quantization resolution

**Returns:**
- `numpy.ndarray`: Quantized values

#### `apply_outliers(values, probability, magnitude, std_dev)`

Add outliers to sensor data.

**Parameters:**
- `values` (numpy.ndarray): Array of sensor values
- `probability` (float): Probability of outlier occurrence
- `magnitude` (float): Multiplier for outlier size (relative to std_dev)
- `std_dev` (float): Standard deviation for outlier generation

**Returns:**
- `numpy.ndarray`: Array with outliers applied

#### `apply_missing_data(values, probability, mechanism="MCAR", auxiliary_data=None)`

Apply missing data based on mechanism type.

**Parameters:**
- `values` (numpy.ndarray): Array of sensor values
- `probability` (float): Base probability of missing data
- `mechanism` (str): Missing data mechanism ("MCAR", "MAR", "MNAR")
- `auxiliary_data` (numpy.ndarray, optional): Auxiliary feature data for MAR mechanism

**Returns:**
- `numpy.ndarray`: Array with missing values (NaN) applied

#### `apply_global_stuck_values(df, probability, duration)`

Apply stuck values to entire rows (all sensors stuck at once).

**Parameters:**
- `df` (pandas.DataFrame): DataFrame with sensor data
- `probability` (float): Probability of stuck value occurrence
- `duration` (int): Number of consecutive rows to keep stuck

**Returns:**
- `pandas.DataFrame`: DataFrame with stuck values applied

#### `apply_string_invalid_values(df, invalid_indices_dict)`

Convert numeric values to string format for invalid entries.

**Parameters:**
- `df` (pandas.DataFrame): DataFrame with sensor data
- `invalid_indices_dict` (dict): Dictionary mapping features to boolean masks

**Returns:**
- `pandas.DataFrame`: DataFrame with invalid values converted to strings

### Scenario and Correlation Classes (`src.scenario_effects`)

#### `ScenarioEffects`

Applies scenario-specific adjustments to sensor readings over time.

**Initialization:**
```python
ScenarioEffects(
    features: Dict[str, Dict[str, Any]],
    scenario: str,
    config: Optional[Dict[str, Any]] = None,
    *,
    rng: Optional[np.random.Generator] = None,
    tick_minutes_override: Optional[float] = None
)
```

**Parameters:**
- `features` (dict): Feature configuration dictionary
- `scenario` (str): Scenario name (e.g., "normal", "combustion", "methane_leak")
- `config` (dict, optional): Scenario configuration dictionary
- `rng` (numpy.random.Generator, optional): Random number generator
- `tick_minutes_override` (float, optional): Override tick duration in minutes

**Methods:**

- `apply(row: Dict[str, Any], tick: Optional[int] = None) -> Dict[str, Any]`
  - Apply scenario effects to a row of sensor data
  - `row`: Dictionary of sensor readings
  - `tick`: Optional tick number (uses internal counter if None)
  - Returns: Updated row dictionary

**Scenario Inheritance:**
Scenarios can inherit from `"normal"` by including `"inherits": "normal"` in their configuration. The base scenario's parameters are loaded first, then overridden by the specific scenario's parameters.

**Example:**
```python
from src.scenario_effects import ScenarioEffects
import numpy as np

features = load_features_config()
scenarios = load_scenarios_config()
rng = np.random.default_rng(42)

scenario_effects = ScenarioEffects(
    features,
    "combustion",
    scenarios,
    rng=rng
)

row = {"CH4": 0.5, "CO": 10.0, "Temperature": 25.0}
updated_row = scenario_effects.apply(row, tick=100)
```

#### `CorrelationAdjuster`

Applies correlation rules to sensor readings.

**Initialization:**
```python
CorrelationAdjuster(
    features: Dict[str, Dict[str, Any]],
    config: Optional[Dict[str, Any]] = None
)
```

**Parameters:**
- `features` (dict): Feature configuration dictionary
- `config` (dict, optional): Correlation configuration dictionary

**Methods:**

- `apply(row: Dict[str, Any]) -> Dict[str, Any]`
  - Apply correlation rules to a row of sensor data
  - `row`: Dictionary of sensor readings
  - Returns: Updated row dictionary

**Correlation Types:**
- **Pairwise Linear**: Adjusts target based on source deviation from baseline
- **Pairwise Ratio**: Enforces ratio relationship (e.g., PM2.5 = 65% of PM10)
- **Humidity Effect**: Increases targets when humidity exceeds threshold
- **Temperature Effect**: Adjusts targets based on temperature deviation from baseline

**Example:**
```python
from src.scenario_effects import CorrelationAdjuster

features = load_features_config()
correlations = load_correlations_config()

correlation_adjuster = CorrelationAdjuster(features, correlations)

row = {"PM10": 100.0, "PM2.5": 50.0, "Humidity": 75.0}
updated_row = correlation_adjuster.apply(row)
```

### Streaming Simulator (`src.streaming_simulator`)

#### `StatefulSensorSimulator`

Stateful simulator that maintains per-feature drift and global stuck state across ticks for realistic continuous operation.

**Initialization:**
```python
StatefulSensorSimulator(
    features: Dict[str, Dict[str, tuple]],
    noise_config: Dict[str, Any],
    *,
    random_state: Optional[int] = None,
    scenario: str = "normal",
    scenario_config: Optional[Dict[str, Any]] = None,
    correlation_config: Optional[Dict[str, Any]] = None,
    tick_minutes: Optional[float] = None
)
```

**Parameters:**
- `features` (dict): Feature configuration dictionary
- `noise_config` (dict): Noise configuration dictionary
- `random_state` (int, optional): Random seed for reproducibility
- `scenario` (str): Scenario name (default: "normal")
- `scenario_config` (dict, optional): Scenario configuration dictionary
- `correlation_config` (dict, optional): Correlation configuration dictionary
- `tick_minutes` (float, optional): Duration of each tick in minutes

**Methods:**

- `next_row() -> Dict[str, Any]`
  - Generate the next row of sensor data
  - Maintains drift state across calls
  - Handles stuck value sequences
  - Applies scenario and correlation effects
  - Returns: Dictionary of sensor readings

**State Management:**
- **Per-feature drift**: Each sensor maintains its own drift value that accumulates over time
- **Global stuck state**: When stuck values occur, all sensors freeze for the configured duration
- **Tick counter**: Tracks elapsed time for scenario effects

**Example:**
```python
from src.streaming_simulator import StatefulSensorSimulator
from src import load_features_config, load_noise_config, load_scenarios_config, load_correlations_config

features = load_features_config()
noise_config = load_noise_config()
scenarios = load_scenarios_config()
correlations = load_correlations_config()

simulator = StatefulSensorSimulator(
    features,
    noise_config,
    random_state=42,
    scenario="methane_leak",
    scenario_config=scenarios,
    correlation_config=correlations,
    tick_minutes=1.0
)

# Generate continuous stream
for i in range(1000):
    row = simulator.next_row()
    print(f"Tick {i}: {row}")
```

### Visualization Functions (`src.visualization`)

#### `plot_dataset(df, title="Dataset Distribution", figsize=(16, 12), scenario=None)`

Plot histograms for all features in the dataset with scenario-specific highlighting.

**Parameters:**
- `df` (pandas.DataFrame): DataFrame with sensor data
- `title` (str): Title for the plot (default: "Dataset Distribution")
- `figsize` (tuple): Figure size as (width, height) (default: (16, 12))
- `scenario` (str, optional): Scenario name for color highlighting

**Example:**
```python
from src import plot_dataset
plot_dataset(df, title="Combustion Scenario", scenario="combustion")
```

#### `plot_comparison(df_clean, df_noisy, feature, figsize=(14, 5))`

Plot comparison between clean and noisy data for a single feature.

**Parameters:**
- `df_clean` (pandas.DataFrame): DataFrame with clean data
- `df_noisy` (pandas.DataFrame): DataFrame with noisy data
- `feature` (str): Feature name to compare
- `figsize` (tuple): Figure size as (width, height) (default: (14, 5))

**Example:**
```python
from src import plot_comparison
plot_comparison(df_clean, df_noisy, feature="CH4")
```

#### `plot_time_series(df, feature, n_samples=500, figsize=(14, 5))`

Plot time series for a specific feature.

**Parameters:**
- `df` (pandas.DataFrame): DataFrame with sensor data
- `feature` (str): Feature name to plot
- `n_samples` (int): Number of samples to plot (default: 500)
- `figsize` (tuple): Figure size as (width, height) (default: (14, 5))

**Example:**
```python
from src import plot_time_series
plot_time_series(df, feature="Temperature", n_samples=1000)
```

#### `plot_correlation_matrix(df, figsize=(12, 10))`

Plot correlation matrix heatmap for all numeric features.

**Parameters:**
- `df` (pandas.DataFrame): DataFrame with sensor data
- `figsize` (tuple): Figure size as (width, height) (default: (12, 10))

**Example:**
```python
from src import plot_correlation_matrix
plot_correlation_matrix(df)
```

#### `plot_missing_data_pattern(df, figsize=(14, 6))`

Visualize missing data patterns across features.

**Parameters:**
- `df` (pandas.DataFrame): DataFrame with sensor data
- `figsize` (tuple): Figure size as (width, height) (default: (14, 6))

**Example:**
```python
from src import plot_missing_data_pattern
plot_missing_data_pattern(df)
```

## Code Structure

### Module Breakdown

**`src/config_loader.py`**
- Configuration loading and validation
- Auto-generation of default configs
- Default templates for noise, scenarios, and correlations

**`src/dataset_generator.py`**
- Batch dataset generation logic
- Integration of scenario effects and correlations
- Noise application orchestration
- Dataset saving and summary functions

**`src/noise_functions.py`**
- Individual noise type implementations
- Per-feature noise application
- Global stuck values and invalid value handling
- Missing data mechanism implementations

**`src/scenario_effects.py`**
- `ScenarioEffects` class: Scenario-specific dynamics
- `CorrelationAdjuster` class: Correlation rule application
- Scenario inheritance mechanism
- Diurnal cycles, gas rises, spikes, and periodic events

**`src/streaming_simulator.py`**
- `StatefulSensorSimulator` class: Stateful continuous generation
- Per-feature drift state management
- Global stuck state handling
- Tick-based progression

**`src/visualization.py`**
- Plotting functions for analysis
- Scenario-specific color highlighting
- Statistical visualizations

## Extension Guide

### Adding a New Scenario

1. Edit `config/scenarios.json` and add a new scenario entry:

```json
{
    "my_custom_scenario": {
        "inherits": "normal",
        "custom_parameter": 0.5
    }
}
```

2. Implement the scenario handler in `src/scenario_effects.py`:

```python
def _apply_my_custom_scenario(self, row: Dict[str, Any], minutes: float, tick: int) -> Dict[str, Any]:
    """Apply custom scenario effects."""
    row = self._apply_normal(row, minutes, tick)
    # Your custom logic here
    return row
```

3. Use the scenario:
```bash
python batch_generator.py --scenario my_custom_scenario
```

### Adding a New Noise Type

1. Implement the noise function in `src/noise_functions.py`:

```python
def apply_custom_noise(values, parameter):
    """Apply custom noise type."""
    # Your implementation
    return modified_values
```

2. Add noise application in `apply_noise_to_feature()`:

```python
if cfg.get("custom_noise", {}).get("enabled", False):
    values = apply_custom_noise(values, cfg["custom_noise"]["parameter"])
```

3. Update default config in `src/config_loader.py`:

```python
"custom_noise": {"enabled": True, "parameter": 0.1}
```

### Adding a New Correlation Rule

1. Edit `config/correlations.json` to add your rule
2. Implement the correlation logic in `CorrelationAdjuster.apply()` or add a new method
3. The correlation will be automatically applied during dataset generation

### Internal Details

**Drift State Management:**
- In batch mode: Drift is calculated per-sample using cumulative operations
- In streaming mode: Drift accumulates in `StatefulSensorSimulator.per_feature[name]["drift"]`
- Drift is clipped to `max_drift` if specified in config

**Scenario Inheritance:**
- Base scenario (`normal`) is loaded first
- Inheriting scenario's parameters override base parameters
- Implemented in `ScenarioEffects.__init__()` via dictionary update

**Missing Data Mechanisms:**
- **MCAR**: Simple random probability
- **MAR**: Probability adjusted based on auxiliary feature value (normalized)
- **MNAR**: Probability adjusted based on the value's deviation from mean

**Stuck Values:**
- Global stuck values affect all sensors simultaneously
- In batch mode: Entire rows are replicated for the duration
- In streaming mode: State is maintained in `StatefulSensorSimulator.stuck_remaining`

## Dependencies

- **numpy** (>=1.21.0): Numerical operations
- **pandas** (>=1.3.0): Data manipulation
- **matplotlib** (>=3.4.0): Basic plotting
- **seaborn** (>=0.11.0): Statistical visualizations
