import io
import math

import pytest

from agents.base import AuditTrail
from dvh_analyzer.parser import parse_dvh_csv
from dvh_analyzer.metrics import get_volume_at_dose, compute_d_mean
from dvh_analyzer.models import ClinicalConstraint
from dvh_analyzer.evaluator import evaluate_plan_constraints


def test_cgy_input_and_endpoint_interpolation():
    plan = parse_dvh_csv("Dose_cGy,Spinal_Cord\n0,100\n1000,60\n2000,0\n")
    curve = plan.curves["Spinal_Cord"]
    assert curve.doses_gy == [0, 10, 20]
    assert get_volume_at_dose(curve, 20) == 0
    assert get_volume_at_dose(curve, 10) == 60
    assert compute_d_mean(curve) == pytest.approx(11.0)
    assert len(evaluate_plan_constraints(plan)) == 2


@pytest.mark.parametrize("input_text", [
    "Dose_Gy,Lung\n0,100\n10,abc\n20,0\n",
    "Dose_Gy,Lung\n0,100\n10,130\n20,0\n",
    "Dose_Gy,Lung\n0,100\n10,90\n20,95\n",
    "Dose_Gy,Lung\n0,100\n10,90\n9,0\n",
    "Dose_Gy,Lung\n0,100\n10,nan\n20,0\n",
    "Dose_Gy,Lung\n0,100\n10,50,extra\n20,0\n",
    "Dose_Gy,Lung,Lung\n0,100,100\n10,0,0\n",
    "Dose_Gy,Lung\n10,100\n20,0\n",
    "Dose_Gy,Lung\n0,100\n",
]):
    def test_reject_invalid_dvh(input_text):
        with pytest.raises(ValueError):
            parse_dvh_csv(io.StringIO(input_text))


def test_custom_empty_constraints_do_not_fall_back():
    plan = parse_dvh_csv("Dose_Gy,Lungs\n0,100\n10,0\n")
    assert evaluate_plan_constraints(plan, []) == []


def test_unknown_constraint_operator_is_not_a_pass():
    c = ClinicalConstraint("Lungs", "V_dose", 5, "!", 30, "%")
    with pytest.raises(ValueError):
        c.evaluate(12)


def test_hmac_audit_detects_tampering():
    trail = AuditTrail(secret_key="test-key-not-for-production")
    trail.log("test", "system", "evaluation", {"value": 10})
    assert trail.verify_integrity()
    exported = trail.get_trail()
    exported[0]["actor"] = "external"
    assert trail.verify_integrity()
    trail.logs[0]["actor"] = "attacker"
    assert not trail.verify_integrity()
