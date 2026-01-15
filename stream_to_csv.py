"""
Continuous CSV streaming of coal mine sensor data using a stateful simulator.

Usage example:
  python stream_to_csv.py --interval 1.0 --output data/stream/coal_mine_stream.csv
"""

import argparse
import csv
import os
import sys
import time
from pathlib import Path
from typing import Optional

import pandas as pd

from src import (
    load_features_config,
    load_noise_config,
    load_scenarios_config,
    load_correlations_config
)
from src.streaming_simulator import StatefulSensorSimulator


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stream sensor data to CSV continuously")
    parser.add_argument("--features", default="config/features.json", help="Path to features config JSON")
    parser.add_argument("--noise-config", default="config/noise_config.json", help="Path to noise config JSON")
    parser.add_argument("--scenario-config", default="config/scenarios.json", help="Path to scenario config JSON")
    parser.add_argument("--correlation-config", default="config/correlations.json", help="Path to correlation config JSON")
    parser.add_argument("--scenario", default="normal", help="Scenario key to simulate")
    parser.add_argument("--output", default="data/stream/coal_mine_stream.csv", help="Output CSV path")
    parser.add_argument("--interval", type=float, default=1.0, help="Seconds between ticks")
    parser.add_argument("--batch-size", type=int, default=1, help="Rows per tick")
    parser.add_argument("--random-state", type=int, default=42, help="Random seed")
    parser.add_argument("--duration", type=float, default=-1, help="Seconds to run (-1 = forever)")
    parser.add_argument("--max-bytes", type=int, default=0, help="Rotate file if size exceeds this (0 = no rotation)")
    return parser.parse_args()


def ensure_parent(path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def write_header_if_needed(path: str, fieldnames) -> None:
    if not Path(path).exists() or os.path.getsize(path) == 0:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_NONNUMERIC)
            writer.writeheader()


def rotate_if_needed(path: str, max_bytes: int) -> None:
    if max_bytes and Path(path).exists() and os.path.getsize(path) > max_bytes:
        ts = int(time.time())
        rotated = f"{Path(path).with_suffix('')}.{ts}{Path(path).suffix}"
        os.replace(path, rotated)


def main() -> None:
    args = parse_args()

    features = load_features_config(args.features)
    noise_cfg = load_noise_config(args.noise_config)
    scenario_cfg = load_scenarios_config(args.scenario_config)
    correlation_cfg = load_correlations_config(args.correlation_config)

    simulator = StatefulSensorSimulator(
        features,
        noise_cfg,
        random_state=args.random_state,
        scenario=args.scenario,
        scenario_config=scenario_cfg,
        correlation_config=correlation_cfg,
        tick_minutes=max(args.interval / 60.0, 1e-3),
    )

    ensure_parent(args.output)
    fieldnames = ["timestamp", *features.keys()]
    write_header_if_needed(args.output, fieldnames)

    start_time = time.time()
    try:
        while True:
            batch_rows = []
            for _ in range(max(1, args.batch_size)):
                row = simulator.next_row()
                payload = {"timestamp": time.time()}
                payload.update(row)
                batch_rows.append(payload)

            # Append to CSV
            rotate_if_needed(args.output, args.max_bytes)
            with open(args.output, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore", quoting=csv.QUOTE_NONNUMERIC)
                for r in batch_rows:
                    writer.writerow(r)

            # Brief log
            print(f"wrote {len(batch_rows)} rows -> {args.output}")

            # Stop if duration reached
            if args.duration > 0 and (time.time() - start_time) >= args.duration:
                print("Duration reached. Stopping.")
                break

            time.sleep(max(0.0, args.interval))

    except KeyboardInterrupt:
        print("Interrupted by user. Exiting.")
    except Exception as e:
        print(f"Error occurred: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
