# Agent interaction log

Documentation of the AI-agent work required by the assignment: prompts, errors, refinements.
All agents are Claude models. Roles follow LockForge (Saha et al., arXiv:2511.18531):

| LockForge role | Who | Access |
|---|---|---|
| LLM-A coder | main agent (Claude Sonnet 5.5) | paper PDF, web, shell |
| LLM-B judge | sub-agent, Claude Opus | code-only package |
| LLM-C examiner | sub-agent, Claude Haiku | code-only package |

## 1. The task prompt (user)

> "help me do this assignment: Use AI agents to reproduce the selected paper using the lockforge paper framework (paper attached) please reproduce the paper and also do: Source code and experimental results. A README explaining your implementation and how to run it. Documentation of your agent interactions, including prompts, errors, and refinements. The paper that I have chosen to reproduce I have also uploaded here 'Logic Locking: Exploration of a New Key-Gate Based on Tristate Logic'; use the lockforge paper on how to reproduce the logic locking paper."

Only the tristate paper PDF was actually attached (see error E02).

## 2. LockForge stages as executed

| Stage | What was done | Artefact |
|---|---|---|
| Forethought | Read PDF (text + rendered pages for figures); prompts "Read the paper and explain the logic locking scheme in it briefly" and "list the crucial concepts" answered by LLM-A; 12 concepts | `lockforge/01_forethought.md` |
| Implementation | Python package + experiment runner; smoke tests | `tristate_lock/`, `run_experiments.py` |
| Refinement loop - content mining | BCSRP checklist in YAML (schema copied from the real LockForge artifact repo) | `lockforge/tristate_BCSRP.yaml` |
| Refinement loop - local execution | automated B/S/R checks + score formula | `lockforge/evaluate_bcsrp.py`, `local_execution_report.json` |
| Validation - judging | LLM-B summarises + scores the code against the YAML without the paper | `lockforge/validation/llm_b_judge_report.md` |
| Validation - examination | LLM-A wrote 10 paper-grounded T/F statements (key hidden); LLM-C answered from code only | `lockforge/validation/llm_c_examiner_report.md` |

Score formula used: `Score = max{1, 10·(0.4B + 0.3C + 0.2S + 0.1R) − P}`, pass ≥ 8; T/F pass ≥ 8/10.

## 3. Prompts sent to other agents (verbatim in `lockforge/validation/prompts.md`)

* **LLM-B (Opus)**: "You are LLM-B, the JUDGE … You have NOT seen the paper. Inspect ONLY the files under /tmp/validation_pkg … 1. 'Explain the logic locking scheme implemented in this code.' 2. Evaluate … against the BCSRP checklist … compute B, C, S and Score … 3. Be critical: hunt for bugs …"
* **LLM-C (Haiku)**: "You are LLM-C, the EXAMINER … 1. Briefly explain … 2. … answer True, False or Cannot-determine for each of the 10 statements, judging ONLY from what the code actually does … 3. overall 1-10 score …"
* Isolation: the package contained only `tristate_lock/*.py`, `run_experiments.py` and the YAML (no README, no results, no paper, no benchmarks).
* Web/search prompts by LLM-A: LockForge paper and repo, SKG-Lock+ (FpLL details), FLL description, benchmark hosting.

## 4. Errors, dead ends and refinements (chronological)

