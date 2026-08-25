"""
CLI for dvh-analyzer.
"""

import argparse
import sys
from .models import PlanAssessment
from .parser import parse_dvh_csv
from .evaluator import evaluate_plan_constraints
from .metrics import compute_homogeneity_index, compute_d_mean, compute_d_max, compute_geud, get_volume_at_dose
from .renderer_svg import render_dvh_svg


def _generate_thoracic_sample_csv() -> str:
    """Generates realistic Thoracic Radiotherapy (60 Gy in 30 fx) DVH dataset."""
    lines = ["Dose_Gy,PTV_60Gy,Spinal_Cord,Total_Lungs,Heart,Esophagus"]
    for d in range(0, 71):
        dose = float(d)
        # PTV: high volume until 60 Gy, steep drop
        if dose <= 58.0:
            ptv = 100.0
        elif dose <= 60.0:
            ptv = 100.0 - (dose - 58.0) * 2.5
        elif dose <= 63.0:
            ptv = 95.0 - (dose - 60.0) * 30.0
        else:
            ptv = 0.0

        # Spinal Cord: drops off early, max ~38 Gy
        if dose <= 10.0:
            cord = 100.0 - dose * 4.0
        elif dose <= 25.0:
            cord = 60.0 - (dose - 10.0) * 3.0
        elif dose <= 38.0:
            cord = 15.0 - (dose - 25.0) * 1.15
        else:
            cord = 0.0

        # Lungs: V20Gy around 22%, V5Gy around 52%
        if dose <= 5.0:
            lung = 100.0 - dose * 9.6
        elif dose <= 20.0:
            lung = 52.0 - (dose - 5.0) * 2.0
        elif dose <= 60.0:
            lung = 22.0 - (dose - 20.0) * 0.55
        else:
            lung = 0.0

        # Heart: V25Gy around 6%, Dmean ~8 Gy
        if dose <= 10.0:
            heart = 100.0 - dose * 7.5
        elif dose <= 25.0:
            heart = 25.0 - (dose - 10.0) * 1.25
        elif dose <= 50.0:
            heart = 6.25 - (dose - 25.0) * 0.25
        else:
            heart = 0.0

        # Esophagus
        if dose <= 15.0:
            eso = 100.0 - dose * 4.0
        elif dose <= 35.0:
            eso = 40.0 - (dose - 15.0) * 1.25
        elif dose <= 60.0:
            eso = 15.0 - (dose - 35.0) * 0.6
        else:
            eso = 0.0

        lines.append(f"{dose:.1f},{max(0.0, ptv):.2f},{max(0.0, cord):.2f},{max(0.0, lung):.2f},{max(0.0, heart):.2f},{max(0.0, eso):.2f}")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="dvh-analyzer",
        description="Radiation Oncology Dose-Volume Histogram (DVH) Analyzer & QUANTEC Constraint Compliance Engine.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Report
    rep_parser = subparsers.add_parser("report", help="Calculate dosimetric metrics and evaluate QUANTEC compliance")
    rep_parser.add_argument("-i", "--input", required=True, help="Path to DVH CSV file")
    rep_parser.add_argument("--rx", type=float, default=60.0, help="Prescribed dose in Gy (default: 60.0)")

    # Plot
    plot_parser = subparsers.add_parser("plot", help="Render DVH Multi-Structure Overlay SVG")
    plot_parser.add_argument("-i", "--input", required=True, help="Path to DVH CSV file")
    plot_parser.add_argument("-o", "--output", default="dvh_plot.svg", help="Output SVG filepath")
    plot_parser.add_argument("-t", "--title", default="Dose-Volume Histogram", help="Plot title")
    plot_parser.add_argument("--rx", type=float, default=60.0, help="Prescribed dose in Gy")

    # Sample CSV
    sample_parser = subparsers.add_parser("sample-csv", help="Generate sample Thoracic Radiotherapy DVH CSV")
    sample_parser.add_argument("-o", "--output", default=None, help="Save to file (or stdout)")

    args = parser.parse_args(argv)

    if args.command == "sample-csv":
        data = _generate_thoracic_sample_csv()
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(data)
            print(f"Sample DVH CSV written to: {args.output}")
        else:
            sys.stdout.write(data)
        return 0

    if args.command == "plot":
        plan = parse_dvh_csv(args.input, prescribed_dose_gy=args.rx)
        svg_content = render_dvh_svg(plan, title=args.title)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(svg_content)
        print(f"DVH plot successfully rendered -> {args.output} ({len(plan.curves)} structures)")
        return 0

    if args.command == "report":
        plan = parse_dvh_csv(args.input, prescribed_dose_gy=args.rx)
        print("=" * 80)
        print(f"  RADIOTHERAPY PLAN DOSIMETRY & QUANTEC AUDIT: {plan.plan_name}")
        print(f"  Prescribed Dose: {plan.prescribed_dose_gy:.1f} Gy")
        print("=" * 80)

        # Target Structures
        targets = [c for c in plan.curves.values() if c.is_target]
        if targets:
            print("\n[TARGET METRICS (PTV / CTV)]")
            for t in targets:
                hi = compute_homogeneity_index(t)
                d_mean = compute_d_mean(t)
                d_max = compute_d_max(t)
                v95 = get_volume_at_dose(t, plan.prescribed_dose_gy * 0.95)
                print(f"  • {t.structure_name:18} | Dmean: {d_mean:.1f} Gy | Dmax: {d_max:.1f} Gy | V95%: {v95:.1f}% | HI (ICRU 83): {hi:.3f}")

        # QUANTEC Evaluations
        evals = evaluate_plan_constraints(plan)
        print("\n[ORGAN-AT-RISK (OAR) QUANTEC COMPLIANCE]")
        print(f"{'Structure':<16} | {'Metric':<8} | {'Plan Val':<10} | {'Constraint':<12} | {'Status':<8} | {'Clinical Endpoint'}")
        print("-" * 80)

        all_pass = True
        for ev in evals:
            status_str = f"[{ev.result.value}]"
            if ev.result.value != "PASS":
                all_pass = False
            limit_str = f"<= {ev.limit_value:.1f} {ev.unit}"
            plan_val_str = f"{ev.computed_value:.1f} {ev.unit}"
            print(f"{ev.structure_name:<16} | {ev.metric_label:<8} | {plan_val_str:<10} | {limit_str:<12} | {status_str:<8} | {ev.endpoint}")

        print("-" * 80)
        if all_pass:
            print("  OVERALL AUDIT: ALL QUANTEC NORMAL TISSUE CONSTRAINTS MET [PASS]")
        else:
            print("  OVERALL AUDIT: ONE OR MORE CONSTRAINTS EXCEEDED [REVIEW REQUIRED]")
        print("=" * 80)
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
