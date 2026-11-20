#!/usr/bin/env python3
"""Plot algorithm comparison CSV as an SVG grouped bar chart (no extra deps)."""

from __future__ import annotations

import argparse
import csv
import os
import sys


COLORS = {
    "waiting": "#d97706",
    "turnaround": "#2563eb",
    "response": "#7c3aed",
}


def read_rows(path: str):
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    if not rows:
        raise SystemExit(f"No data rows in {path}")
    required = {"algorithm", "avg_waiting", "avg_turnaround", "avg_response"}
    if not required.issubset(rows[0].keys()):
        raise SystemExit(f"CSV missing columns; expected {sorted(required)}")
    return rows


def write_svg(rows, out_path: str) -> None:
    width = 720
    height = 420
    margin_left = 60
    margin_right = 24
    margin_top = 48
    margin_bottom = 72
    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom

    algos = [r["algorithm"] for r in rows]
    series = [
        ("avg_waiting", "Waiting", COLORS["waiting"]),
        ("avg_turnaround", "Turnaround", COLORS["turnaround"]),
        ("avg_response", "Response", COLORS["response"]),
    ]

    values = []
    for r in rows:
        for key, _, _ in series:
            values.append(float(r[key]))
    y_max = max(values) if values else 1.0
    if y_max <= 0:
        y_max = 1.0
    y_max *= 1.15

    group_w = plot_w / max(len(algos), 1)
    bar_gap = 4
    bar_w = (group_w - 20 - bar_gap * (len(series) - 1)) / len(series)
    if bar_w > 28:
        bar_w = 28

    def y_scale(v: float) -> float:
        return margin_top + plot_h * (1.0 - (v / y_max))

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<text x="24" y="28" font-family="Helvetica, Arial, sans-serif" '
        'font-size="18" fill="#111827">Scheduler comparison</text>',
        f'<line x1="{margin_left}" y1="{margin_top}" '
        f'x2="{margin_left}" y2="{margin_top + plot_h}" '
        'stroke="#9ca3af" stroke-width="1"/>',
        f'<line x1="{margin_left}" y1="{margin_top + plot_h}" '
        f'x2="{margin_left + plot_w}" y2="{margin_top + plot_h}" '
        'stroke="#9ca3af" stroke-width="1"/>',
    ]

    for tick in range(0, 5):
        v = y_max * tick / 4.0
        y = y_scale(v)
        parts.append(
            f'<line x1="{margin_left}" y1="{y:.1f}" '
            f'x2="{margin_left + plot_w}" y2="{y:.1f}" '
            'stroke="#e5e7eb" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{margin_left - 8}" y="{y + 4:.1f}" text-anchor="end" '
            f'font-family="Helvetica, Arial, sans-serif" font-size="11" '
            f'fill="#6b7280">{v:.1f}</text>'
        )

    for i, row in enumerate(rows):
        group_x = margin_left + i * group_w + (group_w - (len(series) * bar_w + (len(series) - 1) * bar_gap)) / 2
        for j, (key, _label, color) in enumerate(series):
            val = float(row[key])
            x = group_x + j * (bar_w + bar_gap)
            y = y_scale(val)
            h = margin_top + plot_h - y
            parts.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" '
                f'fill="{color}">'
                f'<title>{row["algorithm"]} {_label}: {val:.2f}</title></rect>'
            )
        cx = margin_left + i * group_w + group_w / 2
        parts.append(
            f'<text x="{cx:.1f}" y="{margin_top + plot_h + 20}" text-anchor="middle" '
            f'font-family="Helvetica, Arial, sans-serif" font-size="12" '
            f'fill="#111827">{row["algorithm"]}</text>'
        )

    legend_x = margin_left
    legend_y = height - 28
    for j, (_key, label, color) in enumerate(series):
        x = legend_x + j * 140
        parts.append(f'<rect x="{x}" y="{legend_y - 10}" width="12" height="12" fill="{color}"/>')
        parts.append(
            f'<text x="{x + 18}" y="{legend_y}" font-family="Helvetica, Arial, sans-serif" '
            f'font-size="12" fill="#374151">{label}</text>'
        )

    parts.append("</svg>")

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))
        f.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "csv_path",
        nargs="?",
        default="build/compare.csv",
        help="CSV from ./scheduler ... compare (default: build/compare.csv)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="build/compare.svg",
        help="Output SVG path (default: build/compare.svg)",
    )
    args = parser.parse_args()

    if not os.path.isfile(args.csv_path):
        print(f"CSV not found: {args.csv_path}", file=sys.stderr)
        print("Run: ./scheduler data/processes1.txt compare 4", file=sys.stderr)
        return 1

    rows = read_rows(args.csv_path)
    write_svg(rows, args.output)
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
