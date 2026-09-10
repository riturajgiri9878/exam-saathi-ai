# Exam Saathi 3.3 - Quick Question Solver

## What students get

At the top of Secure Upload, students now see a Quick Question Solver. They can
type one question and press Enter or `Solve step by step`. No PDF is required.
The answer stays in a chat panel so they can ask a follow-up question.

The solver detects Mathematics, Physics, Chemistry or another study subject.
It asks Gemini for subject-appropriate working:

- Mathematics: interpreted expression, valid transformations, arithmetic check
  and an exact final value when requested.
- Physics: known/required values, formula, substitution, units, dimensional
  check and assumptions.
- Chemistry: concept or reaction, readable equations/structures, reagents and
  conditions, mechanism/reasoning and explicit ambiguity.
- Other subjects: clear ordered reasoning and a final takeaway.

The existing Indian-language dropdown controls the output. Recent messages are
kept for follow-up questions. `New question` clears the panel.

## Install

Upload these files from the v3.3 ZIP into the GitHub repository root, replacing
files with the same names:

1. `app.py`
2. `quick_solver.py` (new)
3. `README.md`
4. `V3_3_QUICK_SOLVER.md`
5. `test_quick_solver.py` (offline regression tests)

Commit, wait for Render to become Live, then hard-refresh the application. The
banner should show `Version 3.3 - Quick Solver + Full Chapter Learning`.

## Test question

Paste this into Quick Question Solver:

`Find the exact value of (sqrt(18)/(sqrt(12)-sqrt(6)))^10`

The correct simplification is `sqrt(6) + sqrt(3)`, and the expected exact final
answer is `817209 + 577854 sqrt(2)`.

The live wording can differ because Gemini generates the explanation. Model
access, quota and response quality still depend on the Render Gemini settings.
This workspace had no Gemini key, so the live provider response was not tested.
The direct solver flow, prompt contract, history, selected language, error
handling and existing project behavior passed 19 offline automated checks.
