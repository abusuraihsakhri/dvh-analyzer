"""
Compliance Evaluation Engine against QUANTEC / RTOG Clinical Organ-at-Risk Constraints.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from .models import ClinicalConstraint, ConstraintResult, DVHCurve, PlanAssessment, STANDARD_QUANTEC_CONSTRAINTS
from .metrics import compute_d_max, compute_d_mean, get_volume_at_dose, get_dose_at_volume


@dataclass
class ConstraintEvaluation:
    structure_name: str
    metric_label: str
    computed_value: float
    limit_value: float
    unit: str
    result: ConstraintResult
    protocol: str
    endpoint: str


def evaluate_plan_constraints(
    plan: PlanAssessment,
    custom_constraints: Optional[List[ClinicalConstraint]] = None,
) -> List[ConstraintEvaluation]:
    """
    Evaluates all matched structures in the plan against standard QUANTEC or custom constraints.
    """
    constraints_to_check = custom_constraints or STANDARD_QUANTEC_CONSTRAINTS
    evaluations: List[ConstraintEvaluation] = []

    for constraint in constraints_to_check:
        # Match structure by case-insensitive substring
        target_curve = None
        for s_name, curve in plan.curves.items():
            if constraint.structure_name.lower() in s_name.lower() or s_name.lower() in constraint.structure_name.lower():
                target_curve = curve
                break

        if target_curve is None:
            continue

        computed_val = 0.0
        label = ""

        if constraint.metric_type == "D_max":
            computed_val = compute_d_max(target_curve)
            label = "D_max"
        elif constraint.metric_type == "D_mean":
            computed_val = compute_d_mean(target_curve)
            label = "D_mean"
        elif constraint.metric_type == "V_dose":
            computed_val = get_volume_at_dose(target_curve, constraint.parameter_value)
            label = f"V{constraint.parameter_value:.0f}Gy"
        elif constraint.metric_type == "D_volume":
            computed_val = get_dose_at_volume(target_curve, constraint.parameter_value)
            label = f"D{constraint.parameter_value:.0f}%"

        result = constraint.evaluate(computed_val)

        evaluations.append(
            ConstraintEvaluation(
                structure_name=target_curve.structure_name,
                metric_label=label,
                computed_value=computed_val,
                limit_value=constraint.limit_value,
                unit=constraint.unit,
                result=result,
                protocol=constraint.protocol_source,
                endpoint=constraint.clinical_endpoint,
            )
        )

    return evaluations
