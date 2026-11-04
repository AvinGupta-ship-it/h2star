# Cover letter — submission to *Adsorption*

Dear Editors,

Please consider the enclosed manuscript, "Single-isotherm non-identifiability
of modified Dubinin–Astakhov parameters and the statement of system-level
hydrogen-storage requirements in observable quantities," for publication in
*Adsorption* as an original research article.

The paper asks a statistical question underneath a translation this community
uses constantly — from system-level hydrogen-storage targets to required
sorbent properties via the modified Dubinin–Astakhov model — namely, which
parameter combinations a single published excess isotherm actually
determines. Using a dual-digitized, uncertainty-tagged reconstruction of the
classic AX-21 dataset and profile likelihoods under an errors-in-pressure
measurement model, we show that one 77 K isotherm of ordinary published
quality leaves the parameter vector practically non-identifiable (a 3.8-fold
95% range in n_max), that seven supercritical isotherms fitted jointly
restore identifiability almost completely, and — the practical point — that
the loose single-isotherm region nonetheless pins system-level predictions
to a few per cent. The model is sloppy in the sense of Gutenkunst et al., so
requirements stated as isotherm parameters are conditional on a ridge the
data do not resolve, and we argue they belong in observable axes
(deliverable excess uptake and packing density), following the Argonne
sorbent targets' practice of stating requirements in measured quantities —
the HSECoE acceptability envelope, by contrast, states its requirements
partly in the fitted n_max itself, which is exactly the ridge-conditional
parameter.

Three aspects may interest your referees in particular:

1. The engineering model's calibration and held-out validation were frozen
   by an externally time-stamped pre-registration (Zenodo DOI
   10.5281/zenodo.23931242) before the model code existed. The held-out gate
   failed on one of four comparisons, and the paper's claims are narrowed by
   the pre-registered fork rule rather than by post-hoc judgment. We believe
   reporting a pre-registered negative engineering result alongside the
   statistical findings is itself useful to the field.
2. Every number in the manuscript is compiled from a machine-generated macro
   file, and a repository test fails if manuscript and regeneration
   disagree. All data, code and analysis records are open
   (github.com/AvinGupta-ship-it/h2star, archived on Zenodo).
3. The uncertainty attribution uses Shapley effects over the joint material
   posterior and declared engineering inputs, which to our knowledge has not
   been applied to cryo-adsorbent system models.

AI use in the research workflow is disclosed in the Methods section and
documented in the repository; the author takes full responsibility for all
content.

This manuscript is not under consideration elsewhere. A preprint will be
posted on ChemRxiv.

Suggested referees: [AVIN: 3–4 names — natural candidates are researchers
active on D–A modelling of cryo-adsorption, HSECoE system modelling, or
adsorption UQ; to be chosen by you, avoiding conflicts.]

Sincerely,
Avin Gupta
[AVIN: affiliation line]
iamavingupta@gmail.com
