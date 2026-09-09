# Exam Saathi 3.0 — Full Chapter Learning

## Version 3.1 reliability fix

If the page shows `0/4 partial`, install the small Version 3.1 patch. It sends
one source section per model request, removes the second language-verification
request that could fail after a successful lesson response, relaxes unreliable
space-based word counting for Indian scripts, and shows a safe failure reason.
The same 34,790-character sample becomes 12 smaller resumable requests. More
progress steps are expected and do not mean content was duplicated.

The Teaching language dropdown controls the generated language. Typing “Hindi
mein” while the dropdown still says Hinglish does not change it; select Hindi.

This update fixes the short-answer path used by Understand Today's Class and
adds its detailed lesson to the downloaded HTML. It is a code handoff, not a
claim that the Render deployment or Gemini account has been tested live.

## What changed

- Full Chapter mode processes all extracted document text in ordered batches,
  instead of selecting four search chunks and limiting the answer to 1,200 tokens.
- Each topic requests a story, definition, explanation steps, worked example,
  concept diagram, memory tip, limitations, takeaways and a check question.
- Short and long practice questions include model answers. Long questions also
  include an answer outline. Importance means relevance to the supplied lesson;
  it does not mean a guaranteed exam prediction or verified past-paper frequency.
- Concept diagrams are responsive HTML cards/arrows, not generated photographs.
  Original extracted source images remain available in the gallery and export.
- Screen and HTML use the same detailed lesson renderer. HTML answers expand on
  click and work offline. It also includes the existing revision tools.
- Completed batches stay in session state. Build / Resume retries the unfinished
  part when the notes, selected language and request are unchanged.
- New notes invalidate the old lesson. A partial lesson is explicitly marked.
- Export failures retain the completed lesson. All generated text is HTML-escaped.

## Upload the update, step by step

1. Extract this ZIP on your computer.
2. Open your existing `exam-saathi-ai` GitHub repository.
3. Choose Add file → Upload files.
4. Upload the extracted files into the repository ROOT, where `app.py` already
   lives. Do not upload the ZIP itself or create a nested project folder.
5. Include ALL Python modules. In particular `chapter_teacher.py` is new and
   must accompany the updated `app.py` and `study_export.py`.
6. Commit the update. Your existing auto-deploy setup can deploy that commit.
7. Keep existing Render login credentials and Gemini environment variables.
   This update does not replace credentials or require sharing them in chat.
8. Wait for the new deployment to report Live, then open the application.
9. The banner should say `Version 3.0 — Full Chapter Learning`.

If browser uploading fails, replace `app.py` and `study_export.py` using GitHub's
file editor and create `chapter_teacher.py` with Add file → Create new file.
Use the COMPLETE file contents from this ZIP; do not append them to old code.
Keep all the other supplied modules from the existing version in place.

## Get the detailed lesson and HTML

1. Open Understand Today's Class.
2. Upload PDF/HTML/photos/text, or paste your notes in the text box.
3. Press the corresponding Process button and wait for its confirmation.
4. Select the teaching language. Generated explanations use this selection;
   navigation labels stay in English and original source snippets keep their language.
5. Leave the optional teaching request empty for the whole chapter, or describe
   where you want extra explanation. This preference does not narrow the source input.
6. Press Build / Resume Full Chapter.
7. Keep the page open. Each completed batch appears with progress. A long chapter
   takes multiple model requests and may take several minutes.
8. Read the Source coverage section. “Complete” means all extracted source
   sections were processed, not that OCR or AI explanations are guaranteed perfect.
9. Open short/long questions to reveal model answers.
10. Download using `Download this detailed lesson as HTML` immediately below the
    lesson. This uses the chosen teaching language automatically.
11. Alternatively use Low Data & Share → Create Complete HTML Guide. Select the
    SAME language as the detailed lesson to reuse it. If you want another language,
    rebuild the lesson in that language first.

Resume survives an API failure within the same active session, but not a server
restart or lost browser session. Download the partial guide before leaving.

## Validation completed

- 12 offline automated tests passed: full text partitioning, all-batch routing,
  partial-result retention/resume, language cache invalidation, invalid references,
  short/long question requirements, safe HTML, stale-source rejection, embedded
  images, missing-image handling and UI state retention when export fails.
- All Python files compile.
- The supplied 34,790-character notes were routed without losing a character:
  12 sections, four batches. That test used a fake provider and does NOT validate
  the actual generated teaching quality.
- SDK parameter names checked against the official Google Gen AI Python SDK docs:
  https://googleapis.github.io/python-genai/

## Live checks still required

The working environment has no Gemini key. Runtime dependency installation was
blocked, and the browser refused the local preview URL. Therefore live Gemini
quality, full Gradio runtime behavior, responsive visual appearance and Render
deployment are NOT verified here.

After deploying, use the assessment chapter to check that the lesson includes:
test, measurement, assessment, evaluation; nominal/ordinal/interval/ratio scales;
teacher-made/standardized tests; placement/formative/diagnostic/summative;
norm/criterion reference; and CCE. Check examples, source references, language,
diagram labels and model answers before using it with students.

Longer output uses more API tokens than the old summary. The provider uses your
configured primary model and at most one configured fallback. Model availability,
quota, pricing and latency depend on your account. A 404/503 can still stop a batch;
successful earlier batches remain available. This update does not grant model access.

The HTML layout preview is hand-authored, uses only section 1.5 of the supplied
notes and is explicitly marked as a sample. It is not a live Gemini result.