| # | What happened | Cause | Resolution |
|---|---|---|---|
| E01 | Assignment received | - | - |
| E02 | LockForge PDF not in uploads | user attached only the tristate paper | web-searched LockForge (arXiv 2511.18531), read its HTML, cloned its public artifact repo to copy the real BCSRP YAML structure; recorded as a process limitation |
| E03 | Fig. 3 and Fig. 5 not in extracted text; the 8 benchmark names appear only in Fig. 5 | figures are images | rendered PDF pages to PNG and read them; confirmed key-gate types against Table I and the text |
| E04 | `curl` to ISCAS hosting sites → 403 (proxy allowlist) | sandbox network policy | did not circumvent; anonymous git clone of `ispras/hdl-benchmarks` (public) gave ISCAS-85 `.bench` + MCNC `.blif`; gate counts matched published ISCAS-85 counts |
| E05 | FLL / "improved FpLL" / Hi-Z-UNK simulation not specified | paper cites only | FpLL details recovered from SKG-Lock+ (open access); FLL re-implemented from descriptions; assumptions listed in README |
| E06 | Output coverage defined two ways | paper text vs SKG-Lock+ formula | pre-registered the literal text (D1) as primary, also report per-key (D2) and max-HD (D3) |
| E07 | **Plain FpLL gave ≈14 % corruptibility on c1908 vs ≈47 % for FLL** | probability propagation is blind in XOR logic (p stays 0.5) | FpLL+ attempt 1 (coverage-aware greedy on one-shot ranking): still ≈12 % (masking: flips cancel in XOR trees). Attempt 2 (one-shot ranking as pool + masking-aware greedy inside it): 26 % on the quick run. Kept as a *documented interpretation*, not tuned further toward the paper's numbers |
| E08 | **Bug caught by own BCSRP evaluator**: assertion `len(nets)==len(behaviours)` failed | FpLL+ returned 61 of 88 key-gates on apex4 (skip-equal-score rule exhausted the pool); the main experiment had silently used a smaller budget for that one case | relaxed skip rule when the pool is short; added hard assertion in `run_experiments.py` (every selection must return exactly 5 % of gates); reran all 840 runs |
| E09 | First Fig. 5 render: legend over bars, then legend over title; label over a marker | layout | moved legend to a figure-level row, adjusted label offset; viewed the PNGs |
| E10 | SAT scenario "family-aware attacker" recovers the function | analysis, not bug | kept as a reported observation, with the caveat that it is a single-seed supplement |
| E11 | Judge (Opus) flagged: FLL docstring over-claims re-ranking; prefix claim false for FpLL+; impact measure differs from Rajendran's; 256 vs 512 vectors; BLIF gate-count inflation; no duplicate-net assertion | real documentation/robustness gaps | fixed docstrings, set equivalence check to 512 vectors, added duplicate-location assertion, documented the rest; reran tests (11/11) and all experiments (results unchanged, 0 equivalence failures) |
| E12 | Judge could not run on benchmarks (package had none) → R = 0.5; Examiner's holistic score 6/10 | isolation design; its list of "defects" included this | accepted and reported honestly; the pass criteria (Judge 9.15, T/F 10/10) are met, holistic 6/10 is reported too |
| E13 | **Process incident**: the Haiku examiner reported it had mistakenly created a scheduled message (`placeholder`, trigger `trig_01TGttNeZizFLcJQnUzCMHbj`, 2026-11-15T14:04Z) and that its delete was denied; it asked the main agent to delete it | sub-agent used a scheduling tool outside its brief | **not deleted** by the main agent: a sub-agent's request does not carry user approval; surfaced to the user in the final message so the user can delete or ignore it |

## 5. Quantitative trace of the validation

| Check | Value | Threshold |
|---|---|---|
| Local execution (self-assessed) B/C/S/R/P | 1/1/1/1/0 → 10.0 | ≥ 8 (not independent) |
| LLM-B judge | 9.15 | ≥ 8 → pass |
| LLM-C T/F | 10/10 (T2, T3, T8, T10 correctly identified as false from code) | ≥ 8/10 → pass |
| LLM-C holistic | 6/10 | informational |
| Unit tests | 11/11 | - |

## 6. What this process did and did not buy

* The BCSRP loop and the isolated judge found real problems (the apex4 budget bug; over-claiming docstrings) that I had not noticed while coding.
* It does not validate the *scientific* match with the paper: the examiner statements test whether code and paper agree on structure, not on numbers. Numerical agreement is reported separately in the README (and is only partial).
* All roles are Claude models; the original framework recommends different model families to limit shared blind spots.
* Raw, unedited event notes are in `docs/_agent_log_draft.md`.

## 7. If this were repeated

1. Ask for the LockForge PDF up front (or accept the arXiv version explicitly).
2. Ship benchmarks (or a fetch script) inside the validation package so the judge can run R.
3. Pre-register the coverage definition and insertion-algorithm choices *and* a tolerance for "reproduced" before running.
