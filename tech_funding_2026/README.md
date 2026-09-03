# tech_funding_2026

Structured extract of **15th FYP China tech self-reliance funding signals** for the Data Analyst workstream. Figures are only those stated in gov.cn / MOST / CAC / NDRC Outline sources crawled **2026-09-03**.

## Critical constraint

**Provincial subsidy RMB totals are not in official releases. They were not invented.**

Every instrument row has `rmb_total_tn = NA`. Every named region in `provincial_subsidy_gap.csv` has `subsidy_rmb_tn = NA`. Null / NA is a documentation gap, **not** a zero subsidy.

Chart Panel C is therefore a **presence matrix of policy instruments** (central / co-funded / local), matching the Researcher’s instruction: co-funding, hub vs low-latency compute, three S&T centers — **not fake RMB bars**.

## Outputs

| file | role |
|---|---|
| `tech_funding_data.json` | Canonical structured file (national series, illustrative envelope, instruments, provincial gap) |
| `tech_funding_data.csv` | Sourced numeric series + illustrative 7% CAGR floor, long format, `series_type` and `notes` columns |
| `central_vs_local_instruments.csv` | Instrument presence table; `rmb_total_tn` is NA on every row |
| `provincial_subsidy_gap.csv` | Named S&T-center / hub regions with unpublished RMB explicitly marked NA |
| `tech_funding_2026.png` | Three-panel chart |
| `plot_tech_funding_2026.py` | Reproducible matplotlib / seaborn script |

## Chart design

**Panel A — R&D trajectory.** 2025 MOST baseline `>3.92` RMB tn (plotted as a lower-bound marker). Dashed line compounds that bound at **exactly 7%** through 2030 (`3.92 × 1.07^(t)`, ≈5.50 tn in 2030). Official language is **annual growth >7% at constant prices** (indicative), so shading **above** the dashed line is an unquantified “greater than” region. The 2030 value is **not** an official point estimate. No second invented CAGR (e.g. 8% or 9%) is treated as data.

**Panel B — Basic research.** Sourced 2025 figures only: **~0.28 tn** (MOST: ~RMB 280 bn) and **7.08% of R&D**. Composition bar uses the reported share, not `0.28/3.92`. The implied residual `~3.64 tn` is derived and labelled as such. 15th FYP says the share should “rise clearly”; **no 2030 RMB or 2030 % was published**, so none is plotted.

**Panel C — Central vs local instruments.** Seaborn heatmap of presence (1) vs not-this-layer (0). Columns: Central; Co-funded (央地投入共担); Local / regional. Rows follow the extracted-targets list (national projects, NSFC, labs, hub compute / 东数西算, central fiscal S&T, 揭榜挂帅 / 以奖代补 / 后补助, R&D super-deduction, gov purchase of compute, 央地投入共担, low-latency compute, three international S&T centers, Chengdu-Chongqing / Wuhan / Xi’an, local pilots, 首台套). **No RMB magnitudes.**

Other sourced national KPIs (R&D intensity 2.8% 2025; digital-economy core VA/GDP 10.5% 2024 → 12.5% 2030; high-value invention patents/10k 16 → >22; AI terminal/agent penetration >70% 2027 / >90% 2030; 5G BTS >4.90m as of Feb 2026) live in the data file. They are **not** funding totals and are not forced into the three requested panels.

## Methodology notes

- **Sourced vs derived vs illustrative vs gap.** `series_type` is one of `sourced`, `derived`, `illustrative_7pct_cagr_floor`, `gap`, `qualitative`. `value_qualifier` records `lower_bound_gt`, `approximate`, `unpublished`, etc.
- **Do not force-reconcile** `0.28 / 3.92 ≈ 7.14%` with the separately reported `7.08%` share. One is approximate RMB, the other is a reported percentage, and 3.92 is itself a lower bound.
- **Constant prices.** The >7% rule is specified at constant prices. The envelope is an arithmetic illustration of that floor, not a deflator-adjusted official path.
- **Reproduce:** from this directory, `.venv/bin/python plot_tech_funding_2026.py` (see `requirements.txt`). Canonical input is `tech_funding_data.json`; CSVs and PNG are regenerated on each run.

## Source of figures

Staged extract: `/workspace/policy-briefs/04-extracted-targets-for-data-analyst.md` (and the MOST / gov.cn / CAC briefs behind it). Primary citations:

- MOST 2026-03-05 (2025 societal R&D, intensity, basic research)
- NDRC 15th FYP Outline col.1 #4–6, ch.8.3, ch.9.2, ch.12
- 国发〔2025〕11号 via CAC (AI penetration waypoints)
- CAC 2026-04-20 (5G stock, Feb 2026)

## Canonical script

Regenerate CSVs + PNG from the JSON:

```bash
cd /workspace/tech_funding_2026
.venv/bin/python plot_tech_funding_2026.py
```

`NOTES.md` has additional source URLs. `plot_tech_funding.py` is an earlier draft; **`plot_tech_funding_2026.py` is the script that matches `tech_funding_data.json`.**
