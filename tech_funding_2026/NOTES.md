# tech_funding_2026 — methodology notes

Prepared 2026-09-03 from official texts staged under `/workspace/policy-briefs/` and `/workspace/.firecrawl/`.
**Rule: sourced figures only. Provincial subsidy RMB totals are unavailable and were not invented.**

## Purpose

Document the national 15th Five-Year Plan (2026–2030) tech-funding *series that official sources actually publish*, and the central vs local *policy instruments* they name, without fabricating a province-by-province subsidy ledger.

## Files

| file | role |
|---|---|
| `tech_funding_data.csv` | Machine-readable national series + instrument presence matrix + explicit provincial RMB gap rows |
| `plot_tech_funding.py` | Matplotlib multi-panel chart (reads the CSV) |
| `tech_funding_2026.png` | Generated figure |
| `NOTES.md` | This methodology note |

CSV `section` values: `national_series` · `illustrative_rd_envelope` · `central_vs_local_instruments` · `provincial_subsidy_gap`.
Column `provincial_subsidy_rmb` is **NA on every row**. 2030 R&D intensity and 2030 basic-research RMB/share are stored as explicit NA gap rows.


## Sources (crawled 2026-09-03)

1. **MOST minister channel**, 2026-03-05, Yin Hejun
   https://most.gov.cn/xwzx/twzb/fbh2026030501/twzbwzsl/202603/t20260305_196080.html
   2025 baselines: societal R&D **> RMB 3.92 tn**; intensity **2.8%**; basic research **~RMB 280 billion**, **7.08%** of R&D (first time above 7%).

2. **MOST work report** (Yin Hejun), 2026-01-26/27
   https://www.most.gov.cn/kjbgz/202601/t20260127_195800.html

3. **NDRC 15th FYP Outline** (official PDF)
   https://www.ndrc.gov.cn/fggz/fzzlgh/gjfzgh/202603/U020260317369114704096.pdf
   Local copy: `/workspace/policy-briefs/ndrc-15th-fyp-outline.pdf`
   Column 1 main indicators (indicative 预期性 unless noted):
   - Societal R&D **growth >7% per year**, constant prices (note ③). 2030 *level* cell is **blank (—)**. 2025 growth-rate cell in the table is 9.1 (a baseline rate, **not** used as a 15th FYP RMB path).
   - High-value invention patents per 10k people: **16 (2025) → >22 (2030)**.
   - Digital-economy core VA / GDP: **10.5% (2024*, starred) → 12.5% (2030)**.
   - Ch.8.1: 揭榜挂帅 / 赛马; 以奖代补 / 后补助.
   - Ch.8.2: expand national major S&T tasks and **NSFC original/disruptive** project scale and share.
   - Ch.8.3: basic-research share of R&D to **rise clearly** (no 2030 point).
   - Ch.9.2: improve **central fiscal S&T** allocation; **央地投入共担** for major S&T tasks.
   - Ch.12 / column 7: national integrated compute network; **东数西算**; government **purchase / leasing of compute**.
   - 完善首台（套）、首批次、首版次.

4. **CAC** digital China / cyber-power / AI+
   - Digital China route, 2026-03-17: https://www.cac.gov.cn/2026-03/17/c_1775482046495737.htm
   - AI+ opinion 国发〔2025〕11号: https://www.cac.gov.cn/2025-08/27/c_1758018277755538.htm
     Timed penetration: **>70% (2027)**, **>90% (2030)** of new-generation terminals/agents.
   - Cyber-power progress, 2026-04-20: https://www.cac.gov.cn/2026-04/20/c_1778423801556165.htm
     **5G BTS >4.90 million as of Feb 2026**; national compute scale described qualitatively as global #2.

5. **gov.cn** Xinhua explainers (2025-10-29, 2025-11-29) on 15th FYP tech self-reliance — no provincial RMB table.

6. **Shenzhen 15th FYP** (local counterpart, not a national series)
   https://fgw.sz.gov.cn/gkmlpt/content/12/12851/post_12851583.html
   Contains local *plan targets* (e.g. R&D intensity 7% by 2030, software & IT services VA > RMB 800 bn, national VC guidance-fund regional vehicle > RMB 50 bn). **Still no city-wide compute-voucher or IC-subsidy RMB table.** Those plan targets are **not** treated as provincial subsidy disbursements and are **not** entered as subsidy RMB in the CSV.

## National series used (CSV section `national_series`)

Only figures that appear in the sources above:

| series | year | value stored | bound | why this bound |
|---|---|---|---|---|
| societal_rd | 2025 | 3.92 RMB tn | lower | official wording 超过 / > |
| rd_intensity | 2025 | 2.8% of GDP | point | stated as 达到 2.8% |
| basic_research | 2025 | 0.28 RMB tn | approx | 接近 2800 亿元 |
| basic_research_share_of_rd | 2025 | 7.08% | point | 比重达到 7.08% |
| digital_economy_core_va_gdp | 2024 | 10.5% | point | Outline * = 2024 |
| digital_economy_core_va_gdp | 2030 | 12.5% | point | Outline indicative target |
| high_value_invention_patents_per_10k | 2025 | 16 | point | Outline |
| high_value_invention_patents_per_10k | 2030 | 22 | lower | official ＞22 |
| ai_terminal_agent_penetration | 2027 | 70% | lower | official >70% |
| ai_terminal_agent_penetration | 2030 | 90% | lower | official >90% |
| 5g_base_stations | 2026-02 | 4.90 million | lower | 突破 490 万座 |
| societal_rd_annual_growth_15fyp | 2026–2030 | 7% | lower | 年均增长 7% 以上, constant prices |

