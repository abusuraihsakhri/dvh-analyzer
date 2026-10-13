"""Validate and parse cumulative dose-volume histograms from tabular CSV/TSV.

This parser accepts explicitly labelled Dose_Gy or Dose_cGy columns; it does
not claim to support proprietary, non-tabular treatment-planning exports.
"""
import csv
import io
import math
import re
from pathlib import Path
from typing import Dict, List, Union

from .models import DVHCurve, PlanAssessment

PALETTE = [
    "#e41a1c", "#377eb8", "#4daf4a", "#984ea3", "#ff7f00",
    "#b8860b", "#a65628", "#f781bf", "#999999",
]


def parse_dvh_csv(
    file_or_path: Union[str, Path, io.StringIO],
    plan_name: str = "Radiotherapy Treatment Plan",
    prescribed_dose_gy: float = 60.0,
) -> PlanAssessment:
    """Parse a cumulative DVH table with increasing dose and decreasing volume.

    Requires at least two data rows, a zero-dose origin, and finite numeric
    volumes in [0, 100]. Invalid rows are rejected rather than silently skipped.
    """
    if not math.isfinite(prescribed_dose_gy) or prescribed_dose_gy <= 0:
        raise ValueError("Prescribed dose must be a positive finite value.")

    if isinstance(file_or_path, Path):
        content = file_or_path.read_text(encoding="utf-8-sig")
    elif isinstance(file_or_path, io.StringIO):
        content = file_or_path.getvalue()
    elif isinstance(file_or_path, str):
        if "\n" in file_or_path or "\r" in file_or_path or re.match(
            r"^\s*Dose_(?:c?Gy)\s*[,;\t]", file_or_path, re.IGNORECASE
        ):
            content = file_or_path
        else:
            content = Path(file_or_path).read_text(encoding="utf-8-sig")
    else:
        raise TypeError("Expected a file path or text containing a DVH table.")

    lines = [line for line in content.lstrip("\ufeff").splitlines() if line.strip()]
    if not lines:
        raise ValueError("DVH input is empty.")

    header_idx = next(
        (i for i, line in enumerate(lines[:20]) if re.match(
            r'^\s*"?Dose_(?:c?Gy)"?\s*[,;\t]', line, re.IGNORECASE
        )),
        None,
    )
    if header_idx is None:
        raise ValueError("Expected a Dose_Gy or Dose_cGy first column.")

    header_line = lines[header_idx]
    delimiter = "\t" if "\t" in header_line else ";" if ";" in header_line else ","
    rows = list(csv.reader(lines[header_idx:], delimiter=delimiter, strict=True))
    header = [h.strip() for h in rows[0]]
    if len(header) < 2 or any(not name for name in header[1:]):
        raise ValueError("At least one named structure column is required.")
    if header[0].lower() not in {"dose_gy", "dose_cgy"}:
        raise ValueError("First column must be Dose_Gy or Dose_cGy.")
    if len(rows) < 3:
        raise ValueError("At least two dose-volume records are required.")

    names = [re.sub(r"\[.*?\]|\(.*?\)", "", s).strip() for s in header[1:]]
    if not all(names) or len({s.casefold() for s in names}) != len(names):
        raise ValueError("Structure names must be distinct and nonempty.")

    doses: List[float] = []
    volumes: Dict[str, List[float]] = {name: [] for name in names}
    factor = 0.01 if header[0].lower() == "dose_cgy" else 1.0
    for line_number, row in enumerate(rows[1:], start=header_idx + 2):
        if not any(cell.strip() for cell in row):
            continue
        if len(row) != len(header):
            raise ValueError(f"Row {line_number}: expected {len(header)} columns.")
        try:
            values = [float(cell.strip()) for cell in row]
        except ValueError as exc:
            raise ValueError(f"Row {line_number}: nonnumeric dose or volume.") from exc
        dose = values[0] * factor
        if not math.isfinite(dose) or dose < 0 or (doses and dose <= doses[-1]):
            raise ValueError(f"Row {line_number}: doses must be finite and strictly increasing.")
        if any(not math.isfinite(v) or v < 0 or v > 100 for v in values[1:]):
            raise ValueError(f"Row {line_number}: volume percentages must be finite and within 0–100.")
        for name, value in zip(names, values[1:]):
            if volumes[name] and value > volumes[name][-1] + 1e-9:
                raise ValueError(f"Row {line_number}: {name} cumulative volume increases with dose.")
            volumes[name].append(value)
        doses.append(dose)

    if len(doses) < 2 or not math.isclose(doses[0], 0.0, abs_tol=1e-8):
        raise ValueError("DVH must contain at least two rows and start at 0 Gy.")

    curves = {}
    for index, name in enumerate(names):
        is_target = any(word in name.casefold() for word in ("ptv", "ctv", "gtv", "target", "tumor"))
        curves[name] = DVHCurve(
            structure_name=name, is_target=is_target, total_volume_cc=0.0,
            doses_gy=doses.copy(), volumes_percent=volumes[name],
            color_hex=PALETTE[index % len(PALETTE)],
        )
    return PlanAssessment(plan_name=plan_name, curves=curves, prescribed_dose_gy=prescribed_dose_gy)
