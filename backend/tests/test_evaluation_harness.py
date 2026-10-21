"""
Unit tests for ScholarSwarm Reproducible Evaluation Harness (Feature F20).
Verifies execution, output schema, metrics keys, and bounded empirical metrics.
"""

import os
import pytest
import tempfile
import json
from scripts.evaluate_harness import run_evaluation_benchmark, format_markdown_report, BENCHMARK_CASES


def test_benchmark_cases_dataset_integrity():
    """Verify that exactly 10 documented benchmark test cases exist with required fields."""
    assert len(BENCHMARK_CASES) == 10
    required_keys = {"id", "name", "profile", "raw_opportunity", "ground_truth"}
    for case in BENCHMARK_CASES:
        assert required_keys.issubset(set(case.keys()))
        assert "expected_eligibility" in case["ground_truth"]
        assert "is_admissible" in case["ground_truth"]
        assert "has_official_source" in case["ground_truth"]


@pytest.mark.asyncio
async def test_evaluation_harness_execution():
    """
    Test end-to-end benchmark run in deterministic mock mode.
    Asserts schema completeness, required metrics keys, and expected bounds.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_output = os.path.join(tmp_dir, "test_experiment_results.json")
        results = await run_evaluation_benchmark(mock_mode=True, output_path=tmp_output)

        # 1. Top-level schema assertions
        assert "timestamp" in results
        assert "mode" in results
        assert results["mode"] == "deterministic_mock"
        assert results["total_benchmark_cases"] == 10
        assert "single_pass" in results
        assert "self_correcting" in results
        assert "delta" in results
        assert "case_details" in results
        assert len(results["case_details"]) == 10

        # 2. Metrics keys assertions (supporting both standard and alias keys)
        for key in ["official_coverage", "eligibility_accuracy", "false_positive_rate",
                    "unsupported_claims_caught", "fault_recovery", "mean_latency_seconds", "mean_rounds"]:
            assert key in results["single_pass"]
            assert key in results["self_correcting"]

        # 3. Expected empirical bounds
        # Self-correcting pipeline must eliminate false-positive admissions
        assert results["self_correcting"]["false_positive_rate"] == 0.0
        assert results["self_correcting"]["false_positive_pass_rate"] == 0.0

        # Self-correcting pipeline must improve official source coverage over single-pass
        assert results["self_correcting"]["official_coverage"] >= results["single_pass"]["official_coverage"]
        assert results["self_correcting"]["official_source_coverage"] >= results["single_pass"]["official_source_coverage"]

        # Self-correcting pipeline must have >= eligibility accuracy
        assert results["self_correcting"]["eligibility_accuracy"] >= results["single_pass"]["eligibility_accuracy"]

        # Self-correcting pipeline must catch 100% of unsupported funding claims and injected faults
        assert results["self_correcting"]["unsupported_claims_caught"] == 100.0
        assert results["self_correcting"]["fault_recovery"] == 100.0

        # Latency and rounds bounds
        assert results["single_pass"]["mean_latency_seconds"] >= 0
        assert results["self_correcting"]["mean_latency_seconds"] >= 0
        assert results["single_pass"]["mean_rounds"] == 1.0
        assert results["self_correcting"]["mean_rounds"] >= 1.0

        # 4. Artifact file persistence assertion
        assert os.path.exists(tmp_output)
        with open(tmp_output, "r", encoding="utf-8") as f:
            loaded_json = json.load(f)
        assert loaded_json["total_benchmark_cases"] == 10
        assert loaded_json["self_correcting"]["false_positive_rate"] == 0.0


def test_format_markdown_report():
    """Verify that markdown report formatting produces a complete, structured document."""
    mock_results = {
        "timestamp": "2026-10-20T23:30:00Z",
        "mode": "deterministic_mock",
        "total_benchmark_cases": 10,
        "single_pass": {
            "official_source_coverage": 70.0,
            "eligibility_accuracy": 80.0,
            "false_positive_pass_rate": 100.0,
            "unsupported_claims_caught": 0.0,
            "unsupported_claims_caught_count": "0/1",
            "fault_recovery": 0.0,
            "mean_latency_seconds": 0.0025,
            "mean_rounds": 1.0
        },
        "self_correcting": {
            "official_source_coverage": 100.0,
            "eligibility_accuracy": 100.0,
            "false_positive_pass_rate": 0.0,
            "unsupported_claims_caught": 100.0,
            "unsupported_claims_caught_count": "1/1",
            "fault_recovery": 100.0,
            "mean_latency_seconds": 0.0045,
            "mean_rounds": 1.7
        },
        "delta": {
            "official_source_coverage": "+30.0%",
            "eligibility_accuracy": "+20.0%",
            "false_positive_pass_rate": "-100.0% (Eliminated)",
            "unsupported_claims_caught": "+100.0%",
            "fault_recovery": "+100.0%",
            "mean_latency_seconds": "+0.0020s",
            "additional_rounds": "+0.7 rounds"
        }
    }

    md = format_markdown_report(mock_results)
    assert "# Experiment: Self-Correcting Scholarship Research" in md
    assert "Empirical Measurements & Results" in md
    assert "CASE-01: Toronto MScAC / Vector AI" in md
    assert "CASE-10: Non-Standard CGPA Scale / Ambiguous Conversion" in md
    assert "Single Pass (Baseline)" in md
    assert "ScholarSwarm" in md
    assert "0.0%" in md
