# Version 4.0 — One-Time Deployment and Acceptance Check

## Deploy once

1. Extract the cumulative ZIP locally.
2. In the GitHub repository, upload every file from inside the extracted folder.
3. Commit with `Deploy Exam Saathi v4.0 visual study packs`.
4. Wait for Render to complete the Docker build and show `Live`.
5. Hard-refresh the app with `Ctrl + Shift + R`.
6. Confirm the header says `Version 4.0 — Verified Visual Study Packs`.

No new environment variable is required. Existing Gemini API, model and login variables
remain unchanged. The Docker build adds Noto fonts so Indian-language PDF text renders
instead of becoming empty squares.

## Acceptance checks

1. Ask the charged-ring oscillation question. Confirm the force sign is negative, the
   ring mass is excluded because the ring is fixed, equations render, and both downloads
   appear.
2. Ask the organic Iodoform/Grignard challenge. Confirm an inconsistent problem is not
   forced into one structure.
3. Ask an Atacama climate question. Confirm the response avoids claims that El Nino is
   required for every flood and that a climate diagram appears in both downloads.
4. Ask a volcano question. Confirm the PDF contains a labelled static volcano and the
   HTML contains moving smoke/lava.
5. Select Hindi or another Indian language and, if Auto classification is uncertain,
   choose the subject manually. Confirm the answer and PDF text remain readable.
6. Enable cited online verification for a factual question. Confirm links are appended;
   uploaded PDFs or private note content must never be included in that search request.

## Honest reliability boundary

No AI can guarantee a perfect answer to every possible question. Version 4.0 improves
reliability with deterministic arithmetic checks, subject rubrics, an independent second
examiner for complex questions, optional cited web verification and explicit ambiguity
handling. Students should still verify high-stakes answers and source claims.
