# References

Every DOI below was confirmed against the Crossref REST API (the returned
title matched the cited work) or, for reports and slide decks without DOIs,
the document itself was fetched and its identity verified on the title
page/slide, on the dates given. Values quoted from these sources in `data/`
carry the quote's location in that file's `_source` field. The S8 reference
audit re-verifies every row against its PDF.

## Primary data and model sources

| Key | Full citation | DOI / URL | Role | Verified |
|---|---|---|---|---|
| RICHARD-2009-I | Richard, M.-A.; Bénard, P.; Chahine, R. Gas adsorption process in activated carbon over a wide temperature range above the critical point. Part 1: modified Dubinin-Astakhov model. *Adsorption* 15 (2009) 43–51 | 10.1007/s10450-009-9149-x | Modified D–A model; AX-21 Table 3 parameter sets; Fig. 1a is the digitized multi-temperature dataset | 2026-11-03 (DOI printed on paper; Crossref) |
| RICHARD-2009-II | Richard, M.-A.; Bénard, P.; Chahine, R. … Part 2: conservation of mass and energy. *Adsorption* 15 (2009) 53–63 | 10.1007/s10450-009-9150-4 | Companion energy-balance formulation (isosteric-heat context) | 2026-11-03 (Crossref) |
| BENARD-2001 | Bénard, P.; Chahine, R. Determination of the adsorption isotherms of hydrogen on activated carbons above the critical temperature… *Langmuir* 17 (2001) 1950–1955 | 10.1021/la001381x | Source of the Fig. 1a measurements; AX-21 properties (2800 m²/g, 0.3 g/cm³, DFT pore width); isosteric heat 6.4→5.0 kJ/mol (q_st anchor band); no numeric isotherm tables (digitization necessity) | 2026-11-03 (full text read) |
| PANELLA-2005 | Panella, B.; Hirscher, M.; Roth, S. Hydrogen adsorption in different carbon nanostructures. *Carbon* 43 (2005) 2209–2214 | 10.1016/j.carbon.2005.03.037 | SWCNT 77 K/298 K isotherms (Fig. 2b, dual-digitized); same-apparatus AC reference; HyCAN-DB HYC-0001 | 2026-11-03 (Crossref; full text) |
| DOE-TARGETS-2017 | U.S. DRIVE Partnership. Target Explanation Document: Onboard Hydrogen Storage for Light-Duty Fuel Cell Vehicles (updated May 2017) | energy.gov …/fcto_targets_onboard_hydro_storage_explanation.pdf | System targets (usable, end-of-life): Ultimate 0.065/0.050, 2025 0.055/0.040, 2020 0.045/0.030; delivery 5–12 bar, −40/85 °C; author-verified against the PDF | 2026-11-03 |

## HSECoE and Argonne system anchors

