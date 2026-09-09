# Version 2.5: class teacher and paper evidence

Upload every file in this update ZIP to the existing repository root. Preserve
Render credentials and Gemini settings. Deploy and check the version banner.

## Class teacher
Process today's notes in Secure Upload, then open आज की क्लास समझाओ.
Select a language; type a doubt or record and transcribe it. Press Explain.
Answer the understanding-check question and press Check my answer for feedback.
Start a fresh explanation after changing documents. The teacher retrieves at most
four relevant chunks, so it is not a complete long-document coverage guarantee.
Original diagrams remain available in Smart Notes.

## Previous-paper evidence
Process class notes separately in Secure Upload. In Previous Papers, fill the
board/university, class, stream/degree/semester, subject and syllabus version.
Upload papers from ONE year and one matching profile at a time. Add them to the
catalog, change year and repeat. Select the target exam year and prioritize notes.
Metadata is user-supplied, not independently verified. Papers in the preceding
ten years are counted by distinct year. Sample papers do not enter the ranking.
Exact phrase matching provides transparent baseline evidence, but can miss
synonyms, translated topics and OCR errors. Marks/question-type weighting is not
implemented. This changes existing note/topic order, not missing-topic detection.

## What remains
The paper catalog is session-only. No nationwide paper corpus is bundled and
no national ten-year coverage is claimed. Durable storage, verified ingestion,
source rights checking, administrator curation, syllabus mapping and automatic
question/marks analysis require a separate production data service.
These two modules are the first implementation stage, not that completed corpus.

## Verification
Python compilation and isolated metadata/year-window/deduplication checks passed.
Gemini teacher and Render UI require testing in the configured live environment.
