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