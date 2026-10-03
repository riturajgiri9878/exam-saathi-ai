# Exam Saathi v6.0.0 — Production Hardening

This release keeps the v5.4.1 UI and adds ten quality controls:

1. deterministic fast route for supported calculations and curated facts;
2. progressive paragraph display plus immediate progress events;
3. evidence-based verification labels instead of a blanket 100% claim;
4. conservative question validation before provider use;
5. subject-specific deterministic post-checks;
6. runtime health scoring and provider cooldown/fallback;
7. normalized SHA-256 answer cache that excludes current facts;
8. GitHub Actions regression and hardening tests;
9. privacy-safe structured logs and optional LangSmith tracing;
10. Correct / Incorrect / Report feedback saved as JSONL.

## Repository layout

Upload the contents of `UPLOAD_TO_GITHUB` to the repository root, and also copy
the sibling `TESTS` directory to repository root so GitHub Actions can run it.

## Important truthfulness rule

`LOCALLY_VERIFIED` means deterministic code checked the calculation.
`VERIFIED` means the configured evidence gates passed. `REVIEW_NEEDED` means the
answer may still be useful but was not independently established. No label is a
promise that every possible question is error-free.

## Feedback persistence on Render

Set `EXAM_SAATHI_DATA_DIR` to a mounted persistent-disk directory if feedback
must survive restarts. Without a persistent disk, feedback is session-instance
data and may disappear after a redeploy.