| Key | Full citation | DOI / URL | Role | Verified |
|---|---|---|---|---|
| TAMBURELLO-2017 | Tamburello, D.; Hardy, B.; Corgnale, C.; Sulic, M.; Anton, D. Cryo-adsorbent hydrogen storage systems for fuel cell vehicles. *Proc. ASME FEDSM2017*, FEDSM2017-69411 (manuscript SRNL-STI-2017-00079) | 10.1115/FEDSM2017-69411 | E1 calibration case (Table 5 HexCell and MATI specifications; Table 2 MOF-5 parameter sets); BOP component inventory (Table 3) | 2026-11-03 (Crossref; manuscript read) |
| PUREWAL-2019 | Purewal, J.; Veenstra, M.; Tamburello, D.; Ahmed, A.; Matzger, A.; Wong-Foy, A.; Seth, S.; Liu, Y.; Siegel, D. Estimation of system-level hydrogen storage for metal-organic frameworks with high volumetric storage density. *IJHE* 44 (2019) 15135–15145 | 10.1016/j.ijhydene.2019.04.082 | Full-scale type-1 system description (MLVI, embedded LN2 channels, shell, BOP); usable TPS basis; compaction transfer function | 2026-11-03 (full text read) |
| AHLUWALIA-2009 | Ahluwalia, R. K.; Peng, J. K. Automotive hydrogen storage system using cryo-adsorption on activated carbon. *IJHE* 34 (2009) 5476–5487 | 10.1016/j.ijhydene.2009.05.023 | Netting-analysis sizing, SF 2.35, T700S properties, liner/shell gauges, MLVSI properties, 30 kg/25 L BOP anchor, dormancy/vent model, recoverable-capacity framing | 2026-11-03 (full text read) |
| AHLUWALIA-2015 | Ahluwalia, R. K.; Peng, J. K.; Hua, T. Q. Sorbent material property requirements for on-board hydrogen storage for automotive fuel cell systems. *IJHE* 40 (2015) 6373–6390 | 10.1016/j.ijhydene.2015.03.025 | Argonne Level-1 sorbent targets (Table 9: 120 g/kg excess at 100 bar/155 K; 420 kg/m³; peak 190 g/kg at 77 K); requirement-in-observables precedent | 2026-11-03 (full text read; author-verified) |
| HARDY-2018 | Hardy, B.; Tamburello, D.; Corgnale, C. Hydrogen storage adsorbent systems acceptability envelope. *IJHE* 43 (2018) 19528–19539 | 10.1016/j.ijhydene.2018.08.140 | The Adsorbent Acceptability Envelope: prior inverse construction this project's maps are compared against | 2026-11-03 (manuscript SRNL-STI-2018-00196 read) |
| HARDY-2012 | Hardy, B.; Corgnale, C.; Tamburello, D.; Garrison, S.; Anton, D. et al. Modeling of adsorbent based hydrogen storage systems. *IJHE* 37 (2012) 5691–5705 | 10.1016/j.ijhydene.2011.12.125 | HSECoE adsorbent detailed-model formulation | 2026-11-03 (Crossref) |
| ST044-2012 | Motyka, T. et al. (SRNL). SRNL technical work scope for the HSECoE…, DOE AMR 2012, ST044 | hydrogen.energy.gov …/review12/st044_motyka_2012_o.pdf | Anchors: slide 17 baseline 0.03665/0.02265 (80 K/200 bar); slide 12 carbon row 99.8 kg/206.6 L (60 bar/40 K) — gate E2 case H3; author-verified | 2026-11-03 |
| ST044-2013 | Tamburello, D. et al. (SRNL). …Design and testing of adsorbent storage systems, DOE AMR 2013, ST044 | hydrogen.energy.gov …/review13/st044_tamburello_2013_o.pdf | End-of-Phase-1 baseline 0.0312/0.0194 (slides 18–19; the printed "gH2/Lsys" read as kg/L, a slide typo); slide 27 tank component table; slide 10 MOF-5 parameters; slide 25 HexCell structure datum; author-verified | 2026-11-03 |
| APR-2011 | Anton, D.; Motyka, T. Hydrogen Storage Engineering Center of Excellence. FY2011 DOE Hydrogen and Fuel Cells Program Annual Progress Report, ch. IV.D.1 | hydrogen.energy.gov …/progress11/iv_d_1_anton_2011.pdf | Adsorbent column Table 1: 0.039/0.024 anchors; 5 W heat-leak budget; baseline configuration; author-verified | 2026-11-03 |
| HSECOE-FINAL | Hydrogen Storage System Modeling: Public Access, Maintenance, and Enhancements. NREL/MP-5400-73571 (2019) | nrel.gov/docs/fy19osti/73571.pdf | HSECoE model-access report (the v0.2 file cited it as TP- and as the Gate V3 anchor; both corrected — the anchor is ST044) | number per research-hub.nlr.gov; PDF unreachable from this session's networks, title corroborated by OSTI 1572650; flagged for the S8 audit |
| ANL-10-24 | Hua, T. Q.; Ahluwalia, R. K.; Peng, J.-K. et al. Technical assessment of compressed hydrogen storage tank systems… ANL-10/24 (2010); journal version *IJHE* 36 (2011) 3037–3049 | 10.1016/j.ijhydene.2010.11.090 | Composite quality knockdown; superseded v0.2 vessel parameters (record) | 2026-11-03 (Crossref; report held) |
| ST001-2011 | Ahluwalia, R. et al. System level analysis of hydrogen storage options. DOE AMR 2011, ST001 | hydrogen.energy.gov …/review11/st001_ahluwalia_2011_o.pdf | MLI k_eff/density; slide 26: 16 kg miscellaneous BOP mass + 10 L miscellaneous volume, stated as fixed assumptions of the MOF-5 on-board analysis (type-3 CF tank, storage design point 150 atm, vent 187.5 atm — slides 12/26/27). The v1.0 model's placement of this anchor at 100 bar design-class was a mis-assignment found by the S8 audit after gate E2 was adjudicated; see the correction record in docs/validation_plan.md (gate verdict unaffected) | 2026-11-03 (corrected; was 2026-08-18 v0.2 record) |
| ST047-2013 | Newhouse, N. Development of improved composite pressure vessels… DOE AMR 2013, ST047 | hydrogen.energy.gov …/review13/st047_newhouse_2013_o.pdf | Performance-factor cross-check benchmark (735 bar·L/kg, 100 bar Type IV) | 2026-08-17 (v0.2 record) |
| MENEGHELLI-2017 | Meneghelli, B.; Tamburello, D.; Fesmire, J.; Swanger, A. Integrated insulation system for automotive cryogenic storage tanks. FY2017 APR IV.D.4 | hydrogen.energy.gov …/progress17/iv_d_4_meneghelli_2017.pdf | <7 W heat-leak ceiling corroboration | 2026-08-18 (v0.2 record) |

