"""
Parser for Radiation Treatment Plan Dose-Volume Histogram (DVH) export files.
Supports Eclipse, RayStation, Monaco, and standard CSV/TSV table formats.
"""

import csv
import io
import re
from typing import Dict, List, Optional, Tuple, Union
from .models import DVHCurve, PlanAssessment


PALETTE = [
    "#e41a1c",  # PTV - Red
    "#377eb8",  # Spinal Cord - Blue
    "#4daf4a",  # Lungs - Green
    "#984ea3",  # Heart - Purple
    "#ff7f00",  # Rectum - Orange
    "#ffff33",  # Bladder - Yellow
    "#a65628",  # Esophagus - Brown
    "#f781bf",  # Femoral Heads - Pink
    "#999999",  # Gray
]


def parse_dvh_csv(
    file_or_path: Union[str, io.StringIO],
    plan_name: str = "Radiotherapy Treatment Plan",
    prescribed_dose_gy: float = 60.0,
) -> PlanAssessment:
    """
    Parse a DVH tabular CSV or text export.
    Expects header: Dose_Gy (or Dose_cGy), Structure1, Structure2, ...
    """
    if isinstance(file_or_path, str) and "\n" not in file_or_path and not file_or_path.startswith("Dose"):
        with open(file_or_path, mode="r", encoding="utf-8-sig") as f:
            content = f.read()
    elif isinstance(file_or_path, io.StringIO):
        content = file_or_path.getvalue()
    else:
        content = str(file_or_path)

    lines = [line.strip() for line in content.splitlines() if line.strip()]
    if not lines:
        raise ValueError("DVH input file is empty.")

    # Find the header line (starts with Dose or contains Dose)
    header_idx = 0
    for idx, line in enumerate(lines[:20]):
        if "dose" in line.lower():
            header_idx = idx
            break

    reader = csv.reader(io.StringIO("\n".join(lines[header_idx:])))
    rows = [r for r in reader if any(cell.strip() for cell in r)]
    if len(rows) < 2:
        raise ValueError("DVH table has insufficient data rows.")

    header = [h.strip() for h in rows[0]]
    dose_col_name = header[0].lower()
    is_cgy = "cgy" in dose_col_name

    structure_names = header[1:]
    if not structure_names:
        raise ValueError("No structure columns found in DVH header.")

    doses: List[float] = []
    struct_vols: Dict[str, List[float]] = {s: [] for s in structure_names}

    for row in rows[1:]:
        if not row or len(row) < len(header):
            continue
        try:
            raw_dose = float(row[0])
            dose_gy = raw_dose / 100.0 if is_cgy else raw_dose
            doses.append(dose_gy)

            for idx, s_name in enumerate(structure_names, start=1):
                vol_pct = float(row[idx])
                # Ensure clamped in [0, 100]
                struct_vols[s_name].append(max(0.0, min(100.0, vol_pct)))
        except (ValueError, IndexError):
            continue

    if not doses:
        raise ValueError("Could not parse numeric dose-volume records.")

    # Construct DVHCurves
    curves: Dict[str, DVHCurve] = {}
    for idx, s_name in enumerate(structure_names):
        clean_name = re.sub(r"\[.*?\]|\(.*?\)", "", s_name).strip()
        is_target = any(term in clean_name.lower() for term in ["ptv", "ctv", "gtv", "target", "tumor"])
        color = PALETTE[idx % len(PALETTE)]

        curves[clean_name] = DVHCurve(
            structure_name=clean_name,
            is_target=is_target,
            total_volume_cc=100.0,
            doses_gy=list(doses),
            volumes_percent=struct_vols[s_name],
            color_hex=color,
        )

    return PlanAssessment(
        plan_name=plan_name,
        curves=curves,
        prescribed_dose_gy=prescribed_dose_gy,
    )
