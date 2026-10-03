# Exam Saathi v6.0.0 Architecture

```mermaid
flowchart TD
    Q[Student question / file / voice] --> V[Security + question validator]
    V --> R{Supervisor router}
    R -->|Safe calculation| S[SymPy local solver]
    R -->|Uploaded notes| L[LlamaIndex hybrid retrieval]
    R -->|Static subject| P[Healthy provider mesh]
    R -->|Current fact| W[Web-grounded provider + official sources]
    S --> G[Deterministic quality gate]
    L --> G
    P --> G
    W --> G
    G -->|Passed| A[Paragraph answer stream]
    G -->|Uncertain| H[Review needed label]
    A --> X[Fresh PDF + animated HTML]
    H --> X
    A --> F[Correct / Incorrect / Report]
    F --> D[Privacy-minimised feedback dataset]
```

## Cache rule

Only stable answers that passed a verification gate may be cached. Cache keys
include normalized full question, language, subject and engine version. Current,
high-risk and web-required questions are never cached.

## Monitoring rule

Structured logs exclude raw questions, answers and keys. LangSmith remains
optional and hides student input/output unless an administrator explicitly
changes that privacy setting.
