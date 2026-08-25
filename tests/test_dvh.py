import io
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from dvh_analyzer.models import DVHCurve, PlanAssessment, ClinicalConstraint, ConstraintResult
from dvh_analyzer.metrics import (
    get_volume_at_dose,
    get_dose_at_volume,
    compute_d_mean,
    compute_d_max,
    compute_homogeneity_index,
    compute_geud,
)
from dvh_analyzer.parser import parse_dvh_csv
from dvh_analyzer.evaluator import evaluate_plan_constraints
from dvh_analyzer.renderer_svg import render_dvh_svg
from dvh_analyzer.cli import main


def test_dvh_metrics_interpolation():
    curve = DVHCurve(
        structure_name="Test Structure",
        is_target=False,
        total_volume_cc=100.0,
        doses_gy=[0.0, 10.0, 20.0, 30.0, 40.0],
        volumes_percent=[100.0, 80.0, 50.0, 20.0, 0.0],
    )
    # V at 15 Gy -> halfway between 10 (80%) and 20 (50%) -> 65%
    assert pytest.approx(get_volume_at_dose(curve, 15.0), 0.1) == 65.0
    # D at 50% vol -> 20 Gy
    assert pytest.approx(get_dose_at_volume(curve, 50.0), 0.1) == 20.0
    # D mean
    assert compute_d_mean(curve) > 0


def test_homogeneity_index():
    curve = DVHCurve(
        structure_name="PTV",
        is_target=True,
        total_volume_cc=250.0,
        doses_gy=[0.0, 50.0, 58.0, 60.0, 62.0],
        volumes_percent=[100.0, 100.0, 98.0, 50.0, 2.0],
    )
    hi = compute_homogeneity_index(curve)
    assert hi >= 0.0


def test_geud():
    curve = DVHCurve(
        structure_name="Lung",
        is_target=False,
        total_volume_cc=3000.0,
        doses_gy=[0.0, 10.0, 20.0, 30.0],
        volumes_percent=[100.0, 50.0, 20.0, 0.0],
    )
    geud_parallel = compute_geud(curve, a_parameter=1.0)
    assert geud_parallel > 0.0


def test_quantec_evaluator(tmp_path):
    csv_file = tmp_path / "dvh.csv"
    csv_file.write_text(
        "Dose_Gy,PTV,Spinal_Cord,Lungs\n"
        "0.0,100,100,100\n"
        "20.0,100,40,25\n"
        "40.0,100,10,5\n"
        "60.0,95,0,0\n",
        encoding="utf-8",
    )
    plan = parse_dvh_csv(str(csv_file), prescribed_dose_gy=60.0)
    assert "Spinal_Cord" in plan.curves or "Spinal Cord" in [c.structure_name for c in plan.curves.values()]
    evals = evaluate_plan_constraints(plan)
    assert len(evals) > 0


def test_cli_execution(tmp_path):
    csv_file = tmp_path / "dvh_test.csv"
    csv_file.write_text(
        "Dose_Gy,PTV,Spinal_Cord,Lungs\n"
        "0.0,100,100,100\n"
        "20.0,100,40,25\n"
        "40.0,100,10,5\n"
        "60.0,95,0,0\n",
        encoding="utf-8",
    )
    out_svg = str(tmp_path / "out.svg")
    assert main(["report", "-i", str(csv_file)]) == 0
    assert main(["plot", "-i", str(csv_file), "-o", out_svg]) == 0
    assert (tmp_path / "out.svg").exists()
