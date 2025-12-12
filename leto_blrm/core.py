"""
Core BLRM scenario runner with baseline metrics.
"""

import time
import random
from typing import List, Dict, Any, Tuple
from .config import LetoBLRMConfig


def compute_baseline_score(row: Dict[str, Any]) -> float:
    """
    Compute a baseline score from features.

    This is a toy implementation for v0.1.
    In production, this would be your actual BLRM model.

    Args:
        row: Dictionary with features

    Returns:
        Computed score
    """
    # Extract numeric features
    features = []
    for key, value in row.items():
        if key not in ["id", "target"] and isinstance(value, (int, float)):
            features.append(value)

    if not features:
        return 0.0

    # Simple baseline: weighted average
    score = sum(features) / len(features)

    # Add some randomness for scenario variation
    score += random.uniform(-5, 5)

    return max(0.0, score)


def run_single_scenario(
    data: List[Dict[str, Any]],
    scenario_id: int,
    seed: int,
    cfg: LetoBLRMConfig
) -> Dict[str, Any]:
    """
    Run a single BLRM scenario.

    Args:
        data: Input data rows
        scenario_id: Scenario identifier
        seed: Random seed for reproducibility
        cfg: Configuration object

    Returns:
        Dictionary with scenario results
    """
    start_time = time.time()

    # Set random seed for reproducibility
    random.seed(seed + scenario_id)

    # Compute scores for all rows
    scores = []
    hits = 0
    total_rows = len(data)

    for row in data:
        score = compute_baseline_score(row)
        scores.append(score)

        # Count "hits" (scores above threshold)
        if score > 50:  # Arbitrary threshold for demo
            hits += 1

    # Aggregate metrics
    avg_score = sum(scores) / len(scores) if scores else 0.0
    max_score = max(scores) if scores else 0.0
    min_score = min(scores) if scores else 0.0
    p_hit = hits / total_rows if total_rows > 0 else 0.0

    runtime_sec = time.time() - start_time

    result = {
        "scenario_id": scenario_id,
        "seed": seed + scenario_id,
        "num_rows": total_rows,
        "avg_score": round(avg_score, 4),
        "max_score": round(max_score, 4),
        "min_score": round(min_score, 4),
        "p_hit": round(p_hit, 4),
        "num_hits": hits,
        "runtime_sec": round(runtime_sec, 4),
    }

    return result


def run_scenarios(
    data: List[Dict[str, Any]],
    cfg: LetoBLRMConfig
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Run multiple BLRM scenarios.

    Args:
        data: Input data rows
        cfg: Configuration object

    Returns:
        Tuple of (summary, runs) where:
        - summary: Aggregated statistics across all scenarios
        - runs: List of per-scenario results
    """
    print(f"Running {cfg.n_scenarios} scenarios...")
    start_time = time.time()

    runs = []
    for i in range(cfg.n_scenarios):
        print(f"  Scenario {i+1}/{cfg.n_scenarios}...")
        result = run_single_scenario(data, i, cfg.seed, cfg)
        runs.append(result)

    total_runtime = time.time() - start_time

    # Compute summary statistics
    avg_scores = [r["avg_score"] for r in runs]
    p_hits = [r["p_hit"] for r in runs]
    runtimes = [r["runtime_sec"] for r in runs]

    summary = {
        "config_name": cfg.name,
        "num_rows": len(data),
        "num_scenarios": cfg.n_scenarios,
        "seed": cfg.seed,
        # Aggregated metrics across scenarios
        "mean_avg_score": round(sum(avg_scores) / len(avg_scores), 4) if avg_scores else 0.0,
        "mean_p_hit": round(sum(p_hits) / len(p_hits), 4) if p_hits else 0.0,
        "total_runtime_sec": round(total_runtime, 4),
        "avg_scenario_runtime_sec": round(sum(runtimes) / len(runtimes), 4) if runtimes else 0.0,
        "max_scenario_runtime_sec": round(max(runtimes), 4) if runtimes else 0.0,
        # Best scenario (highest avg score)
        "best_scenario_id": max(runs, key=lambda x: x["avg_score"])["scenario_id"] if runs else None,
        "best_avg_score": max(avg_scores) if avg_scores else 0.0,
    }

    print(f"Completed {cfg.n_scenarios} scenarios in {total_runtime:.2f}s")
    print(f"  Mean avg score: {summary['mean_avg_score']:.4f}")
    print(f"  Mean p(hit): {summary['mean_p_hit']:.4f}")

    return summary, runs
