#!/usr/bin/env python3
"""tech_funding_2026 — sourced 15th FYP funding signals, no invented provincial RMB.

Reads tech_funding_data.json (canonical), writes:
  - tech_funding_data.csv
  - central_vs_local_instruments.csv
  - provincial_subsidy_gap.csv
  - tech_funding_2026.png

Panel A: 2025 MOST R&D baseline + illustrative >7% CAGR floor to 2030
         (NOT official 2030 point estimates).
Panel B: Basic research ~0.28 tn / 7.08% share (2025); 2030 share qualitative only.
Panel C: Central vs local *instrument presence* heatmap — rmb_total is NA on every row.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib import font_manager as fm
from matplotlib.colors import ListedColormap
from matplotlib.gridspec import GridSpec
from matplotlib.patches import FancyBboxPatch, Patch, Rectangle

HERE = Path(__file__).resolve().parent
JSON_PATH = HERE / "tech_funding_data.json"
PNG_PATH = HERE / "tech_funding_2026.png"
CSV_SERIES = HERE / "tech_funding_data.csv"
CSV_INSTR = HERE / "central_vs_local_instruments.csv"
CSV_PROV = HERE / "provincial_subsidy_gap.csv"

# --- palette (print-safe, muted) ---
NAVY = "#1B365D"
CRIMSON = "#9B2C2C"
GOLD = "#B7791F"
TEAL = "#276749"
SLATE = "#4A5568"
INK = "#1A202C"
MUTED = "#718096"
PAPER = "#F4EFE6"
PANEL = "#FFFCF7"
ENVELOPE = "#2B6CB0"
GRID = "#E2D9CC"
ZERO = "#EDE6D9"
PRESENT = "#1B365D"

CJK_REG = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
CJK_BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"


def cjk(size=10, weight="regular"):
    path = CJK_BOLD if weight == "bold" else CJK_REG
    return fm.FontProperties(fname=path, size=size)


def configure_fonts():
    for p in (CJK_REG, CJK_BOLD):
        try:
            fm.fontManager.addfont(p)
        except Exception:
            pass
    sns.set_theme(style="white", rc={"axes.spines.top": False, "axes.spines.right": False})
    # Set CJK-capable default AFTER seaborn theme so heatmap tick layout
    # does not fall back to DejaVu Sans (missing CJK glyphs).
    mpl.rcParams.update(
        {
            "figure.facecolor": PAPER,
            "axes.facecolor": PANEL,
            "axes.edgecolor": "#CBD5E0",
            "axes.labelcolor": INK,
            "text.color": INK,
            "xtick.color": SLATE,
            "ytick.color": SLATE,
            "axes.unicode_minus": False,
            "font.size": 10,
            "axes.titlesize": 12,
            "figure.dpi": 140,
            "savefig.dpi": 160,
            "savefig.facecolor": PAPER,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "font.family": "sans-serif",
            "font.sans-serif": [
                "Noto Sans CJK SC",
                "Noto Sans CJK JP",
                "DejaVu Sans",
            ],
        }
    )


def load():
    with JSON_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def export_csvs(data: dict) -> None:
    """Flatten JSON tables to CSVs. Null → NA. Never fills provincial RMB."""
    series_rows = []
    for r in data["national_series"]:
        series_rows.append(
            {
                "table": "national_series",
                "metric_id": r.get("metric_id"),
                "metric": r.get("metric"),
                "year": r.get("year") if r.get("year") is not None else "",
                "period": r.get("period", ""),
                "value": r.get("value") if r.get("value") is not None else "NA",
                "value_qualifier": r.get("value_qualifier"),
                "unit": r.get("unit") or "",
                "series_type": r.get("series_type"),
                "is_official_point_estimate": r.get("is_official_point_estimate"),
                "official_wording": r.get("official_wording") or "",
                "source": r.get("source"),
                "notes": r.get("notes") or "",
            }
        )
    for r in data["illustrative_rd_envelope"]:
        series_rows.append(
            {
                "table": "illustrative_rd_envelope",
                "metric_id": "societal_rd_illustrative_7pct_cagr_floor",
                "metric": "Societal R&D — illustrative 7% CAGR floor (constant prices)",
                "year": r["year"],
                "period": "",
                "value": r["rd_tn_at_7pct_floor"],
                "value_qualifier": "illustrative_floor_not_official",
                "unit": "RMB_tn",
                "series_type": r["series_type"],
                "is_official_point_estimate": False,
                "official_wording": "",
                "source": "Derived: 3.92 × 1.07^(year-2025); growth *rule* from Outline col.1 #4",
                "notes": r["notes"],
            }
        )
    pd.DataFrame(series_rows).to_csv(CSV_SERIES, index=False, encoding="utf-8")

    instr = pd.DataFrame(data["central_vs_local_instruments"])
    # Keep rmb_total_tn as NA string so the gap is visible in Excel
    instr["rmb_total_tn"] = instr["rmb_total_tn"].apply(
        lambda x: "NA" if x is None or (isinstance(x, float) and np.isnan(x)) else x
    )
    instr.to_csv(CSV_INSTR, index=False, encoding="utf-8")

    prov = pd.DataFrame(data["provincial_subsidy_gap"])
    prov["subsidy_rmb_tn"] = prov["subsidy_rmb_tn"].apply(
        lambda x: "NA" if x is None or (isinstance(x, float) and np.isnan(x)) else x
    )
    prov.to_csv(CSV_PROV, index=False, encoding="utf-8")


def panel_a(ax, data: dict) -> None:
    env = data["illustrative_rd_envelope"]
    years = np.array([r["year"] for r in env], dtype=float)
    floor = np.array([r["rd_tn_at_7pct_floor"] for r in env], dtype=float)

    ax.set_facecolor(PANEL)
    # 15th FYP window
    ax.axvspan(2025.5, 2030.35, color="#E8F0F7", alpha=0.85, zorder=0)
    ax.text(
        2027.9,
        6.42,
        "15th FYP window (indicative >7% rule)",
        ha="center",
        va="top",
        fontproperties=cjk(8),
        color=ENVELOPE,
        zorder=4,
    )

    y_top = 6.55
    ax.fill_between(
        years,
        floor,
        np.full_like(floor, y_top),
        color=ENVELOPE,
        alpha=0.10,
        hatch="///",
        edgecolor=ENVELOPE,
        linewidth=0.0,
        zorder=1,
        label="Indicative >7% region (unquantified; not official points)",
    )
    ax.plot(
        years,
        floor,
        color=NAVY,
        ls="--",
        lw=2.0,
        marker="o",
        ms=5.5,
        markerfacecolor=PANEL,
        markeredgecolor=NAVY,
        markeredgewidth=1.4,
        zorder=3,
        label="Illustrative path at the 7% CAGR floor",
    )
    # 2025 sourced baseline
    ax.scatter(
        [2025],
        [3.92],
        s=110,
        color=CRIMSON,
        zorder=5,
        edgecolors="white",
        linewidths=1.2,
        label="2025 MOST baseline (sourced, >3.92 tn)",
    )
    ax.annotate(
        ">3.92 tn\n2025 MOST baseline\n(lower bound)",
        xy=(2025, 3.92),
        xytext=(2025.18, 4.55),
        fontproperties=cjk(8.5),
        color=CRIMSON,
        ha="left",
        arrowprops=dict(arrowstyle="-", color=CRIMSON, lw=0.8),
        zorder=6,
    )
    ax.annotate(
        "≈5.50 tn at 7% floor\nindicative — not an official\n2030 point estimate",
        xy=(2030, floor[-1]),
        xytext=(2028.05, 5.72),
        fontproperties=cjk(8.2),
        color=NAVY,
        ha="left",
        arrowprops=dict(arrowstyle="-", color=NAVY, lw=0.8),
        zorder=6,
    )
    ax.text(
        2026.15,
        5.95,
        "Official rule: annual growth >7%\n(constant prices) → realised path\nwould lie on or above this floor",
        fontproperties=cjk(7.8),
        color=ENVELOPE,
        ha="left",
        va="center",
        linespacing=1.35,
    )

    ax.set_xlim(2024.7, 2030.45)
    ax.set_ylim(3.55, y_top)
    ax.set_xticks([2025, 2026, 2027, 2028, 2029, 2030])
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.1f"))
    ax.set_ylabel(
        "Societal R&D (RMB tn, constant prices — illustrative path)",
        fontproperties=cjk(9),
        color=SLATE,
    )
    ax.set_title(
        "A. National societal R&D: 2025 baseline vs 15th FYP >7% CAGR envelope",
        fontproperties=cjk(11, "bold"),
        color=NAVY,
        loc="left",
        pad=8,
    )
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.grid(axis="x", visible=False)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.spines["left"].set_color("#CBD5E0")
    ax.spines["bottom"].set_color("#CBD5E0")
    for lab in ax.get_xticklabels() + ax.get_yticklabels():
        lab.set_fontproperties(cjk(8.5))
    leg = ax.legend(
        loc="lower right",
        frameon=True,
        fancybox=False,
        edgecolor="#E2D9CC",
        facecolor="#FFFdf8",
        prop=cjk(7.4),
        borderpad=0.6,
    )
    leg.get_frame().set_linewidth(0.6)


def panel_b(ax, data: dict) -> None:
    ax.set_facecolor(PANEL)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.set_title(
        "B. Basic research, 2025 — absolute and share of R&D",
        fontproperties=cjk(11, "bold"),
        color=NAVY,
        loc="left",
        pad=8,
    )

    def card(x, y, w, h, face):
        box = FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.012,rounding_size=0.02",
            linewidth=1.0,
            edgecolor="#D6CBB8",
            facecolor=face,
            transform=ax.transAxes,
            zorder=2,
        )
        ax.add_patch(box)

    card(0.02, 0.58, 0.46, 0.36, "#F8EDED")
    card(0.52, 0.58, 0.46, 0.36, "#EAF2EA")

    ax.text(
        0.25,
        0.86,
        "~0.28 tn",
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontproperties=cjk(16, "bold"),
        color=CRIMSON,
        zorder=3,
    )
    ax.text(
        0.25,
        0.72,
        "Basic research, 2025\nMOST: ~RMB 280 bn",
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontproperties=cjk(7.6),
        color=SLATE,
        zorder=3,
        linespacing=1.35,
    )
    ax.text(
        0.75,
        0.86,
        "7.08%",
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontproperties=cjk(16, "bold"),
        color=TEAL,
        zorder=3,
    )
    ax.text(
        0.75,
        0.72,
        "of societal R&D, 2025\nfirst time above 7%",
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontproperties=cjk(7.6),
        color=SLATE,
        zorder=3,
        linespacing=1.35,
    )

    # Composition bar using the *reported share* (7.08), not the 0.28/3.92 residual
    ax.text(
        0.02,
        0.50,
        "2025 composition (reported share)     residual ~3.64 tn is derived, not independently sourced",
        transform=ax.transAxes,
        ha="left",
        va="center",
        fontproperties=cjk(7.2),
        color=MUTED,
        zorder=3,
    )
    bar_y, bar_h = 0.33, 0.12
    share = 0.0708
    ax.add_patch(
        Rectangle(
            (0.02, bar_y),
            share * 0.96,
            bar_h,
            transform=ax.transAxes,
            facecolor=TEAL,
            edgecolor="none",
            zorder=3,
        )
    )
    ax.add_patch(
        Rectangle(
            (0.02 + share * 0.96, bar_y),
            (1 - share) * 0.96,
            bar_h,
            transform=ax.transAxes,
            facecolor="#D9E2D9",
            edgecolor="none",
            zorder=3,
        )
    )
    ax.text(
        0.02 + share * 0.96 * 0.5,
        bar_y + bar_h + 0.015,
        "7.08%\nbasic",
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontproperties=cjk(7.2, "bold"),
        color=TEAL,
        zorder=3,
        linespacing=1.15,
    )
    ax.text(
        0.55,
        bar_y + bar_h * 0.5,
        "other R&D  92.92%",
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontproperties=cjk(8),
        color=TEAL,
        zorder=4,
    )

    ax.add_patch(
        FancyBboxPatch(
            (0.02, 0.04),
            0.96,
            0.24,
            boxstyle="round,pad=0.01,rounding_size=0.018",
            linewidth=1.0,
            edgecolor="#E8D9A8",
            facecolor="#FBF6E8",
            transform=ax.transAxes,
            zorder=2,
        )
    )
    ax.text(
        0.50,
        0.16,
        "15th FYP: basic-research share of R&D “to rise clearly”\n"
        "No 2030 RMB total or 2030 % published  →  not plotted",
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontproperties=cjk(8),
        color=GOLD,
        zorder=3,
        linespacing=1.4,
    )


def panel_c(ax, data: dict) -> None:
    instr = data["central_vs_local_instruments"]
    labels = []
    rows = []
    for r in instr:
        prefix = {"central": "C  ", "cofunded": "C+L ", "local": "L  "}[r["layer"]]
        labels.append(prefix + r["instrument_en"] + "  ·  " + r["instrument_zh"])
        rows.append(
            {
                "Central": r["presence_central"],
                "Co-funded  (央地共担)": r["presence_cofunded"],
                "Local / regional": r["presence_local"],
            }
        )
    df = pd.DataFrame(rows, index=labels)
    annot = df.map(lambda v: "●" if v == 1 else "")
    cmap = ListedColormap([ZERO, PRESENT])
    sns.heatmap(
        df,
        ax=ax,
        cmap=cmap,
        vmin=0,
        vmax=1,
        cbar=False,
        linewidths=2.0,
        linecolor="white",
        square=False,
        annot=annot,
        fmt="",
        annot_kws={"color": "white", "fontsize": 11, "ha": "center", "va": "center"},
        xticklabels=True,
        yticklabels=True,
    )
    ax.xaxis.tick_top()
    ax.tick_params(axis="x", length=0, pad=6, labelrotation=0)
    ax.tick_params(axis="y", length=0, pad=4)
    ax.set_xlabel("")
    ax.set_ylabel("")
    for lab in ax.get_xticklabels():
        lab.set_fontproperties(cjk(9.5, "bold"))
        lab.set_color(NAVY)
    layer_color = {"C  ": NAVY, "C+L ": GOLD, "L  ": TEAL}
    for tick in ax.get_yticklabels():
        tick.set_fontproperties(cjk(8.1))
        key = "C+L " if tick.get_text().startswith("C+L") else tick.get_text()[:3]
        tick.set_color(layer_color.get(key, INK))
    ax.set_title(
        "C. Central vs local policy instruments — presence only, not RMB  "
        "(every rmb_total_tn = NA; provincial subsidy totals unpublished)",
        fontproperties=cjk(11, "bold"),
        color=NAVY,
        loc="left",
        pad=14,
    )
    legend_handles = [
        Patch(facecolor=PRESENT, edgecolor="white", label="Instrument present on this layer"),
        Patch(facecolor=ZERO, edgecolor="#D6CBB8", label="Not this layer (RMB still NA — not zero)"),
    ]
    ax.legend(
        handles=legend_handles,
        loc="lower right",
        bbox_to_anchor=(1.0, -0.085),
        ncol=2,
        frameon=False,
        prop=cjk(7.6),
        handlelength=1.4,
        handleheight=0.9,
        borderaxespad=0.0,
    )



def draw(data: dict) -> None:
    configure_fonts()
    fig = plt.figure(figsize=(16.4, 12.6))
    gs = GridSpec(
        3,
        2,
        figure=fig,
        height_ratios=[1.12, 1.62, 0.22],
        width_ratios=[1.22, 0.90],
        hspace=0.42,
        wspace=0.22,
        left=0.22,
        right=0.975,
        top=0.88,
        bottom=0.055,
    )
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[1, :])
    ax_f = fig.add_subplot(gs[2, :])
    ax_f.axis("off")

    fig.suptitle(
        "China 15th FYP tech self-reliance: sourced funding signals",
        fontproperties=cjk(16.5, "bold"),
        color=NAVY,
        x=0.22,
        ha="left",
        y=0.975,
    )
    fig.text(
        0.22,
        0.942,
        "National R&D envelope and policy-instrument map  ·  "
        "Provincial subsidy RMB totals are not in official releases and are not invented here",
        fontproperties=cjk(9.5),
        color=SLATE,
        ha="left",
        va="top",
    )
    fig.text(
        0.975,
        0.975,
        "Extracted 2026-09-03\ngov.cn / MOST / CAC / NDRC Outline",
        fontproperties=cjk(8),
        color=MUTED,
        ha="right",
        va="top",
    )

    panel_a(ax_a, data)
    panel_b(ax_b, data)
    panel_c(ax_c, data)

    ax_f.text(
        0.0,
        0.62,
        "Sources: MOST 2026-03-05 (societal R&D >3.92 tn, intensity 2.8%, basic research ~0.28 tn / 7.08%); "
        "NDRC 15th FYP Outline col.1 #4–6, ch.8.3, ch.9.2, ch.12 ( >7% constant-price R&D growth, patents, digital-economy VA, 央地投入共担, compute); "
        "国发〔2025〕11号 / CAC (AI penetration >70% 2027, >90% 2030); CAC 2026-04-20 (5G BTS >4.90m, Feb 2026).",
        fontproperties=cjk(7.4),
        color=SLATE,
        ha="left",
        va="top",
        wrap=True,
        linespacing=1.35,
    )
    ax_f.text(
        0.0,
        0.08,
        "Methodology: Panel A compounds the 2025 lower bound at exactly 7% to draw the official floor; shading above the line is an unquantified “greater than” region, not a second CAGR. "
        "Panel B uses the reported 7.08% share; the ~3.64 tn residual is derived (3.92 − 0.28) and flagged. "
        "Panel C is a presence matrix — C = central, C+L = co-funded, L = local. "
        "Critical constraint: no province-by-province subsidy RMB table exists in the crawled releases; rmb_total_tn / subsidy_rmb_tn are NA throughout. Null ≠ 0.",
        fontproperties=cjk(7.4),
        color=MUTED,
        ha="left",
        va="top",
        wrap=True,
        linespacing=1.35,
    )

    fig.savefig(PNG_PATH, dpi=160)
    plt.close(fig)


def main() -> None:
    data = load()
    export_csvs(data)
    draw(data)
    print(f"wrote {CSV_SERIES}")
    print(f"wrote {CSV_INSTR}")
    print(f"wrote {CSV_PROV}")
    print(f"wrote {PNG_PATH}")
    # sanity: no fabricated provincial numbers
    for row in data["provincial_subsidy_gap"]:
        assert row["subsidy_rmb_tn"] is None, row
    for row in data["central_vs_local_instruments"]:
        assert row["rmb_total_tn"] is None, row
    print("sanity: all provincial / instrument RMB fields are null")


if __name__ == "__main__":
    main()
