# Exam Saathi AI — Version 4.1 Source-Supported Geography Visuals

Start with [V3_0_START_HERE.md](V3_0_START_HERE.md) for the current update,
deployment steps, detailed HTML download and validation limits. Full Chapter
mode adds ordered source processing, stories, concept diagrams, short/long model
answers and resumable batches. Existing features below remain available.

Version 3.1 reliability patch uses one source section per Gemini request,
removes the extra language-check API call, and displays a safe reason when a
batch stops. The Teaching language dropdown remains the output-language control.

Version 3.2 upgrades Previous Papers with question-level extraction, ten-year
coverage and missing-year reporting, source-page evidence, distinct-year/topic
frequency, and a portable catalog that can be saved and restored. See
[V3_2_PREVIOUS_PAPERS.md](V3_2_PREVIOUS_PAPERS.md).

Version 3.3 adds a prominent Quick Question Solver at the top of Secure Upload.
Students can type one Mathematics, Physics, Chemistry or general study question,
press Enter, and receive a step-by-step answer without uploading a document.
The selected Indian language controls the answer, and follow-up questions retain
the recent conversation.

Version 3.4 adds independent numeric verification. For calculation questions,
Gemini must return the interpreted original expression and claimed final value in
a restricted calculator syntax. The server evaluates both at 50-digit precision.
A mismatch is rejected and regenerated once; a second mismatch shows an error
instead of placing an unverified result in the student's chat.

Version 3.5 fixes hard science word-problem routing. A question containing the word
"calculate" is no longer automatically treated as one arithmetic expression. The
solver first audits stoichiometry, conservation laws, units, assumptions, data
consistency and whether the requested unknowns are uniquely determined. It can use
Gemini code execution when available, retries without the tool for compatibility, and
must identify an impossible or underdetermined problem instead of inventing a number.

Version 3.6 adds a separate second-pass science examiner for complex Chemistry and
Physics prompts. It independently checks carbon/functional-group continuity, named
tests, reagents, stoichiometry, conservation laws, dimensions and units. The reviewed
answer replaces the first draft, and an incomplete review is blocked. Quick Solver chat
bubbles are also forced to a readable light palette in browser dark mode.

Version 3.7 enforces KaTeX-compatible `$$...$$` equations in Quick Solver, converts
accidental fenced math blocks before display, and explicitly configures Gradio's math
delimiters. Complex electrostatics and magnetism problems now enter the independent
science review, which checks signed force direction, units, dimensions, square roots
and agreement between the working and final formula.

Version 4.0 turns every Quick Solver response into a downloadable visual lesson. The
app detects the subject, generates a safe labelled diagram, creates a colorful static
A4 PDF and a separate animated offline HTML file, and keeps both downloads beside the
answer. Standard PDFs are intentionally static because common PDF readers do not
reliably support animation; the HTML carries motion without needing an account, API key
or internet connection after download. Volcano, coastal-climate, charged-ring and cell
questions receive dedicated diagrams; other subjects receive a structured concept map.

Version 4.1 fixes political-geography packs end to end. Doubly-landlocked questions
are now classified as Geography and receive a dedicated Uzbekistan-neighbour diagram
instead of the generic concept map. A clearly appended student answer is hidden from
the question panel for active recall, recognised factual packs include readable source
links, unsupported packs are labelled reviewed rather than verified, and diagram images
are compressed before PDF embedding for substantially smaller downloads.

Complex Biology, Geography, History, Civics, Economics and Literature questions now
join Physics and Chemistry in the independent examiner workflow. Factual questions can
optionally receive cited online-source verification; this is off by default to avoid
sending a student's question to an external search service without consent.

## Version 2.0 features

- 10–60 minute last-minute exam sprint with priority topics, notes, formulas and questions.
- Tap-to-reveal flashcards and active-recall MCQ practice with session XP and weak-topic tracking.
- Diagram gallery using original PDF pages plus a hide/reveal diagram challenge.
- Microphone question transcription and source-grounded answers in Hinglish, Simple Hindi or Exam English.
- Batch notebook scanning for up to 10 PDFs/images, including image auto-crop and enhancement.
- Smart revision planner, low-data revision pack and downloadable private friend quiz HTML.
- Required private login through Render environment variables.

