"""
Input/Output utilities for Leto BLRM.
"""

from pathlib import Path
from typing import List, Dict, Any
import json
import csv
import random
from datetime import datetime


def ensure_output_dir(path: str) -> Path:
    """
    Ensure output directory exists.

    Args:
        path: Directory path

    Returns:
        Path object
    """
    output_path = Path(path)
    output_path.mkdir(parents=True, exist_ok=True)
    return output_path


def load_input_data(path: str) -> List[Dict[str, Any]]:
    """
    Load input data from CSV or generate synthetic data.

    Args:
        path: Path to input CSV file

    Returns:
        List of dictionaries representing rows
    """
    input_path = Path(path)

    # If file exists, load it
    if input_path.exists():
        data = []
        with open(input_path, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Convert numeric strings to floats
                converted_row = {}
                for key, value in row.items():
                    try:
                        converted_row[key] = float(value)
                    except (ValueError, TypeError):
                        converted_row[key] = value
                data.append(converted_row)
        print(f"Loaded {len(data)} rows from {path}")
        return data

    # Generate synthetic data
    print(f"Input file not found: {path}, generating synthetic data")
    n_rows = random.randint(100, 300)
    data = []

    for i in range(n_rows):
        row = {
            "id": i,
            "feature_1": random.uniform(0, 100),
            "feature_2": random.uniform(-50, 50),
            "feature_3": random.uniform(0, 1),
            "feature_4": random.uniform(10, 1000),
            "target": random.uniform(0, 10),
        }
        data.append(row)

    print(f"Generated {len(data)} synthetic rows")
    return data


def save_results(output_dir: Path, summary: Dict[str, Any], runs: List[Dict[str, Any]]) -> None:
    """
    Save BLRM results to disk.

    Args:
        output_dir: Directory to save results
        summary: Summary statistics dictionary
        runs: List of per-scenario run dictionaries
    """
    # Save summary as JSON
    summary_path = output_dir / "summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Saved summary to {summary_path}")

    # Save runs as CSV
    runs_path = output_dir / "runs.csv"
    if runs:
        fieldnames = runs[0].keys()
        with open(runs_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(runs)
        print(f"Saved {len(runs)} runs to {runs_path}")

    # Save timestamp metadata
    metadata_path = output_dir / "metadata.json"
    metadata = {
        "completed_at": datetime.utcnow().isoformat(),
        "num_scenarios": len(runs),
        "summary_path": str(summary_path),
        "runs_path": str(runs_path),
    }
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"Saved metadata to {metadata_path}")


def save_input_sample(output_dir: Path, data: List[Dict[str, Any]], max_rows: int = 10) -> None:
    """
    Save a sample of input data for debugging.

    Args:
        output_dir: Directory to save sample
        data: Input data
        max_rows: Maximum rows to save
    """
    sample_path = output_dir / "input_sample.json"
    sample = data[:max_rows]
    with open(sample_path, "w") as f:
        json.dump(sample, f, indent=2)
    print(f"Saved input sample ({len(sample)} rows) to {sample_path}")