## Prior materials-to-system and requirements literature

| Key | Full citation | DOI | Role | Verified |
|---|---|---|---|---|
| CORGNALE-2012 | Corgnale, C.; Hardy, B.; Tamburello, D.; Garrison, S.; Anton, D. Acceptability envelope for metal hydride-based hydrogen storage systems. *IJHE* 37 (2012) 2812–2824 | 10.1016/j.ijhydene.2011.07.037 | Origin of the acceptability-envelope method | 2026-11-03 (SRNL-TR-2011-00211 read) |
| PASINI-2012 | Pasini, J. M.; van Hassel, B. A.; Mosher, D. A.; Veenstra, M. J. System modeling methodology and analyses for materials-based hydrogen storage. *IJHE* 37 (2012) 2874–2884 | 10.1016/j.ijhydene.2011.05.169 | HSECoE system-modelling framework | 2026-11-03 (Crossref) |
| PASINI-2013 | Pasini, J. M.; Corgnale, C.; van Hassel, B. A.; Motyka, T.; Kumar, S.; Simmons, K. Metal hydride material requirements for automotive hydrogen storage systems. *IJHE* 38 (2013) 9755–9765 | 10.1016/j.ijhydene.2012.08.112 | Requirements-inversion precedent (hydrides); arXiv:1307.0890 | 2026-11-03 (Crossref; arXiv abs) |
| AHMED-2017 | Ahmed, A. et al. Balancing gravimetric and volumetric hydrogen density in MOFs. *Energy Environ. Sci.* 10 (2017) 2459–2471 | 10.1039/c7ee02477k | Usable-capacity material screening | 2026-11-03 (Crossref) |
| AHMED-2019 | Ahmed, A. et al. Exceptional hydrogen storage achieved by screening nearly half a million metal-organic frameworks. *Nat. Commun.* 10 (2019) 1568 | 10.1038/s41467-019-09365-w | Large-scale TPS usable-capacity screening | 2026-11-03 (Crossref) |
| ALLENDORF-2018 | Allendorf, M. et al. An assessment of strategies for the development of solid-state adsorbents for vehicular hydrogen storage. *Energy Environ. Sci.* 11 (2018) 2784–2812 | 10.1039/c8ee01085d | Sorbent development-strategy review | 2026-11-03 (Crossref) |
| GOLDSMITH-2013 | Goldsmith, J.; Wong-Foy, A.; Cafarella, M.; Siegel, D. Theoretical limits of hydrogen storage in metal-organic frameworks… *Chem. Mater.* 25 (2013) 3373–3382 | 10.1021/cm401978e | Chahine-rule surface-area scaling constant | 2026-11-03 (Crossref) |
| YANG-2010 | Yang, J.; Sudik, A.; Wolverton, C.; Siegel, D. High capacity hydrogen storage materials… *Chem. Soc. Rev.* 39 (2010) 656–675 | 10.1039/b802882f | Material- vs system-level target framing | 2026-11-03 (Crossref) |
| BHATIA-2006 | Bhatia, S.; Myers, A. Optimum conditions for adsorptive storage. *Langmuir* 22 (2006) 1688–1700 | 10.1021/la0523816 | Optimal-enthalpy/temperature-regime precedent | 2026-11-03 (author copy read) |
| MYERS-2014 | Myers, A.; Monson, P. Physical adsorption of gases: the case for absolute adsorption… *Adsorption* 20 (2014) 591–622 | 10.1007/s10450-014-9604-1 | Excess vs absolute; the v_a ambiguity | 2026-11-03 (author copy) |
| SIRCAR-1999 | Sircar, S. Gibbsian surface excess for gas adsorption — revisited. *Ind. Eng. Chem. Res.* 38 (1999) 3670–3682 | 10.1021/ie9900871 | Excess-adsorption thermodynamics | 2026-11-03 (Crossref) |
| DUBININ-1989 | Dubinin, M. M. Fundamentals of the theory of adsorption in micropores of carbon adsorbents… *Carbon* 27 (1989) 457–467 | 10.1016/0008-6223(89)90078-X | D–A origin reference (short version: *Pure Appl. Chem.* 61 (1989) 1841, 10.1351/pac198961111841) | 2026-11-03 (Crossref; PAC version read) |
| SDANGHI-2020 | Sdanghi, G.; Canevesi, R.; Celzard, A.; Thommes, M.; Fierro, V. Characterization of carbon materials for hydrogen storage and compression. *C* 6 (2020) 46 | 10.3390/c6030046 | Recent review of carbon H2 storage characterization | 2026-11-03 (Crossref; open access) |
| PAGGIARO-2010 | Paggiaro, R.; Bénard, P.; Polifke, W. Cryo-adsorptive hydrogen storage on activated carbon. I… *IJHE* 35 (2010) 638–647 | 10.1016/j.ijhydene.2009.10.108 | Cryo-adsorption vessel thermodynamics precedent | 2026-11-03 (Crossref) |

