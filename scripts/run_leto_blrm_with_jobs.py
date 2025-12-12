#!/usr/bin/env python
"""
Leto BLRM CLI - Run BLRM scenarios with Forge Jobs integration.

Usage:
    python -m scripts.run_leto_blrm_with_jobs --job-id JOB_ID [OPTIONS]

Example:
    python -m scripts.run_leto_blrm_with_jobs \
        --job-id leto-blrm-20231210-001 \
        --sphere orunmila \
        --config leto_blrm/configs/default.json \
        --output-dir data/leto_blrm_runs
"""

import argparse
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.job_store import job_store
from leto_blrm.runner import run_leto_blrm_job


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run Leto BLRM scenarios with Forge Jobs integration"
    )

    parser.add_argument(
        "--job-id",
        type=str,
        required=False,
        help="Job ID for status tracking (creates job if not exists)"
    )

    parser.add_argument(
        "--sphere",
        type=str,
        default="orunmila",
        choices=["forge", "orunmila"],
        help="Job sphere (default: orunmila)"
    )

    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to config file (JSON or YAML). If not provided, uses defaults."
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/leto_blrm_runs",
        help="Output directory for results (default: data/leto_blrm_runs)"
    )

    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)"
    )

    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()

    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    logger = logging.getLogger(__name__)

    # If job_id provided, update job status
    if args.job_id:
        try:
            # Check if job exists, if not create it
            try:
                job = job_store.get_job(args.job_id)
                logger.info(f"Found existing job: {args.job_id}")
            except KeyError:
                logger.info(f"Creating new job: {args.job_id}")
                job = job_store.create_job(
                    job_id=args.job_id,
                    name="leto_blrm_v1",
                    status="pending",
                    sphere=args.sphere
                )

            # Mark job as running
            logger.info(f"Marking job {args.job_id} as running")
            job_store.mark_running(args.job_id)

        except Exception as e:
            logger.error(f"Failed to initialize job status: {e}")
            if args.job_id:
                # Don't fail the whole job if status update fails
                pass

    try:
        # Run the BLRM job
        summary = run_leto_blrm_job(
            config_path=args.config,
            output_dir=args.output_dir,
            logger=logger
        )

        # Mark job as succeeded
        if args.job_id:
            logger.info(f"Marking job {args.job_id} as succeeded")
            job_store.mark_succeeded(args.job_id)

        # Print summary to stdout for scripts
        logger.info("\n" + "=" * 60)
        logger.info("SUMMARY")
        logger.info("=" * 60)
        for key, value in summary.items():
            if key not in ["config", "output_dir"]:  # Skip verbose fields
                logger.info(f"  {key}: {value}")
        logger.info("=" * 60)

        return 0

    except Exception as e:
        logger.error(f"Job failed: {e}", exc_info=True)

        # Mark job as failed
        if args.job_id:
            error_msg = str(e)[:500]  # Truncate long errors
            logger.info(f"Marking job {args.job_id} as failed")
            job_store.mark_failed(args.job_id, error_msg)

        return 1


if __name__ == "__main__":
    sys.exit(main())
