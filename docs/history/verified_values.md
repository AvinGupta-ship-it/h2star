# H2STAR v1.0 — verified-values ledger (load-bearing inputs)

Each value below was read by Claude directly from the named primary artifact in this session
(2026-11-03), independently of the 2026-10-27 review and of the literature-retrieval agent.
"AG-sheet" marks items on Avin's verification sheet. S8's isolated agent re-verifies all rows.

## A. Modified D–A parameters (Richard, Bénard & Chahine, Adsorption 15 (2009) 43–51)
Artifact: sources/richard2009a.pdf (DOI printed on p.43: 10.1007/s10450-009-9149-x — matches the repo's citation; the review's open DOI question is closed).
Table 3, p.48 (AG-sheet):
- H2 global fit (all isotherms): n_max 71.6 mol/kg; P0 1470 MPa; α 3080 J/mol; β 18.9 J/(mol·K); Va 0.00143 m³/kg.
- H2 reduced fit (77 K + 298 K only, footnote a): n_max 65.4; P0 1090 MPa; α 3310; β 16.8; Va 0.00138.
  NOTE: the v0.2 review scripts used the reduced set with Va left at 1.43e-3; the correct reduced Va is 1.38e-3 — use it in S5.
- Fig. 1a (p.48): H2/AX-21 excess isotherms at 30, 35, 40, 45, 60, 77, 93, 113, 153, 213, 298 K, 0–6 MPa.
  Data source per caption: Bénard & Chahine 2001. Fit quality statement (p.48): avg rel. deviation 2.2% at 77 K, 8.8% at 153 K for P > 0.1 MPa.

