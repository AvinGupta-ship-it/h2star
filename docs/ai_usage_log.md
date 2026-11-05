# AI-use disclosure

Tool: Anthropic Claude (2026 releases), used under the project's
version-controlled execution manual and the externally deposited,
DOI-stamped pre-registration (10.5281/zenodo.23931242).

Scope: model and analysis implementation, figure digitization and
reconciliation, literature retrieval and DOI checks, documentation and
manuscript drafting, execution of the pre-registered gates, and independent
verification passes (re-derivation, reference audit, adversarial review)
run as isolated instances with no access to the generating session's work.
AI tools were not used to create or alter any primary data; the digitized
datasets carry both extraction routes' raw readings.

Responsibility: all commits are authored by the repository owner, who
verified the load-bearing inputs against primary sources, ratified every
pre-registered decision (gate targets, tolerances, fork rule), and holds
sole scientific responsibility for every claim.
`docs/author_signoff_checklist.md` gates submission; the dated author
sign-off entry is added below on completion.

Record: the contemporaneous session-by-session log is preserved verbatim at
`docs/history/ai_usage_log_full.md`, outside the claim surface like the
progress journal; the git history is the complete record.

## Author sign-off — 2026-11-05

I have read and approved the compiled manuscript (final revision pass,
2026-11-04). I have read the S8 verification reports (independent
re-derivation, reference audit, adversarial review rounds 1 and 2), which
were provided to me directly and are summarized with their correction
records in docs/validation_plan.md. The five primary-source checklist items
were verified against papers I supplied; I reviewed and confirmed those
records (2026-11-05), including the Ahluwalia & Peng provenance correction
(the 30 kg/25 L balance-of-plant block is stated as pressure-independent;
the committed sensitivity variant covers it, no verdict changes) and the
NREL report number dropped per the checklist's fallback. I confirm the five
README Findings as my own conclusions. Affiliation: Texas Academy of
Mathematics and Science, University of North Texas. For the preprint: no
external funding to declare for this independent project, no competing
interests, suggested referees not applicable. Changes made during my
verification: provenance texts in data/engineering_v1.yaml and
docs/references.md (commit 83ab753) and the affiliation line (commit
6dba41d).

— Avin Gupta