## CNT corpus (notebook example only; the case study was dropped per the pre-registered rule)

| Key | Full citation | DOI | Verified |
|---|---|---|---|
| TIBBETTS-2001 | Tibbetts, G.; Meisner, G.; Olk, C. Hydrogen storage capacity of carbon nanotubes, filaments, and vapor-grown fibers. *Carbon* 39 (2001) 2291–2301 | 10.1016/S0008-6223(01)00051-3 | 2026-11-03 (Crossref) |
| ZHOU-2004 | Zhou, L.; Zhou, Y.; Sun, Y. A comparative study of hydrogen adsorption on superactivated carbon versus carbon nanotubes. *IJHE* 29 (2004) 475–479 | 10.1016/S0360-3199(03)00092-2 | 2026-11-03 (Crossref) |
| WANG-2002 | Wang, Q.; Zhu, C.; Liu, W.; Wu, T. Hydrogen storage by carbon nanotube and their films under ambient pressure. *IJHE* 27 (2002) 497–500 | 10.1016/S0360-3199(01)00162-8 | 2026-11-03 (Crossref) |

The remaining CNT-corpus papers are cited individually in
`data/materials/cnt_literature.yaml` with verbatim source sentences; that
file is the authority for them.

## Methods

| Key | Full citation | DOI | Role | Verified |
|---|---|---|---|---|
| RAUE-2009 | Raue, A. et al. Structural and practical identifiability analysis of partially observed dynamical models by exploiting the profile likelihood. *Bioinformatics* 25 (2009) 1923–1929 | 10.1093/bioinformatics/btp358 | Profile-likelihood method | 2026-11-03 (Crossref) |
| GUTENKUNST-2007 | Gutenkunst, R. et al. Universally sloppy parameter sensitivities in systems biology models. *PLoS Comput. Biol.* 3 (2007) e189 | 10.1371/journal.pcbi.0030189 | Sloppiness framework; Fisher spectrum | 2026-11-03 (Crossref) |
| SONG-2016 | Song, E.; Nelson, B.; Staum, J. Shapley effects for global sensitivity analysis: theory and computation. *SIAM/ASA JUQ* 4 (2016) 1060–1083 | 10.1137/15M1048070 | Shapley-effect estimator for dependent inputs | 2026-11-03 (Crossref) |
| OWEN-2014 | Owen, A. Sobol' indices and Shapley value. *SIAM/ASA JUQ* 2 (2014) 245–251 | 10.1137/130936233 | Shapley–Sobol relationship | 2026-11-03 (Crossref) |
| KUCHERENKO-2012 | Kucherenko, S.; Tarantola, S.; Annoni, P. Estimation of global sensitivity indices for models with dependent variables. *Comput. Phys. Commun.* 183 (2012) 937–946 | 10.1016/j.cpc.2011.12.020 | Dependent-input sensitivity (alternative estimator) | 2026-11-03 (Crossref) |
| SALTELLI-2010 | Saltelli, A. et al. Variance based sensitivity analysis of model output… *Comput. Phys. Commun.* 181 (2010) 259–270 | 10.1016/j.cpc.2009.09.018 | Estimator behind the superseded v0.2 Sobol study (record) | 2026-11-03 (Crossref) |
| ISHIGAMI-1990 | Ishigami, T.; Homma, T. An importance quantification technique in uncertainty analysis for computer models. *Proc. ISUMA '90*, 398–403 | 10.1109/ISUMA.1990.151285 | v0.2 Gate V4.2 test function (record; the closed form used was derived in-code and checked by quasi-Monte-Carlo) | 2026-11-03 (Crossref; the paper itself remains unread — disclosed) |
| FOREMAN-MACKEY-2013 | Foreman-Mackey, D.; Hogg, D.; Lang, D.; Goodman, J. emcee: the MCMC hammer. *PASP* 125 (2013) 306 | 10.1086/670067 | Posterior sampler used | 2026-11-03 (software's own citation) |
| BELL-2014 | Bell, I.; Wronski, J.; Quoilin, S.; Lemort, V. …CoolProp. *Ind. Eng. Chem. Res.* 53 (2014) 2498–2508 | 10.1021/ie4033999 | EOS library used | 2026-11-03 (Crossref) |
| LEACHMAN-2009 | Leachman, J.; Jacobsen, R.; Penoncello, S.; Lemmon, E. Fundamental equations of state for parahydrogen, normal hydrogen, and orthohydrogen. *JPCRD* 38 (2009) 721–748 | 10.1063/1.3160306 | The reference EOS behind the wrapper and the NIST tables | 2026-11-03 (NIST reprint read) |
| HERMAN-2017 | Herman, J.; Usher, W. SALib: an open-source Python library for sensitivity analysis. *JOSS* 2 (2017) 97 | 10.21105/joss.00097 | Library used in the superseded v0.2 Sobol study (record) | 2026-11-03 (PDF held) |
| HYCAN-DB | Gupta, A. HyCAN-DB: a FAIR database of hydrogen sorption measurements in carbon nanomaterials, v0.1 | 10.5281/zenodo.23231985 | Companion dataset (data rows only; its v0.1 analysis headline is withdrawn by its author and is not cited) | 2026-10-08 |
| PREREG-2026 | Gupta, A. H2STAR v1.0: pre-registration of validation gates, tolerances, calibration/validation split, and analysis plan. Zenodo (2026) | 10.5281/zenodo.23931242 | The frozen plan this repository executes | 2026-11-03 (published record verified) |
