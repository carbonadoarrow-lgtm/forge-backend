"""
Basic tests for Leto BLRM functionality.
"""

import json
import sys
from pathlib import Path

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from leto_blrm.runner import run_leto_blrm_job
from leto_blrm.config import LetoBLRMConfig, load_config
from leto_blrm.io import ensure_output_dir, load_input_data


def test_config_defaults():
    """Test that default config loads correctly."""
    cfg = load_config(None)
    assert cfg.name == "leto_blrm_v0_1"
    assert cfg.n_scenarios == 5
    assert cfg.seed == 42
    print("✓ Config defaults test passed")


def test_ensure_output_dir():
    """Test output directory creation."""
    test_dir = "data/test_leto_output"
    path = ensure_output_dir(test_dir)
    assert path.exists()
    assert path.is_dir()
    print(f"✓ Output dir test passed: {path}")


def test_load_synthetic_data():
    """Test synthetic data generation."""
    # Use non-existent path to trigger synthetic generation
    data = load_input_data("data/nonexistent.csv")
    assert len(data) >= 100
    assert len(data) <= 300
    assert "feature_1" in data[0]
    assert "target" in data[0]
    print(f"✓ Synthetic data test passed: {len(data)} rows")


def test_run_leto_blrm_job():
    """Test full BLRM job execution."""
    output_dir = "data/leto_blrm_runs_test"

    # Run with defaults (should generate synthetic data)
    summary = run_leto_blrm_job(
        config_path=None,
        output_dir=output_dir
    )

    # Check summary structure
    assert "num_rows" in summary
    assert "num_scenarios" in summary
    assert "mean_avg_score" in summary
    assert "mean_p_hit" in summary
    assert "total_runtime_sec" in summary

    # Check that scenarios were run
    assert summary["num_scenarios"] == 5  # default
    assert summary["num_rows"] > 0

    # Check output files exist
    output_path = Path(output_dir)
    assert (output_path / "summary.json").exists()
    assert (output_path / "runs.csv").exists()
    assert (output_path / "metadata.json").exists()

    # Verify summary.json content
    with open(output_path / "summary.json", "r") as f:
        saved_summary = json.load(f)
    assert saved_summary["num_scenarios"] == 5
    assert "mean_avg_score" in saved_summary

    print(f"✓ Full job test passed")
    print(f"  - {summary['num_scenarios']} scenarios")
    print(f"  - {summary['num_rows']} rows")
    print(f"  - Mean avg score: {summary['mean_avg_score']:.4f}")
    print(f"  - Mean p(hit): {summary['mean_p_hit']:.4f}")
    print(f"  - Runtime: {summary['total_runtime_sec']:.2f}s")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Running Leto BLRM Basic Tests")
    print("=" * 60)

    try:
        test_config_defaults()
        test_ensure_output_dir()
        test_load_synthetic_data()
        test_run_leto_blrm_job()

        print("=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)
        return 0

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