Basic research **absolute** (~0.28 tn) and **share** (7.08%) are stored as two independent sourced facts. They are **not** recomputed from each other (0.28 / 3.92 ≈ 7.14%, which would over-interpret two rounded lower/approx figures).

R&D intensity 2.8% (2025) is **not** restated as a 2030 point in Outline column 1, so no 2030 intensity is plotted.

## Illustrative R&D envelope (CSV section `illustrative_rd_envelope`, metric `societal_rd_illustrative_floor`)

Official sources do **not** publish 2026, 2027, 2028, 2029, or 2030 societal-R&D *levels*.

The chart therefore draws an **indicative floor path**:

```
R&D(year) = 3.92 × (1.07) ^ (year − 2025)
```

- 3.92 is the sourced 2025 **lower bound**.
- 7% is the sourced 15th FYP **growth floor** at constant prices.
- 2030 illustrative floor ≈ **5.50 RMB tn**.

This path is labeled in the CSV (`attribute = indicative_projection_not_official`) and on the chart: **not official point estimates**. A light band above the line marks that official language is “>7%” (open upside), not a ceiling. No second CAGR (e.g. 9.1%) is used as a projection; 9.1 in Outline col.1 is the 2025 *growth-rate* cell, not a 15th FYP RMB trajectory.

## Central vs local instruments (CSV section `central_vs_local_instruments`)

Qualitative **presence** (1/0), never RMB.

**Central**

- National major S&T projects / tasks
- NSFC original / disruptive projects
- National labs and major S&T infrastructure
- Hub compute / East-Data-West-Computing / national integrated compute network
- Central fiscal S&T allocation
- 揭榜挂帅 / 以奖代补 / 后补助
- R&D super-deduction (national tax lever)
- Government purchase of compute / compute leasing

**Local / regional**

- 央地投入共担 (marked present on **both** sides — it is a co-funding mechanism; the RMB split is unpublished)
- Low-latency compute in qualified regions
- Jing-Jin-Ji / Yangtze Delta / GBA international S&T centers, plus Chengdu-Chongqing, Wuhan, Xi’an
- Local first-mover pilots
- 首台（套）/ 首批次 / 首版次 application

Chart panel C is a **presence matrix**, not grouped RMB bars. Cell color means “this instrument is named at this level,” not spending size.

## CRITICAL GAP — provincial subsidy RMB unavailable

**Provincial (and city) subsidy RMB totals are not published in the official sources used here.**

Searched and not found:

- gov.cn 15th FYP tech-self-reliance explainers
- MOST 2026-01 work report and 2026-03-05 minister channel
- CAC digital China, AI+, cyber-power releases
- NDRC 15th FYP Outline (PDF + extracted text)
- Shenzhen 15th FYP (local counterpart)

There is **no** province-by-province (Jiangsu, Guangdong, Beijing, Shanghai, …) or city-by-city table of S&T subsidies, compute vouchers, or IC grants in RMB.

Consequences for the deliverables:

1. CSV column `provincial_subsidy_rmb` is **NA on every row**.
2. CSV section `provincial_subsidy_gap` lists Jing-Jin-Ji, Yangtze Delta, GBA, Chengdu-Chongqing, Wuhan, Xi’an, Shenzhen, and an all-province aggregate — each with `value = NA` and `provincial_subsidy_rmb = NA`.
3. The chart **does not draw local RMB bars**. Doing so would be fabrication.
4. 央地投入共担 is recorded as a *mechanism*, not as a numeric split.
5. Shenzhen local plan targets (intensity, software VA, VC vehicle) are noted above as **plan targets**, not subsidy disbursements, and are excluded from the national numeric series.

Anyone needing provincial subsidy RMB must wait for a source that actually publishes them (e.g. provincial finance yearbooks or dedicated subsidy catalogues). They cannot be inferred from the national Outline.

## Chart construction

Three panels, matplotlib, Noto Sans CJK:

- **A** — 2025 crimson marker at 3.92 tn; dashed 7% CAGR floor through 2030; open-upside band; annotation that this is indicative.
- **B** — two independent 2025 facts as callouts: ~0.28 tn absolute and 7.08% share; composition bar uses the sourced share (not a derived RMB residual).
- **C** — 14×3 presence matrix (central / co-funded / local). 央地投入共担 is the only row marked on all three. Footer states the provincial RMB gap.

Companion national figures that are in the CSV but not plotted as extra panels (to keep the figure to the requested A/B/C): R&D intensity 2.8%, digital-core VA/GDP 10.5%→12.5%, patents 16→>22, AI penetration >70% / >90%, 5G BTS >4.90 m. They remain in the data file for downstream use.

## Reproduction

```bash
cd /workspace/tech_funding_2026
source .venv/bin/activate
pip install matplotlib pandas numpy
python plot_tech_funding.py
```

Expected: `tech_funding_2026.png` larger than 10 KB.

## What was deliberately not done

- No invented 2026–2030 official R&D *levels*.
- No invented 2030 R&D intensity.
- No invented basic-research 2030 RMB or share.
- **No invented provincial or city subsidy RMB.**
- No treating Shenzhen plan VA / VC-fund figures as national or subsidy series.
- No fake stacked “central vs local spending” bars.
