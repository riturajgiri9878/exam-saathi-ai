# Deployment Checklist

## Before deployment

- [ ] Keep `Exam_Saathi_AI_Final_MVP.ipynb` as the development backup.
- [ ] Keep `Exam_Saathi_Final_Backup.zip` as the verified data backup.
- [ ] Review every file inside this deployment package.
- [ ] Do not commit API keys, passwords, student data, or `.env` files.
- [ ] Create a new private Git repository for the first deployment test.

## Cloud configuration

- [ ] Select a billing-enabled Google Cloud project.
- [ ] Enable Cloud Run, Cloud Build, and Artifact Registry APIs.
- [ ] Use the `asia-south1` region when appropriate for Indian users.
- [ ] Start with at least 2 GiB memory because the embedding model loads at runtime.
- [ ] Set a practical request timeout for OCR and model cold starts.
- [ ] Decide whether the service is public or requires authentication.

## Functional checks

- [ ] Upload a valid digital PDF.
- [ ] Upload a scanned image and review OCR confidence.
- [ ] Edit OCR text and approve it.
- [ ] Verify topic, notes, question, trend, and retrieval tabs.
- [ ] Confirm filename and page citations.
- [ ] Confirm prompt injection is blocked.
- [ ] Test the interface on a mobile browser.

## Production hardening

- [ ] Add user authentication and authorization.
- [ ] Store files in encrypted object storage with automatic deletion.
- [ ] Store metadata and audit records in a managed database.
- [ ] Add antivirus/malware scanning before document processing.
- [ ] Add centralized logs, latency/error metrics, alerts, and backups.
- [ ] Publish privacy, consent, retention, and deletion policies.
