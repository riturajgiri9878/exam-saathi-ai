# Exam Saathi v6.0.0 Test Report

Date: 2026-10-03 UTC

## Result

- Python compilation: PASS
- Gradio application import/build: PASS
- Regression + production-hardening suite: **82/82 PASS**
- External provider calls during tests: none required

## New controls covered

- empty/current/inconsistent question validation;
- SHA-256 cache isolation and current-fact cache exclusion;
- provider health success/failure scoring;
- subject-specific step/visual checks;
- privacy-minimised JSONL human feedback;
- exact local arithmetic and radical calculation;
- provider fallback/cooldown and bounded attempts;
- geography-specific diagram routing;
- LlamaIndex retrieval fallback;
- LangGraph retry/human-review flow;
- PDF/animated HTML artifact uniqueness;
- chat-first interface and progressive answer frames.

## Important limitation

These tests establish software behavior, not universal correctness of every
future model answer. Current affairs still require working live sources, and
ambiguous/high-stakes questions may correctly be labelled `REVIEW_NEEDED`.
