# Exam Saathi v5.4.0 — Direct Upload Guide

This release fixes the long-running-answer problem without depending on an always-on local PC.

## What changed

- Qwen 3 8B support through either Ollama or an OpenAI-compatible hosted endpoint.
- Qwen hidden thinking is disabled with `think: false` and `/no_think`.
- Qwen output is capped at 1,800 tokens and context at 4,096 tokens by default.
- One provider pass has a 30-second deadline and at most two provider attempts.
- The website has a 120-second final deadline, so a request cannot run forever.
- Whole-workflow retry is disabled by default to avoid repeating an expensive answer.
- Exact arithmetic, percentages, square roots and supported radical expressions use local SymPy first. They consume no Groq/Gemini/Qwen quota.
- Existing Groq, Gemini, NVIDIA NIM, OpenRouter, Cloudflare, Perplexity and OpenAI routing remains available.
- All 77 automated tests pass.

## Direct GitHub upload

1. Extract the ZIP supplied with this release.
2. Open your GitHub repository `exam-saathi-ai`.
3. Select **Add file → Upload files**.
4. Open the extracted folder and select every file and folder inside it.
5. Drag them into the GitHub upload page.
6. Wait until every file finishes uploading.
7. Enter commit message: `Exam Saathi v5.4.0 bounded Qwen and speed fix`.
8. Select **Commit changes**.
9. Render will start Auto-Deploy. If it does not, open Render → your service → **Manual Deploy → Deploy latest commit**.

Do not upload the ZIP itself to GitHub. Extract it and upload its contents.

## Render environment — safest default

No new Qwen variable is required. Leave these absent on Render unless you own a remotely reachable endpoint:

- `QWEN_OLLAMA_URL`
- `QWEN_API_URL`
- `QWEN_API_KEY`

Render cannot reach Ollama at `127.0.0.1:11434` on your Windows PC. Setting that URL on Render would point to Render's own container, not to your computer. With no Qwen endpoint configured, Exam Saathi skips Qwen immediately and uses the existing provider mesh.

## Optional local Windows Qwen mode

For running Exam Saathi on the same Windows computer as Ollama, set:

```text
QWEN_OLLAMA_URL=http://127.0.0.1:11434
QWEN_MODEL=qwen3:8b
```

The release already uses these safe defaults:

```text
QWEN_MAX_TOKENS=1800
QWEN_CONTEXT_TOKENS=4096
QWEN_TIMEOUT_SECONDS=45
ANSWER_PASS_TIMEOUT_SECONDS=30
ANSWER_MAX_PROVIDER_ATTEMPTS=2
ANSWER_UI_TIMEOUT_SECONDS=120
EXAM_GRAPH_MAX_RETRIES=0
```

You do not need to add those variables unless you want to override the defaults.

## Optional hosted Qwen mode

If a provider gives you a Qwen OpenAI-compatible endpoint, add these three Render variables:

```text
QWEN_API_URL=https://provider.example/v1/chat/completions
QWEN_API_KEY=your-provider-key
QWEN_HOSTED_MODEL=provider-model-name
```

Never paste a secret key into GitHub files.

## Important expectation

Qwen 3 8B on a 16 GB RAM, 4 GB GT 730 PC can be slow because much of the model runs on CPU. This release prevents endless thinking and repeated calls, but it cannot turn that older GPU into a modern inference GPU. Render should use hosted providers unless you intentionally expose a secure remote Qwen server.

## Quick verification after deployment

Ask these questions:

1. `2 + 5` — should answer almost instantly.
2. `Find the exact value of ((sqrt(18))/(sqrt(12)-sqrt(6)))^10` — should return `817209 + 577854 sqrt(2)` without an AI provider call.
3. A current-affairs question — should use a configured web-grounded provider and show verification status.

Engine version should display `v5.4.0`.

