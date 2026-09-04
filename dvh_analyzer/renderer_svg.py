"""
Vector SVG Rendering Engine for Dose-Volume Histograms (DVH).
Zero external dependencies, publication-ready vector charts.
"""

import html
from .models import PlanAssessment
from .metrics import compute_d_max, compute_d_mean, get_volume_at_dose


def _escape(text: str) -> str:
    return html.escape(str(text), quote=True)


def render_dvh_svg(
    plan: PlanAssessment,
    chart_width: int = 650,
    chart_height: int = 400,
    title: str = "Dose-Volume Histogram (DVH)",
) -> str:
    """
    Renders a multi-structure DVH overlay plot as an SVG.
    """
    margin_left = 70
    margin_right = 240  # Space for legend
    margin_top = 70
    margin_bottom = 60

    total_width = margin_left + chart_width + margin_right
    total_height = margin_top + chart_height + margin_bottom

    # Find max dose across all curves
    max_dose = 10.0
    for curve in plan.curves.values():
        if curve.doses_gy:
            max_dose = max(max_dose, max(curve.doses_gy))
    max_dose = max(plan.prescribed_dose_gy * 1.15, max_dose * 1.05)

    svg_parts = []
    svg_parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total_width} {total_height}" '
        f'width="{total_width}" height="{total_height}" style="background-color:#ffffff; font-family:-apple-system, BlinkMacSystemFont, \'Segoe UI\', Helvetica, Arial, sans-serif;">'
    )

    svg_parts.append("""
    <style>
      .title { font-size: 16px; font-weight: 700; fill: #1a1a1a; text-anchor: middle; }
      .axis-title { font-size: 13px; font-weight: 600; fill: #333333; text-anchor: middle; }
      .axis-tick { font-size: 11px; fill: #555555; }
      .grid-line { stroke: #eaeaea; stroke-width: 1; }
      .axis-line { stroke: #333333; stroke-width: 1.5; }
      .legend-title { font-size: 13px; font-weight: 700; fill: #222222; }
      .legend-text { font-size: 12px; font-weight: 500; fill: #333333; }
      .legend-sub { font-size: 10.5px; fill: #777777; }
      .rx-line { stroke: #d9534f; stroke-width: 1.5; stroke-dasharray: 4,4; }
      .curve-path { fill: none; stroke-width: 2.5; stroke-linecap: round; stroke-linejoin: round; }
    </style>
    """)

    # Title
    svg_parts.append(f'<text x="{total_width/2:.1f}" y="32" class="title">{_escape(title)} - {_escape(plan.plan_name)}</text>')

    # Grid Lines & X Axis Ticks (Dose in Gy)
    # Choose reasonable tick step (e.g., 10 Gy or 20 Gy)
    step_gy = 10.0 if max_dose <= 80.0 else 20.0
    curr_tick = 0.0
    while curr_tick <= max_dose:
        x_pos = margin_left + (curr_tick / max_dose) * chart_width
        svg_parts.append(
            f'<line x1="{x_pos:.1f}" y1="{margin_top}" x2="{x_pos:.1f}" y2="{margin_top + chart_height}" class="grid-line" />'
        )
        svg_parts.append(
            f'<text x="{x_pos:.1f}" y="{margin_top + chart_height + 20}" class="axis-tick" text-anchor="middle">{curr_tick:.0f}</text>'
        )
        curr_tick += step_gy

    # Grid Lines & Y Axis Ticks (Volume %)
    for vol_pct in range(0, 101, 20):
        y_pos = margin_top + chart_height - (vol_pct / 100.0) * chart_height
        svg_parts.append(
            f'<line x1="{margin_left}" y1="{y_pos:.1f}" x2="{margin_left + chart_width}" y2="{y_pos:.1f}" class="grid-line" />'
        )
        svg_parts.append(
            f'<text x="{margin_left - 12}" y="{y_pos + 4:.1f}" class="axis-tick" text-anchor="end">{vol_pct}%</text>'
        )

    # Prescription Line
    if plan.prescribed_dose_gy <= max_dose:
        rx_x = margin_left + (plan.prescribed_dose_gy / max_dose) * chart_width
        svg_parts.append(
            f'<line x1="{rx_x:.1f}" y1="{margin_top}" x2="{rx_x:.1f}" y2="{margin_top + chart_height}" class="rx-line" />'
        )
        svg_parts.append(
            f'<text x="{rx_x:.1f}" y="{margin_top - 8}" style="font-size:10px; font-weight:700; fill:#d9534f; text-anchor:middle;">Prescription ({plan.prescribed_dose_gy:.0f} Gy)</text>'
        )

    # Draw DVH Curves
    for s_name, curve in plan.curves.items():
        if not curve.doses_gy or not curve.volumes_percent:
            continue

        path_points = []
        for d, v in zip(curve.doses_gy, curve.volumes_percent):
            x = margin_left + min(1.0, (d / max_dose)) * chart_width
            y = margin_top + chart_height - (min(100.0, max(0.0, v)) / 100.0) * chart_height
            path_points.append(f"{x:.1f},{y:.1f}")

        if path_points:
            d_str = "M " + " L ".join(path_points)
            stroke_style = 'stroke-dasharray="6,3"' if not curve.is_target else ''
            svg_parts.append(
                f'<path d="{d_str}" stroke="{curve.color_hex}" class="curve-path" {stroke_style}>'
                f'<title>{_escape(s_name)}</title>'
                f'</path>'
            )

    # Main Axes
    svg_parts.append(
        f'<line x1="{margin_left}" y1="{margin_top + chart_height}" x2="{margin_left + chart_width}" y2="{margin_top + chart_height}" class="axis-line" />'
    )
    svg_parts.append(
        f'<line x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{margin_top + chart_height}" class="axis-line" />'
    )

    # Axis Titles
    svg_parts.append(
        f'<text x="{margin_left + chart_width/2:.1f}" y="{margin_top + chart_height + 48}" class="axis-title">Dose (Gy)</text>'
    )
    y_title_x = 22
    y_title_y = margin_top + chart_height/2
    svg_parts.append(
        f'<text x="{y_title_x}" y="{y_title_y:.1f}" class="axis-title" transform="rotate(-90 {y_title_x} {y_title_y:.1f})">Volume (%)</text>'
    )

    # Legend Panel
    leg_x = margin_left + chart_width + 25
    leg_y = margin_top + 10
    svg_parts.append(f'<text x="{leg_x}" y="{leg_y}" class="legend-title">Structures &amp; Metrics:</text>')

    for idx, (s_name, curve) in enumerate(plan.curves.items()):
        y_item = leg_y + 24 + (idx * 36)
        d_mean = compute_d_mean(curve)
        d_max = compute_d_max(curve)

        svg_parts.append(
            f'<rect x="{leg_x}" y="{y_item - 10}" width="16" height="12" fill="{curve.color_hex}" rx="2"/>'
        )
        svg_parts.append(
            f'<text x="{leg_x + 24}" y="{y_item}" class="legend-text">{_escape(s_name)}</text>'
        )
        svg_parts.append(
            f'<text x="{leg_x + 24}" y="{y_item + 14}" class="legend-sub">Dmean: {d_mean:.1f} Gy | Dmax: {d_max:.1f} Gy</text>'
        )

    svg_parts.append('</svg>')
    return "\n".join(svg_parts)
