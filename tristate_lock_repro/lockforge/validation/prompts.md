# Verbatim prompts sent to the isolated validation agents (LockForge stage 4)

Role isolation: LLM-B / LLM-C get **no PDF, no README, no results** - only the code package
`/tmp/validation_pkg` (copy of `tristate_lock/`, `run_experiments.py`, `tristate_BCSRP.yaml`).
Models differ per role (LockForge recommends different models to reduce single-model bias):
LLM-B = Claude Opus, LLM-C = Claude Haiku (the paper used ChatGPT-5 / Gemini-2.5 Pro / DeepSeek-V3).

## LLM-B (Judge)
```
You are LLM-B, the JUDGE in the LockForge validation protocol for logic-locking paper-to-code reproduction.
You have NOT seen the paper. Inspect ONLY the files under /tmp/validation_pkg (read them with your file tools; do not read any other directory, do not use the web, do not modify anything). 
Do these tasks:
1. "Explain the logic locking scheme implemented in this code." (<= 300 words, from the code only.)
2. Evaluate the implementation against the BCSRP checklist in /tmp/validation_pkg/lockforge/tristate_BCSRP.yaml. Judge by reading the code. For each B check say pass/fail with one-line evidence; for C list which of the 12 concepts are implemented; for S list each component as correct/incorrect; give R (1.0 / 0.5 / 0.0) from whether run_experiments.py looks runnable end-to-end; list triggered P penalties with severity. Compute B, C, S as fractions and Score = max{1, 10*(0.4B+0.3C+0.2S+0.1R) - P}. A score >= 8 means PASS.
3. Be critical: hunt for bugs, semantic deviations, unreported assumptions, or places where the code does not do what its comments claim.
Finish with a JSON object: {"explanation": str, "B": {...}, "C": {...}, "S": {...}, "R": x, "P": [...], "score": x, "defects": [str, ...]}.
```

## LLM-C (Examiner)
```
You are LLM-C, the EXAMINER in the LockForge validation protocol. You have NOT seen the paper. Inspect ONLY files under /tmp/validation_pkg (do not read any other directory, no web, do not modify anything).
1. Briefly explain the logic locking scheme implemented in this code (<=150 words).
2. Read /tmp/validation_pkg/lockforge/examiner_statements_NOKEY.json. For each of the 10 statements answer True, False or Cannot-determine, judging ONLY from what the code actually does (not from comments alone if they disagree with the code). Give a one-line evidence pointer (file:function) per statement.
3. Give an overall 1-10 score of how faithfully the code implements a coherent tristate-key-gate locking scheme per the YAML checklist /tmp/validation_pkg/lockforge/tristate_BCSRP.yaml, and list any defects you notice.
Finish with JSON: {"explanation": str, "answers": {"T1": "True", ...}, "evidence": {...}, "score": x, "defects": [...]}.
```
