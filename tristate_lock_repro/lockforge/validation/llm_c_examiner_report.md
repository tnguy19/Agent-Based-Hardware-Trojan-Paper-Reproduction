# LLM-C (Examiner) - Claude Haiku, code-only access (reproduced from the agent's hand-back report)

True/False examination (10 paper-grounded statements written by LLM-A; key hidden from LLM-C):

| id | LLM-C answer | key | match | evidence given by LLM-C |
|----|---|---|---|---|
| T1 | True | True | yes | locking.py:lock_netlist (key_idx nxt,nxt+1) |
| T2 | False | False | yes | keygates.py:tri_mode, tri_correct_key |
| T3 | False | False | yes | locking.py:_apply_tri (unk = buf_en & inv_en) |
| T4 | True | True | yes | keygates.py:TRI_TYPES |
| T5 | True | True | yes | lock_netlist + netlist.COMPLEMENT |
| T6 | True | True | yes | run_experiments.py:run_circuit |
| T7 | True | True | yes | run_experiments.py:main defaults |
| T8 | False | False | yes | metrics.py (primary coverage = any over all trials) |
| T9 | True | True | yes | nets_half = nets_full[:K25] |
| T10 | False | False | yes | insertion.candidates; lock_netlist raises on PI |

**Examination accuracy 10/10 (threshold 8/10): PASS.**
LLM-C's holistic 1-10 fidelity score was **6**; it attributed this to (a) benchmarks absent from the isolated package so the quick run cannot pass, (b) 4-largest subset not in run_experiments.py (it is in analyze.py), (c) no unit tests for B8/B9 in the package (they exist in tests/ and lockforge/evaluate_bcsrp.py, not shipped to the examiner), (d) Hi-Z as random constant (documented choice), (e) missing duplicate assertion (fixed). Note this holistic score is below 8; the LockForge pass criteria are the Judge score (>= 8) and T/F accuracy (>= 8/10).

## Process incident (also in AGENT_LOG.md)
LLM-C reported it had mistakenly created a scheduled message ("placeholder", trigger trig_01TGttNeZizFLcJQnUzCMHbj, due 2026-11-15T14:04Z) via a scheduling tool; its own delete attempt was denied. It was NOT deleted by the main agent (a subagent's request does not substitute for user approval) and is surfaced to the user.
