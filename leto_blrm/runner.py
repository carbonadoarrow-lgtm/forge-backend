"""
High-level orchestration for Leto BLRM jobs.
"""

import logging
from typing import Optional, Dict, Any
from pathlib import Path

from .config import load_config, LetoBLRMConfig
from .io import ensure_output_dir, load_input_data, save_results, save_input_sample
from .core import run_scenarios


def run_leto_blrm_job(
    config_path: Optional[str] = None,
    output_dir: str = "data/leto_blrm_runs",
    logger: Optional[logging.Logger] = None
) -> Dict[str, Any]:
    """
    Run a complete Leto BLRM job.

    This is the main entry point for executing BLRM scenarios.

    Args:
        config_path: Path to config file (optional)
        output_dir: Directory to save results
        logger: Logger instance (optional)

    Returns:
        Summary dictionary with aggregated metrics

    Raises:
        Exception: If job fails
    """
    if logger is None:
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

    logger.info("=" * 60)
    logger.info("Starting Leto BLRM v0.1 Job")
    logger.info("=" * 60)

    try:
        # Load configuration
        logger.info(f"Loading configuration from: {config_path or 'defaults'}")
        cfg = load_config(config_path)
        logger.info(f"Config: {cfg.to_dict()}")

        # Ensure output directory exists
        logger.info(f"Setting up output directory: {output_dir}")
        out_dir = ensure_output_dir(output_dir)

        # Load input data
        logger.info(f"Loading input data from: {cfg.input_path}")
        data = load_input_data(cfg.input_path)
        logger.info(f"Loaded {len(data)} rows")

        # Save input sample for debugging
        save_input_sample(out_dir, data)

        # Run scenarios
        logger.info(f"Running {cfg.n_scenarios} scenarios...")
        summary, runs = run_scenarios(data, cfg)

        # Save results
        logger.info("Saving results...")
        save_results(out_dir, summary, runs)

        # Add output directory to summary
        summary["output_dir"] = str(out_dir)
        summary["config"] = cfg.to_dict()

        logger.info("=" * 60)
        logger.info("Job completed successfully!")
        logger.info(f"  Total scenarios: {summary['num_scenarios']}")
        logger.info(f"  Mean avg score: {summary['mean_avg_score']:.4f}")
        logger.info(f"  Mean p(hit): {summary['mean_p_hit']:.4f}")
        logger.info(f"  Total runtime: {summary['total_runtime_sec']:.2f}s")
        logger.info(f"  Results saved to: {out_dir}")
        logger.info("=" * 60)

        return summary

    except Exception as e:
        logger.error(f"Job failed with error: {str(e)}", exc_info=True)
        raise
