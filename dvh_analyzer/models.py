"""
dvh-analyzer: Radiation Oncology Dose-Volume Histogram (DVH) Models & QUANTEC Constraints.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class ConstraintResult(str, Enum):
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"


@dataclass
class DVHCurve:
    structure_name: str
    is_target: bool
    total_volume_cc: float
    doses_gy: List[float]       # Dose points (Gy)
    volumes_percent: List[float] # Cumulative volume percentages [0.0 - 100.0]
    color_hex: str = "#1f77b4"


@dataclass
class ClinicalConstraint:
    structure_name: str
    metric_type: str  # "V_dose" (e.g. V20Gy <= 30%), "D_volume" (e.g. Dmax <= 50Gy, D0.03cc <= 45Gy), "D_mean"
    parameter_value: float  # e.g., 20.0 for V20Gy
    operator: str  # "<=", ">=", "<", ">"
    limit_value: float  # e.g., 30.0 for 30%
    unit: str  # "%", "Gy", "cc"
    protocol_source: str = "QUANTEC"
    clinical_endpoint: str = "Pneumonitis / Toxicity"

    def evaluate(self, computed_val: float) -> ConstraintResult:
        if self.operator == "<=":
            return ConstraintResult.PASS if computed_val <= self.limit_value else ConstraintResult.FAIL
        elif self.operator == "<":
            return ConstraintResult.PASS if computed_val < self.limit_value else ConstraintResult.FAIL
        elif self.operator == ">=":
            return ConstraintResult.PASS if computed_val >= self.limit_value else ConstraintResult.FAIL
        elif self.operator == ">":
            return ConstraintResult.PASS if computed_val > self.limit_value else ConstraintResult.FAIL
        return ConstraintResult.PASS


# Standard QUANTEC / RTOG Clinical Organ-at-Risk (OAR) Dose Constraints Catalog
STANDARD_QUANTEC_CONSTRAINTS = [
    # Spinal Cord
    ClinicalConstraint("Spinal Cord", "D_max", 0.0, "<=", 45.0, "Gy", "QUANTEC", "Myelopathy (< 0.2%)"),
    ClinicalConstraint("Spinal Cord", "D_max", 0.0, "<=", 50.0, "Gy", "RTOG", "Myelopathy limit"),
    # Lungs (Total - GTV)
    ClinicalConstraint("Lungs", "V_dose", 20.0, "<=", 30.0, "%", "QUANTEC", "Radiation pneumonitis (< 20%)"),
    ClinicalConstraint("Lungs", "V_dose", 5.0, "<=", 60.0, "%", "QUANTEC", "Radiation pneumonitis"),
    ClinicalConstraint("Lungs", "D_mean", 0.0, "<=", 20.0, "Gy", "QUANTEC", "Symptomatic pneumonitis"),
    # Heart
    ClinicalConstraint("Heart", "V_dose", 25.0, "<=", 10.0, "%", "QUANTEC", "1-year cardiac mortality (< 1%)"),
    ClinicalConstraint("Heart", "D_mean", 0.0, "<=", 15.0, "Gy", "QUANTEC", "Pericarditis / Cardiac events"),
    # Rectum
    ClinicalConstraint("Rectum", "V_dose", 50.0, "<=", 50.0, "%", "QUANTEC", "Grade >= 2 late rectal toxicity (< 15%)"),
    ClinicalConstraint("Rectum", "V_dose", 70.0, "<=", 20.0, "%", "QUANTEC", "Grade >= 3 late rectal toxicity"),
    # Bladder
    ClinicalConstraint("Bladder", "V_dose", 65.0, "<=", 50.0, "%", "QUANTEC", "Grade >= 3 late bladder toxicity"),
    ClinicalConstraint("Bladder", "V_dose", 70.0, "<=", 35.0, "%", "QUANTEC", "Late cystitis / hematuria"),
    # Esophagus
    ClinicalConstraint("Esophagus", "D_mean", 0.0, "<=", 34.0, "Gy", "QUANTEC", "Grade >= 2 esophagitis"),
    ClinicalConstraint("Esophagus", "V_dose", 35.0, "<=", 50.0, "%", "QUANTEC", "Acute esophagitis"),
]


@dataclass
class PlanAssessment:
    plan_name: str
    curves: Dict[str, DVHCurve]  # structure_name -> DVHCurve
    prescribed_dose_gy: float = 60.0
