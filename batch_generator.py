"""
Main entry point for coal mine sensor simulator.
Generates clean and noisy datasets with visualization.
"""

import argparse

from src import (
    load_features_config,
    load_noise_config,
    create_default_noise_config,
    load_scenarios_config,
    load_correlations_config,
    generate_dataset,
    save_dataset,
    print_dataset_summary,
    plot_dataset
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate coal mine datasets")
    parser.add_argument("--n-samples", type=int, default=5000, help="Number of rows to generate")
    parser.add_argument("--random-state", type=int, default=42, help="Random seed")
    parser.add_argument("--scenario", default="normal", help="Scenario name to simulate")
    parser.add_argument("--features", default="config/features.json", help="Features config path")
    parser.add_argument("--noise-config", default="config/noise_config.json", help="Noise config path")
    parser.add_argument("--scenario-config", default="config/scenarios.json", help="Scenario config path")
    parser.add_argument("--correlation-config", default="config/correlations.json", help="Correlation config path")
    parser.add_argument("--clean-output", default="data/clean/coal_mine_data_clean.csv", help="Clean dataset output path")
    parser.add_argument("--noisy-output", default="data/noisy/coal_mine_data_noisy.csv", help="Noisy dataset output path")
    return parser.parse_args()


def main():
    """Main execution function."""
    args = parse_args()

    print("Coal Mine Sensor Data Generator")
    print("=" * 60)

    print("\nLoading configurations...")
    features = load_features_config(args.features)
    print(f"✓ Loaded {len(features)} features")

    create_default_noise_config(args.noise_config)
    noise_config = load_noise_config(args.noise_config)
    scenarios = load_scenarios_config(args.scenario_config)
    correlations = load_correlations_config(args.correlation_config)
    print("✓ Scenario and correlation configs loaded")

    print(f"\nGenerating clean dataset (scenario={args.scenario})...")
    df_clean = generate_dataset(
        features=features,
        n_samples=args.n_samples,
        random_state=args.random_state,
        apply_noise=False,
        scenario=args.scenario,
        scenario_config=scenarios,
        correlation_config=correlations
    )
    print(f"✓ Generated {len(df_clean)} clean samples")

    print("\nGenerating noisy dataset...")
    df_noisy = generate_dataset(
        features=features,
        n_samples=args.n_samples,
        random_state=args.random_state,
        noise_config=noise_config,
        apply_noise=True,
        scenario=args.scenario,
        scenario_config=scenarios,
        correlation_config=correlations
    )
    print(f"✓ Generated {len(df_noisy)} noisy samples")

    print("\nSaving datasets...")
    save_dataset(df_clean, args.clean_output)
    save_dataset(df_noisy, args.noisy_output, preserve_strings=True)
    print("✓ Datasets saved successfully")

    print_dataset_summary(df_clean, "Clean Dataset")
    print_dataset_summary(df_noisy, "Noisy Dataset")

    print("\nGenerating visualizations...")
    print("Plotting clean dataset distribution...")
    plot_dataset(
        df_clean,
        title="Clean Dataset Distribution",
        scenario=args.scenario,
    )

    print("Plotting noisy dataset distribution...")
    plot_dataset(
        df_noisy,
        title="Noisy Dataset Distribution",
        scenario=args.scenario,
    )

    print("\n" + "=" * 60)
    print("Dataset generation complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()