Current MVP boundaries: flashcards use buttons instead of a touch-swipe gesture; progress is session-only;
friend sharing creates a downloadable HTML quiz rather than a hosted public URL; and low-data mode is
lightweight in-app output rather than a fully installable offline PWA. The microphone removes the need to
type, while spoken answer playback (TTS) is planned for a later release.

Exam Saathi now keeps important source diagrams alongside Smart Notes. Gemini
identifies useful diagram pages, while the app renders the original PDF page so
handwritten labels, formulas and arrows are not redrawn or changed. If a preview
cannot be rendered, text extraction and notes continue instead of failing.

Exam Saathi is a secure, source-based Agentic AI study assistant. A student can
upload a digital PDF, scanned PDF, or camera image and receive important topics,
complete revision notes, practice questions, semantic-search results, and
evidence-based previous-paper trends.

## Working pipeline

1. Validate file type, signature, size, password state, and page count.
2. Extract digital PDF text or use Tesseract OCR as a fallback.
3. Calculate OCR confidence and allow Human-in-the-Loop correction.
4. Clean text while preserving filename and page metadata.
5. Create overlapping word chunks.
6. Rank topics with TF-IDF.
7. Rank complete notes with TF-IDF and MiniLM sentence embeddings.
8. Generate source-linked short, long, and MCQ practice questions.
9. Route requests through the Supervisor to Notes, Quiz, Trend, or Retrieval agents.
10. Review output and apply security guardrails and recovery plans.

## Project files

- `app.py` - Gradio interface and agent orchestration.
- `core.py` - security, PDF/OCR, NLP, embeddings, search, notes, and questions.
- `study_features.py` - exam sprint, flashcards, active recall, planner, session progress, diagram challenge and sharing.
- `reports/` - verified demo outputs and previous-paper trend evidence.
- `sample_data/` - original demonstration PDFs and camera image.
- `requirements.txt` - Python dependencies.
- `packages.txt` - system OCR dependencies for supported hosting platforms.
- `Dockerfile` - container configuration for Google Cloud Run or another container host.
- `Dockerfile.render` and `render.yaml` - lightweight Plan B configuration for Render Free.
- `PLAN_B_RENDER.md` - exact Plan B notes and limitations.

## Run locally

Install Tesseract OCR and its English/Hindi language packs first. Then run:

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:7860`.

## Run with Docker

```bash
docker build -t exam-saathi .
docker run --rm -p 8080:8080 -e PORT=8080 exam-saathi
```

Open `http://127.0.0.1:8080`.

## Deploy to Google Cloud Run

From the project directory, after authenticating the Google Cloud CLI:

```bash
gcloud run deploy exam-saathi --source . --region asia-south1 --allow-unauthenticated
```

Cloud Run builds the included Dockerfile and returns the service URL after a
successful deployment. Review billing, region, memory, timeout, and access
settings before serving real users.

## Security and privacy

- Allows PDF, PNG, JPG, and JPEG only.
- Maximum upload size is 10 MB; maximum PDF length is 50 pages.
- Blocks malformed and password-protected PDFs.
- Verifies uploaded images before OCR.
- Masks email addresses and Indian mobile numbers in agent requests.
- Blocks common prompt-injection instructions and rate-limits requests.
- Does not intentionally save uploaded documents to the project repository.
- Sends recorded microphone audio to Gemini only after the student requests transcription.
- Friend quiz exports exclude the original PDF and contain generated practice content plus source references.
- Keeps XP/progress only in the current browser session.
- Uses Plan B TF-IDF recovery mode if the embedding model cannot load.
- Includes verified reports for degraded-mode demonstration.

For a production student service, add authentication, encrypted object storage,
a managed database, malware scanning, consent controls, retention/deletion jobs,
centralized logs, monitoring, backups, and a formal incident-response process.

## Prediction disclaimer

Trend scores are evidence-based revision priorities calculated from the supplied
historical question dataset. They are not guaranteed predictions of future exam
questions.

## Current status

- Version 2.0 source compiles successfully and the pure study-mode feature tests pass.
- Deployment package: Render-ready Gradio application with Docker support.

## Render update checklist

Upload or commit all changed files together: `app.py`, `core.py`, `study_features.py`,
`requirements-render.txt`, `requirements.txt`, `render.yaml`, and `README.md`. Keep these Render
environment variables configured: `REQUIRE_AUTH=true`, `EXAM_SAATHI_USERNAME`,
`EXAM_SAATHI_PASSWORD`, and `GEMINI_API_KEY`. Never put their secret values in GitHub.
