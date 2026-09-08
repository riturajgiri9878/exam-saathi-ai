# Exam Saathi AI

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

- Original Colab MVP automated tests: 13 passed, 0 failed.
- Deployment package: cloud-ready Gradio application with Docker support.
