# References

   | Key | Full citation | DOI or URL | Role in project | Date accessed |
   |-----|---------------|------------|-----------------|---------------|
   | DOE-TARGETS | U.S. DRIVE / DOE FCTO — Technical System Targets: Onboard Hydrogen Storage for Light-Duty Fuel Cell Vehicles | https://www.energy.gov/eere/fuelcells/doe-technical-targets-onboard-hydrogen-storage-light-duty-vehicles | System target levels (the requirement to beat) | 2026-06-16 |
   | AX21-DA | Richard, Benard & Chahine — modified Dubinin-Astakhov model, Part 1 | https://doi.org/10.1007/s10450-009-9149-x | Isotherm model + AX-21 parameters (Gate V2 anchor) | 2026-06-16 |
   | HSECoE-SYS | Thornton & Simpson — HSECoE Final Project Report (NREL/TP-5400-73571) | https://docs.nrel.gov/docs/fy19osti/73571.pdf | System-level GC/VC (Gate V3 anchor) | 2026-06-16 |
## Added in v0.2.0

| Key | Full citation | DOI or URL | Role in project | Date accessed |
|-----|---------------|------------|-----------------|---------------|
| HSECOE-ST044 | Tamburello, D. et al. (SRNL) — SRNL Technical Work Scope for the HSECoE: Design and Testing of Adsorbent Storage Systems. DOE Hydrogen and Fuel Cells Program 2013 Annual Merit Review, Project ID ST044 | https://www.hydrogen.energy.gov/docs/hydrogenprogramlibraries/pdfs/review13/st044_tamburello_2013_o.pdf | Gate V3 anchor: AX-21 full-state system GC/VC (slide 18) at 80 K / 200 bar (slide 19) | 2026-06-16 |
| ANL-10/24 | Hua, T.; Ahluwalia, R.; Peng, J.-K. et al. — Technical Assessment of Compressed Hydrogen Storage Tank Systems for Automotive Applications, ANL-10/24 (Argonne/TIAX) | https://publications.anl.gov/anlpubs/2010/09/68050.pdf | Vessel parameters: composite allowable stress, composite density, liner thickness, safety factor | 2026-08-17 |
| ST001 | Ahluwalia, R.; Hua, T.; Peng, J.-K.; Papadias, D.; Kumar, R. — System Level Analysis of Hydrogen Storage Options, DOE Hydrogen Program Review Project ID ST001 (2011) | https://www.hydrogen.energy.gov/docs/hydrogenprogramlibraries/pdfs/review11/st001_ahluwalia_2011_o.pdf | MLI effective conductivity and density, heat-leak budget, balance-of-system mass | 2026-08-18 |
| ST047 | Newhouse, N. — Development of Improved Composite Pressure Vessels for Hydrogen Storage, Hexagon Lincoln / DOE AMR Project ST047 (2013) | https://www.hydrogen.energy.gov/docs/hydrogenprogramlibraries/pdfs/review13/st047_newhouse_2013_o.pdf | Vessel performance-factor cross-check benchmark (100 bar Type IV, 735 bar·L/kg) | 2026-08-17 |
| DOE-CRYO-INSUL | Meneghelli, B.; Tamburello, D.; Fesmire, J.; Swanger, A. — Integrated Insulation System for Automotive Cryogenic Storage Tanks, DOE H2 & Fuel Cells Program FY2017 Annual Progress Report, Sec. IV.D.4, DE-EE0007649 | https://www.hydrogen.energy.gov/docs/hydrogenprogramlibraries/pdfs/progress17/iv_d_4_meneghelli_2017.pdf | Warm-boundary design temperature; corroborating <7 W heat-leak ceiling and the upper endpoint of the heat-leak uncertainty range | 2026-08-18 |
| ISHIGAMI | Ishigami, T.; Homma, T. — An importance quantification technique in uncertainty analysis for computer models. Proc. ISUMA '90, 398-403 (1990) | https://doi.org/10.1109/ISUMA.1990.151285 | Gate V4.2 test function. The closed-form indices used here are derived in `sensitivity.ishigami_analytic` and checked against brute-force quasi-Monte-Carlo rather than taken from this citation; confirming the derivation against the primary text is an open Mode B item | not yet accessed |
| HYCAN-DB | Gupta, A. — HyCAN-DB: a FAIR database of hydrogen sorption measurements in carbon nanomaterials, v0.1 | https://doi.org/10.5281/zenodo.23231985 | Companion dataset. Source of all seven carbon-nanotube papers in the case study | 2026-10-08 |

### Carbon-nanotube corpus

The seven primary papers behind the CNT case study are cited individually in
`data/materials/cnt_literature.yaml`, each with the verbatim sentence and page
its number came from, its measurement method, and what the paper does and does
not state. They are not duplicated here; that file is the authority. Two of the
seven print no DOI, and the file records that rather than supplying one.
