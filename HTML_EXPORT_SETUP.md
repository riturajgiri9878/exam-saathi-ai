# HTML Study Guide export

## Install this update

1. Back up your currently deployed source files.
2. Upload ALL files in the update ZIP into the existing repository root, not the ZIP itself.
3. Keep existing Render username, password and Gemini API key unchanged. No new key is needed.
4. Deploy the new commit and check that Render reports Live.
5. Process a PDF. Open Low Data & Share, enter a title, and select Include original diagram pages.
6. Press Create Complete HTML Guide, then download the returned HTML.
7. Open it in Chrome/Edge/Safari. Turn off internet and check notes, cards, source images and zoom.
8. Use Print / Save as PDF for a printable copy. Browser PDF output may have different pagination.

## Scope and privacy

The guide uses the current structured analysis: notes, formulas, topic ranking, cards, MCQs,
original source-page previews and filenames/page numbers. It does not re-run OCR and does not
copy the Generative AI reference guide's subject matter into unrelated PDFs.
Images are embedded JPEGs: no side folder, login or API key is required to open the export.
The image budget is 18 MiB before base64 encoding. Missing/over-budget images are reported.
Text-only mode removes images. No external fonts, scripts, analytics or CDN resources are loaded.

Anyone receiving the file can read its notes, answers and embedded page images. These page
images can contain handwriting or personal details. Review before sharing. Login protects the
online app, not the downloaded HTML. Voice, AI chat, persistent streaks and OCR are not offline
features. Formulas retain source notation; this version does not bundle a LaTeX renderer.
Language-converted Markdown currently shown in the app is not automatically copied into this
export: export uses the source analysis notes. The existing source references remain attached.

## Verification

Run `python -m unittest test_study_export.py` and `python -m py_compile app.py core.py study_features.py study_export.py`.
Live Render deployment and a real Gemini call still need to be checked on your configured service.
