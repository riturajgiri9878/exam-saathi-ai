# Version 3.6 — Independent Science Examiner

Complex Chemistry and Physics questions now use two stages:

1. A tutor creates a detailed draft.
2. A separate examiner audits the problem and draft from scratch, then returns the
   corrected final answer as structured JSON.

The examiner explicitly checks carbon skeletons, functional groups, named qualitative
tests, reagent effects, stoichiometry, conservation laws, dimensions, units and data
sufficiency. For the cyclohexanol/ozonolysis/aldol/Grignard challenge, it must reject
the claim that a terminal methyl group alone guarantees an iodoform test and expose the
ketone-versus-aldehyde contradiction.

The second call is deliberately limited to long, multi-step science questions so that
ordinary questions remain fast. If the independent review cannot be completed, the app
blocks the unreviewed answer instead of presenting it as verified.
