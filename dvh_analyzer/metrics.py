"""
Dosimetric metrics and radiobiology calculations for Dose-Volume Histograms (DVH).
"""

import math
from typing import List, Tuple
from .models import DVHCurve


def get_volume_at_dose(curve: DVHCurve, target_dose_gy: float) -> float:
    """
    Computes VxGy (% volume receiving >= target_dose_gy) using linear interpolation.
    """
    doses = curve.doses_gy
    vols = curve.volumes_percent
    if not doses or not vols:
        return 0.0

    if target_dose_gy <= doses[0]:
        return vols[0]
    if target_dose_gy >= doses[-1]:
        return 0.0

    for i in range(len(doses) - 1):
        d0, d1 = doses[i], doses[i + 1]
        v0, v1 = vols[i], vols[i + 1]
        if d0 <= target_dose_gy <= d1:
            if d1 == d0:
                return v0
            fraction = (target_dose_gy - d0) / (d1 - d0)
            return max(0.0, min(100.0, v0 + fraction * (v1 - v0)))
    return 0.0


def get_dose_at_volume(curve: DVHCurve, target_vol_pct: float) -> float:
    """
    Computes Dy% (minimum dose received by the hottest target_vol_pct % of volume) using inverse interpolation.
    """
    doses = curve.doses_gy
    vols = curve.volumes_percent
    if not doses or not vols:
        return 0.0

    if target_vol_pct >= vols[0]:
        return doses[0]
    if target_vol_pct <= vols[-1]:
        return doses[-1]

    # Volumes are monotonically decreasing
    for i in range(len(vols) - 1):
        v0, v1 = vols[i], vols[i + 1]
        d0, d1 = doses[i], doses[i + 1]
        if v1 <= target_vol_pct <= v0:
            if v1 == v0:
                return d0
            fraction = (v0 - target_vol_pct) / (v0 - v1)
            return d0 + fraction * (d1 - d0)
    return doses[-1]


def compute_d_mean(curve: DVHCurve) -> float:
    """
    Computes Mean Dose (Gy) by trapezoidal integration of the cumulative DVH curve.
    Integral of V(D) dD / V_total.
    """
    doses = curve.doses_gy
    vols = curve.volumes_percent
    if not doses or len(doses) < 2:
        return 0.0

    integral = 0.0
    for i in range(len(doses) - 1):
        d0, d1 = doses[i], doses[i + 1]
        v0, v1 = vols[i], vols[i + 1]
        step = d1 - d0
        avg_vol = (v0 + v1) / 2.0
        integral += avg_vol * step

    # Normalize by 100%
    return max(0.0, integral / 100.0)


def compute_d_max(curve: DVHCurve) -> float:
    """
    Returns maximum dose (D0.03cc or D_max Gy).
    """
    return get_dose_at_volume(curve, target_vol_pct=0.1)


def compute_d_min(curve: DVHCurve) -> float:
    """
    Returns minimum dose (D99% Gy).
    """
    return get_dose_at_volume(curve, target_vol_pct=99.0)


def compute_homogeneity_index(curve: DVHCurve) -> float:
    """
    ICRU 83 Homogeneity Index (HI) = (D2% - D98%) / D50%
    Lower is more homogeneous (ideal HI -> 0.0).
    """
    d2 = get_dose_at_volume(curve, 2.0)
    d98 = get_dose_at_volume(curve, 98.0)
    d50 = get_dose_at_volume(curve, 50.0)
    if d50 <= 0.001:
        return 0.0
    return (d2 - d98) / d50


def compute_geud(curve: DVHCurve, a_parameter: float) -> float:
    """
    Computes Generalized Equivalent Uniform Dose (gEUD) based on Niemierko's power law:
    gEUD = ( sum_i v_i * D_i^a )^(1/a)
    
    For a -> inf (serial organs like spinal cord, optic chiasm): gEUD -> D_max
    For a = 1 (parallel organs like lung, liver): gEUD = D_mean
    For tumors / PTV (a < 0, e.g. a = -10): sensitive to cold spots
    """
    doses = curve.doses_gy
    vols = curve.volumes_percent
    if not doses or len(doses) < 2:
        return 0.0

    if abs(a_parameter - 1.0) < 1e-4:
        return compute_d_mean(curve)

    differential_sum = 0.0
    for i in range(len(doses) - 1):
        d_mid = (doses[i] + doses[i + 1]) / 2.0
        v_diff = (vols[i] - vols[i + 1]) / 100.0  # fractional volume in this dose bin
        if v_diff > 0 and d_mid > 0:
            differential_sum += v_diff * (d_mid ** a_parameter)

    if differential_sum <= 0:
        return 0.0

    return differential_sum ** (1.0 / a_parameter)
