# Exam Saathi 3.4 - Verified Math

## Problem fixed

The earlier Quick Solver could produce a correct method followed by a wrong
arithmetic sum. In the reported example it added the irrational coefficients as
`2370` instead of `2378`, producing `575910 sqrt(2)` instead of the correct
`577854 sqrt(2)` coefficient after multiplication.

## New calculation gate

For numeric questions containing signals such as exact value, calculate,
evaluate, simplify, square root, `sqrt` or LaTeX radicals/fractions:

1. Gemini is instructed to use its Python code-execution tool.
2. It returns detailed teaching steps separately from two calculator fields:
   the complete interpreted original expression and its claimed exact result.
3. Exam Saathi parses only a restricted arithmetic language: numbers, `+`, `-`,
   `*`, `/`, integer powers, parentheses and non-negative `sqrt(number)`.
   Arbitrary Python code, attributes, variables and imports are rejected.
4. Both expressions are evaluated independently with 50-digit decimal precision.
5. A mismatch triggers one fresh calculation with the mismatch values supplied.
6. If the second result still fails, no solution is added to chat. The student
   receives a verification error and can retry.
7. A passing response gets a separate `Calculator-verified final answer` line.

## Regression example

Question:

`Find the exact value of (sqrt(18)/(sqrt(12)-sqrt(6)))^10`

Verified result:

`817209 + 577854*sqrt(2)`

The reported wrong value `817209 + 575910*sqrt(2)` is explicitly included in
the regression tests and must be rejected.

## Scope

This deterministic gate checks numeric equality of supported expressions. It
does not prove every explanatory sentence, geometry proof, symbolic expression
with free variables, chemistry mechanism or factual answer. Those still require
careful model prompting, source evidence where available, and teacher review for
high-stakes use.
