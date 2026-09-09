# Language update 2.8

Upload all ZIP files to the existing repository. Preserve Render credentials.
Select the target language in the teaching/Ask/notes/export menu. The menu
selection takes precedence over the source or question language.

Teacher and Ask answers now use shared language instructions and an additional
AI language check, including vocabulary/grammar for languages sharing a script.
Notes/quiz translation retries at most twice before retaining original material.
HTML exports translate content through the same check. No Hindi fallback is used
as a successful translated answer. UI headings and operational errors remain
English/Hinglish. Mic transcription preserves what the student actually says;
the selected language controls the subsequent explanation, not their speech.

Supported: 22 scheduled Indian languages plus English and Hinglish. Script choices
are the ones displayed in the dropdown; this is not all Indian dialects/scripts.
AI verification is fallible and does not certify linguistic correctness. Each
language still needs native-speaker/live testing. Extra API calls increase latency
and usage. This update does not improve OCR recognition of all handwritten scripts.
