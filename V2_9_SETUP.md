# Paste Notes and Smart Study Chat

Upload all files in the update ZIP to your existing repository and deploy.
Preserve the configured username, password and Gemini key.

Secure Upload and Understand Today's Class now have Paste Notes boxes and process
buttons. Processing pasted notes replaces the current analysis, just like a new
file upload. UTF-8 .txt files are also accepted. Pasted content does not require OCR.

Smart Study Chat provides session conversation history, microphone transcription,
notes-first answers and Google Search fallback. Enable/disable search with its
checkbox. Only the current masked question goes to search, not the full document.
Follow-up search questions should name the topic explicitly. Uploaded images are
processed by the existing upload pipeline; this update does not generate images or
retrieve web photographs. See Smart Notes for existing source diagrams.

Search uses the Gemini Interactions API with google_search. Your installed
google-genai SDK and model/account must support it. GEMINI_WEB_MODEL optionally
selects a different available search-capable model; default is GEMINI_MODEL.
Google's current integration documentation: https://ai.google.dev/gemini-api/docs/google-search
No source citations means no web answer displayed. Search suggestions use an
isolated iframe. AI language verification remains fallible and adds latency.

This is a study-chat implementation, not feature parity with ChatGPT. Search
availability, SDK compatibility and language behavior need live deployment tests;
only compilation and isolated citation-validation checks were run in this update.
No images are generated, and no permanent cross-session memory is provided.
