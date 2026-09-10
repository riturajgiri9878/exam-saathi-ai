# Version 3.5 — Hard Question Consistency Fix

## What was wrong

Version 3.4 sent many prompts containing `calculate` and digits to the strict
single-expression JSON verifier. That verifier is appropriate for explicit arithmetic,
but not for chemistry and physics word problems. A valid diagnostic answer could
therefore be rejected before it appeared in the chat.

## What changed

- Only explicit arithmetic/exact-value expressions enter the deterministic verifier.
- Science word problems first receive a data, units, conservation-law and
  stoichiometry audit.
- Gemini code execution is attempted for hard calculations, with a compatible
  no-tool retry when it is unavailable.
- The tutor performs a second independent consistency pass before returning.
- Impossible and underdetermined questions are explained instead of forced into a
  numerical answer.

## Regression example

For `2A(g) ⇌ B(g) + C(g)` in a rigid closed vessel at constant temperature,
the reaction changes two moles of gas into two moles of gas. Starting from pure A at
1.0 atm, the reaction alone cannot make total pressure become 1.2 atm. Therefore the
given problem is inconsistent, and neither equilibrium partial pressure of A nor the
reverse rate constant is uniquely determined.

If the intended reaction was instead `A(g) ⇌ B(g) + C(g)` at constant volume, that is
a different, conditional problem. It would give `pA = 0.8 atm`, `pB = pC = 0.2 atm`,
and `kr = 0.04 atm^-1 s^-1` for the stated rate law. The app must label this as a typo
interpretation, never as the answer to the original question.
