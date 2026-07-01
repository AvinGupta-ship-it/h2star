# H2STAR — AI Usage Log

## 2026-06-30 — Day 2 concepts and excess/absolute derivation
Tool: Claude (chat)
Purpose: Learn the four §5.3 concepts; derive the excess/absolute relation; get journal templates.
What I provided: The H2STAR manual (§5.3, §5.4, §3.4C) and my Day-2 deliverable list.
What it produced: Concept explanations, a line-by-line walkthrough of the derivation,
  and journal/log templates with examples.
What I verified: I derived the excess/absolute relation myself on paper and confirmed it
  matches §3.4C; I cross-checked the key concept claims against NIST (hydrogen's 33 K
  critical temperature and the 77 K/100 bar real-gas density, the latter matching my Day-0
  CoolProp check) and the manual's §3.4D literature band for the 4–7 kJ/mol isosteric heat.
What I changed/owned: I wrote all four concept summaries and the derivation in my own words;
  no scientific content was taken verbatim from the AI.

## 2026-06-30 - EOS wrapper (Gate V1)
Tool: Claude Code (implementer session)
Purpose: Implement eos.py + test_eos.py + notebook 01 + viz parity fn from Prompt CC-2.
What I provided: The CC-2 spec plus the exact NIST-CSV format and directory constraints.
What it produced: src/h2star/eos.py, tests/test_eos.py, notebooks/01_eos_validation.ipynb,
  a parity function in src/h2star/viz.py, and a pytest marker registration in pyproject.toml.
What I verified: Read every line of eos.py and test_eos.py focusing on unit handling
  (bar->Pa conversion, P/T argument order, 'Hydrogen' species, 'D' vs 'Dmolar'); ran
  `ruff` and the validation tests myself; confirmed the NIST tables are normal hydrogen.
What I changed: none

## 2026-06-30 — Day 4: Gate V1 execution
Tool: Claude (chat, Opus) — planning/instruction only; no code-generation session.
Purpose: Convert Execution Manual §5.4/§3.8/§3.10 into an unambiguous Day 4 checklist (kernel setup, figure generation, verdict recording).
What I provided: The frozen H2STAR manual and my Day 1–3 repo state.
What it produced: Paste-ready terminal commands, a .vscode/settings.json fix, a throwaway max-relative-error script mirroring test_eos.py's logic, and templates for the validation_plan verdict, journal, and this log.
What I verified: Ran every command in my own h2star venv; confirmed pytest -m validation → 4 passed and the measured max error (0.031%) independently via the script; eye-checked F1 against the parity line; cross-checked the ideal-gas density anchor (31.49 kg/m³) by hand. The Gate V1 verdict, its tolerance, and all interpretive prose are mine.
What I changed: Wrote the validation_plan verdict, journal entry, and Day-0 correction in my own words; no AI text was pasted into any provenance file.

## 2026-07-01 — Day 5 (Week 1 review) planning
Tool: Claude (chat; Opus 4.8)
Purpose: Turn manual §5.4/§5.7 into a step-by-step Day-5 review checklist; rehearse §5.3 concepts
  (supercritical adsorption; excess vs. absolute) for the spoken self-check.
What I provided: The H2STAR manual, the Days 0–4 state, and my required instruction style.
What it produced: The Day-5 task sequence, the §5.7 QC status-table structure, concept rehearsal
  rubrics, and journal/log templates. No code; no scientific decisions.
What I verified: Ran every QC command myself and read each result; confirmed CI green on GitHub;
  authored the weekly review and this log in my own words; checked both concept explanations against
  §5.3 and §3.4C, not the chat's summary alone.
What I changed: none