## B. Bénard & Chahine, Langmuir 17 (2001) 1950–1955 (DOI 10.1021/la001381x)
Artifact: project file la001381x.pdf (full text read).
- NO numeric isotherm tables; data exist only as figures → dual digitization of Richard Fig. 1a stands (D3).
- AX-21: SSA 2800 m²/g; bulk density 0.3 g/cm³; DFT pore width sharply peaked at 12.5 Å (±~1 Å half-width).
- Isosteric heat 6.4 → 5.0 kJ/mol over 0–12 mmol/g (citable anchor for the q_st band, closes minor 5's citation need).
- Ono–Kondo fit: EA ≈ 4 kJ/mol, E ≈ 0.4 kJ/mol, ρmax 65 mol/L.

## C. DOE / U.S. DRIVE targets (Target Explanation Document, updated May 2017)
Artifact: usdrive2017 PDF (Avin's Downloads: fcto_targets_onboard_hydro_storage_explanation.pdf). Verified by the 2026-10-27 referee (report minor 4) and by the literature agent; AG-sheet confirms.
- System gravimetric: 0.045 / 0.055 / 0.065 kg H2/kg sys (2020 / 2025 / Ultimate).
- System volumetric: 0.030 / 0.040 / 0.050 kg H2/L sys.
- Capacities are USABLE, end-of-life (footnote a). Delivery pressure 5–12 bar abs; delivery T −40/85 °C; 1,500 cycles.

## D. HSECoE anchors (AG-sheet)
1. FY2011 APR ch. IV.D.1 (Anton), Table 1, Adsorbent column — artifact iv_d_1_anton_2011.pdf, read in full:
   GC 0.039 kgH2/kg_system; VC 0.024 kgH2/L. Adsorbent baseline: AX-21, 200 bar Type III vessel, MLVI jacket,
   5 W heat leak at 80 K, flow-through charging, in-tank resistance heater, external H2-warming HX.
   Loss of usable H2 0.44 g/h/kg.
2. ST044 2012 (Motyka, May 15 2012) — artifact st044_motyka_2012_o.pdf, read in full:
   - Slide 12 (Design #1, full 60 bar/40 K, empty ~5 bar/100–120 K):
     Powder MaxSorb/AX-21/Activated Carbon: m_sys 99.8 kg, V_sys 206.6 L, GC 0.0562 gH2/g_sys, VC 27.12 gH2/L_sys.
     Also: MOF-5 composite tank 74.6 kg / 180.6 L / 0.0751 / 31.01; MOF-5 Al tank 87.3 kg / 182.7 L / 0.0641 / 30.66.
     CAVEAT: the carbon row's tank type is not labelled on the slide (design narrative says Al 2:1); treat as secondary
     held-out case with this ambiguity disclosed.
   - Slide 17, row A ("Phase 1 Baseline — Activated Carbon in a Composite Tank; FT cooling + resistance heater;
     full 80 K, 200 bar"): GC 0.03665 gH2/g_sys, VC 22.65 gH2/L_sys. Row H: BOP mass+volume −25% → GC +8.4%, VC +3.9%.
3. ST044 2013 (presenter Tamburello, May 14 2013) — artifact st044_tamburello_2013_o.pdf, read in full:
   - Slide 18 spider table, "End of Phase 1 Baseline": GC 0.0312 gH2/g_sys; VC 0.0194 printed as "gH2/L_sys"
     (dimensionally a slide typo; read as kgH2/L = 19.4 g/L). Context bullets: Type 3 Al+CF vs Type 1; AX-21 vs MOF-5;
     200 vs 100 bar.
   - Slide 19 waterfall step A: "Phase 1 Baseline — Activated Carbon; Type 3 tank; Full at 80 K, 200 bar; FT cooling +
     generic resistance heater."
   - Slide 27, Powder MOF-5 HexCell system tank breakdown (context slide 17: 4.4:1 Type 1 Al tank, T_full 80 K,
     P_full 100 bar): Pressure vessel 62.45 kg / 23.45 L; LN2 channel 19.24 kg / 16.42 L; Insulation 8.01 kg / 67.84 L;
     Outer shell 15.35 kg / 5.77 L; Boss/plug/support rings 1.28 kg / 0.00 L; tank-only totals 106.33 kg / 303.36 L.
     Geometry: Lcyl 1.659 m; R1 0.1817 m; wall R2−R1 10.2 mm; LN2 channel R4−R2 6.8 mm; insulation R5−R4 25.4 mm;
     shell R6−R5 2.0 mm; D_tank 0.452 m; L_tank 1.990 m.
   - Slide 10: HSECoE powder MOF-5 D–A set: n_max 88 mol/kg; P0 3200 bar; α 2400 J/mol; β 11 J/(mol·K);
     Va 0.0019 m³/kg; Vv 0.0062 m³/kg; m 2.0; ρ_bulk 150 kg/m³; n_excess grav 0.056 kgH2/kg_ads; n_total vol 0.025 kgH2/L_ads.
   - Slide 28: BOP ≈ 44% of system cost; H2-conditioning HX + 2 pressure regulators ≈ 50% of BOP cost.
   - Report-to-report AX-21 spread (same nominal 80 K/200 bar composite-tank config): 0.039 (FY2011 APR) →
     0.03665 (2012 s17) → 0.0312 (2013 s18) — 21% relative span; disclosed and folded into gate tolerances (M1d, c3).
4. Purewal et al., IJHE 44 (2019) 15135–15145 — artifact IJHE_system_model.pdf, read in full:
   - System: single type-1 6061-T6 Al tank; MLVI 23 mm (10 mm demonstrated for CcH2); embedded LN2 cooling channels
     (3/8 in; 1/4 in an improvement option); honeycomb Al internal HX; 2 mm Al outer shell; BOP incl. on-tank valve,
     refueling receptacle, pressure regulator, FC-coolant H2-warming HX; full details in Tamburello FEDSM2017-69411.
   - Conservative full/empty: 100 bar/80 K → 5.5 bar/160 K; 5.6 kg usable; MOF-5 ρ_pack 0.13 g/cm³ conservative.
   - Compaction transfer: Y = 1 for ρ_pack/ρ_crys < 0.519; else Y = 1.32 − 0.616·(ρ_pack/ρ_crys); n*_max = Y·n_max,
     v*_a = Y·v_a (their Eqs. 5–6).
   - MOF-5 ρ_crys 0.605 g/cm³; max excess 60.0 g/kg at 77 K.
5. Ahluwalia & Peng, IJHE 34 (2009) 5476–5487 — artifact sources/anl-equivalent (chat file), read in full:
   - Netting analysis for geodesic winding (Vasiliev & Morozov ref), T700S CF 2550 MPa, 1600 kg/m³, SF 2.35,
     translation strength 82.5% @350 bar → 63% @700 bar (linear); liner Al 2024 2.4 mm; shell Al 2024 3 mm;
     MLVSI 28 layers/cm aluminized Mylar/Dacron, ρ 59.3 kg/m³, k_eff 5.2e-4 W/m·K, sized to 1 W through sheets
     (+1 W other paths); in-tank U-tube HX Al 2024 (9.5/11.9 mm tubes); 40-PPI Al foam 2 wt%;
     ex-vessel miscellaneous allowance 30 kg / 25 L; L/D 3; dormancy/vent model (Eqs. 13–16); AX-21 Ono–Kondo
     parametrization (Bénard & Chahine): E 0.4 kJ/mol, EA 4 kJ/mol, ρmax 130 kg/m³, Nmax(T) cubic.
6. Ahluwalia, Peng & Hua, IJHE 40 (2015) 6373–6390 — artifact sources/ahluwalia2015.pdf (AG-sheet crop):
   Table 9 (p.6388) Level-1 sorbent material targets: storage 100 bar / 155 K; discharge 5 bar; ΔT 60 K;
   peak excess at 77 K 190 g-H2/kg; excess at storage P,T 120 g-H2/kg; E1 5–7.5 kJ/mol; bulk density 420 kg/m³
   (→ 40 g/L system volumetric); bed k 1 W/m·K; usable fraction 95% (Level 2); Td 215 K.

## E. ANL-10/24 (Hua et al. report version) — artifact sources/anl1024_hua.pdf (81 pp, title page verified)
Compressed 350/700-bar Type IV tank assessment; to be mined in S4 for PF benchmarks, liner/BOP masses.

## F. HyCAN-DB interlock
Released data only (concept DOI 10.5281/zenodo.23231985; v0.1 version DOI ...986). The v0.1 Chahine-rule headline
is withdrawn by its author and must not be cited; dataset rows stand. Panella 2005 = HYC-0001
(DOI 10.1016/j.carbon.2005.03.037, Crossref-confirmed).

## G. Still unobtained
- NREL/MP-5400-73571 (HSECoE final report): nrel.gov link dead for both parties; research-hub.nrel.gov robots-blocked
  here. Not load-bearing (administrative/model-access report); cite with the MP number per the referee's
  research-hub verification; Avin can fetch from research-hub.nrel.gov if a referee asks.
- HSECoE adsorbent system models (HexCell/MATI): not on hsecoe.org or hymarc.org lists; HyMARC registration or
  SRNL contact would be needed — deferred unless S4 requires them.
- Paywalled, citation-only (no values quoted, Crossref-confirmed DOIs): Pasini 2012, Kucherenko 2012, Song 2016,
  Owen 2014, Ishigami 1990, Sircar 1999, Hardy 2012*, Paggiaro 2010* (*in Avin's Downloads as Elsevier files —
  identify by PII on first use: S0360319911028485 ≈ Hardy 2012, S0360319909017376 ≈ Paggiaro 2010; verify first page before quoting).
