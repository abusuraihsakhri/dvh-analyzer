"""
dvh-analyzer: Radiation Oncology Dose-Volume Histogram (DVH) & QUANTEC Constraint Compliance Engine.
"""

from .models import DVHCurve, ClinicalConstraint, ConstraintResult, PlanAssessment, STANDARD_QUANTEC_CONSTRAINTS
from .metrics import (
    get_volume_at_dose,
    get_dose_at_volume,
    compute_d_mean,
    compute_d_max,
    compute_d_min,
    compute_homogeneity_index,
    compute_geud,
)
from .parser import parse_dvh_csv
from .evaluator import evaluate_plan_constraints, ConstraintEvaluation
from .renderer_svg import render_dvh_svg

__version__ = "1.0.0"
__all__ = [
    "DVHCurve",
    "ClinicalConstraint",
    "ConstraintResult",
    "PlanAssessment",
    "STANDARD_QUANTEC_CONSTRAINTS",
    "get_volume_at_dose",
    "get_dose_at_volume",
    "compute_d_mean",
    "compute_d_max",
    "compute_d_min",
    "compute_homogeneity_index",
    "compute_geud",
    "parse_dvh_csv",
    "evaluate_plan_constraints",
    "ConstraintEvaluation",
    "render_dvh_svg",
]
