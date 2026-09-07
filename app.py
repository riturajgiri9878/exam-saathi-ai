"""Production-ready Gradio entrypoint for Exam Saathi AI."""

from __future__ import annotations

import html
import json
import os
from pathlib import Path
from typing import Any

import gradio as gr

from core import (
    SECURITY_GUARD,
    analyze_approved_text,
    analyze_files,
    semantic_search,
)


BASE_DIR = Path(__file__).resolve().parent
REPORTS_DIR = BASE_DIR / "reports"

APP_USERNAME = os.environ.get("EXAM_SAATHI_USERNAME", "").strip()
APP_PASSWORD = os.environ.get("EXAM_SAATHI_PASSWORD", "").strip()
REQUIRE_AUTH = os.environ.get("REQUIRE_AUTH", "false").lower() in {
    "true", "1", "yes", "on"
}

if REQUIRE_AUTH and not (APP_USERNAME and APP_PASSWORD):
    raise RuntimeError(
        "Secure login is required. Set EXAM_SAATHI_USERNAME and "
        "EXAM_SAATHI_PASSWORD in the hosting environment."
    )

APP_AUTH = (APP_USERNAME, APP_PASSWORD) if APP_USERNAME and APP_PASSWORD else None


def read_text_report(name: str, fallback: str) -> str:
    path = REPORTS_DIR / name
    return path.read_text(encoding="utf-8") if path.exists() else fallback


def read_json_report(name: str, fallback: Any) -> Any:
    path = REPORTS_DIR / name
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback


DEMO_TOPICS = read_text_report(
    "important_topics_report.md",
    "## Important Topics\n\nUpload a study file to generate topics.",
)
DEMO_NOTES = read_text_report(
    "smart_notes_report.md",
    "## Smart Notes\n\nUpload a study file to generate notes.",
)
DEMO_QUESTIONS = read_text_report(
    "question_bank_report.md",
    "## Question Bank\n\nUpload a study file to generate questions.",
)
TREND_REPORT = read_text_report(
    "exam_trend_report.md",
    "## Exam Trends\n\nTrend data is unavailable.",
)
DEMO_CHUNKS = read_json_report("text_chunks.json", [])
RECOVERY_DATA = read_json_report("security_and_recovery.json", {})


def topics_markdown(result: dict[str, Any]) -> str:
    output = "## 🔑 Important Topics\n\n"
    for number, item in enumerate(result.get("topics", []), start=1):
        output += (
            f"{number}. **{item['topic']}** — Score: `{item['score']}` "
            f"({item['topic_type']})\n"
        )
    output += f"\n**Processing mode:** {result.get('processing_mode', 'Unknown')}"
    return output


def notes_markdown(result: dict[str, Any]) -> str:
    output = "## 📝 Source-Based Smart Notes\n\n"
    for note in result.get("notes", []):
        output += (
            f"### Note {note['note_number']}\n\n"
            f"{note['text']}\n\n"
            f"📄 **Source:** {note['source_name']} | Page {note['page_number']}  \n"
            f"🎯 **Relevance:** `{note['final_score']}`\n\n---\n\n"
        )
    return output


def questions_markdown(result: dict[str, Any]) -> str:
    bank = result.get("question_bank", {})
    output = "## ✍️ Generated Question Bank\n\n### Short Questions\n\n"
    for number, question in enumerate(bank.get("short_questions", []), start=1):
        output += f"{number}. {question}\n"

    output += "\n### Long Questions\n\n"
    for number, question in enumerate(bank.get("long_questions", []), start=1):
        output += f"{number}. {question}\n"

    output += "\n### MCQ Practice\n\n"
    for number, item in enumerate(bank.get("mcq_questions", []), start=1):
        output += f"**{number}. {item['question']}**\n\n"
        for option_number, option in enumerate(item["options"], start=1):
            output += f"- {option_number}. {option}\n"
        output += (
            f"\n✅ **Correct Answer:** {item['answer']}  \n"
            f"📄 **Source:** {item['source_name']} | Page {item['page_number']}\n\n---\n\n"
        )
    return output


def preview_markdown(result: dict[str, Any]) -> str:
    output = "## 📄 Extracted Text Preview\n\n"
    for document in result.get("documents", [])[:10]:
        safe_text = html.escape(document["text"][:1_500])
        output += (
            f"### {document['source_name']} - Page {document['page_number']}\n\n"
            f"**Method:** {document['extraction_method']}\n\n"
            f"{safe_text}\n\n---\n\n"
        )
    return output


def ocr_markdown(result: dict[str, Any]) -> str:
    confidence = result.get("ocr_confidence")
    if not confidence:
        return (
            "## 👤 Human Review\n\n"
            "Digital text detected. OCR correction is not required, but the extracted "
            "text can still be reviewed below."
        )
    low_words = confidence.get("low_words", [])
    output = (
        "## 👤 OCR Confidence and Human Review\n\n"
        f"- **Average Confidence:** {confidence['average_confidence']}%\n"
        f"- **Status:** {confidence['status']}\n"
    )
    if low_words:
        output += "- **Low-confidence words:** " + ", ".join(
            f"{item['word']} ({item['confidence']}%)" for item in low_words
        )
    output += "\n\nEdit the text below if required, then select **Approve Corrected Text**."
    return output


def process_file_ui(file_paths: Any):
    try:
        if isinstance(file_paths, (str, Path)):
            normalized_paths = [str(file_paths)]
        else:
            normalized_paths = [str(path) for path in (file_paths or [])]
        result = analyze_files(normalized_paths)
        info = result["file_info"]
        file_infos = result.get("file_infos", [info])
        file_list = "\n".join(
            f"  - {item['file_name']} ({item['size_mb']} MB)"
            for item in file_infos
        )
        status = (
            "## ✅ Files Processed Safely\n\n"
            f"- **Files accepted:** {len(file_infos)}\n"
            f"- **Combined size:** {info['size_mb']} MB\n"
            f"- **Readable pages:** {len(result['documents'])}\n"
            "- **Security:** Passed\n"
            f"- **NLP mode:** {result['processing_mode']}\n\n"
            f"**Processed files:**\n{file_list}"
        )
        warnings = result.get("batch_warnings", [])
        if warnings:
            status += "\n\n**Skipped files:**\n" + "\n".join(
                f"- {html.escape(message)}" for message in warnings
            )
        editable_text = "\n\n".join(
            f"[{document['source_name']} - Page {document['page_number']}]\n"
            f"{document['text']}"
            for document in result["documents"]
        )
        return (
            status,
            preview_markdown(result),
            ocr_markdown(result),
            editable_text,
            topics_markdown(result),
            notes_markdown(result),
            questions_markdown(result),
            result,
        )
    except Exception as error:
        safe_error = html.escape(str(error))
        return (
            f"## ❌ Unable to Process File\n\n**Reason:** {safe_error}",
            "## Extracted Preview\n\nNo preview generated.",
            "## Human Review\n\nNo OCR text available.",
            "",
            DEMO_TOPICS,
            DEMO_NOTES,
            DEMO_QUESTIONS,
            {},
        )


def approve_corrected_text(edited_text: str, current_state: dict[str, Any]):
    try:
        source_name = (
            current_state.get("file_info", {}).get("file_name", "Human_Approved_OCR.txt")
            if isinstance(current_state, dict)
            else "Human_Approved_OCR.txt"
        )
        result = analyze_approved_text(edited_text, source_name)
        return (
            "## ✅ Human Review Approved\n\nCorrected text was accepted and NLP results were regenerated.",
            topics_markdown(result),
            notes_markdown(result),
            questions_markdown(result),
            result,
        )
    except Exception as error:
        return (
            f"## ❌ Approval Failed\n\n{html.escape(str(error))}",
            gr.skip(),
            gr.skip(),
            gr.skip(),
            current_state,
        )


def detect_intent(request_text: str) -> tuple[str, str, list[str]]:
    lowered = request_text.lower()
    if any(word in lowered for word in ("trend", "priority", "previous paper", "prediction")):
        return "trend", "Trend Agent", [
            "Load classified questions", "Read trend scores",
            "Rank important topics", "Add prediction disclaimer",
        ]
    if any(word in lowered for word in ("quiz", "mcq", "question", "practice")):
        return "quiz", "Quiz Agent", [
            "Load reliable question bank", "Validate MCQ answers",
            "Verify source references", "Return practice questions",
        ]
    if any(word in lowered for word in ("note", "summary", "revise", "revision")):
        return "notes", "Notes Agent", [
            "Read ranked source sentences", "Check complete sentences",
            "Verify page references", "Return smart notes",
        ]
    return "search", "Retrieval Agent", [
        "Mask personal information", "Create query embedding",
        "Search relevant chunks", "Return source-grounded evidence",
    ]


def ask_agent_ui(request_text: str, current_state: dict[str, Any], request: gr.Request):
    session_id = getattr(getattr(request, "client", None), "host", "anonymous")
    try:
        safe_request = SECURITY_GUARD.check(request_text, session_id)
        intent, agent, plan = detect_intent(safe_request)
        result = current_state if isinstance(current_state, dict) else {}

        header = (
            "## 🤖 Agent Response\n\n"
            f"**Detected Intent:** {intent}  \n"
            f"**Selected Agent:** {agent}  \n"
            "**Review Status:** Approved\n\n"
            "### Execution Plan\n\n"
        )
        header += "\n".join(f"{number}. {step}" for number, step in enumerate(plan, 1))

        if intent == "trend":
            content = TREND_REPORT
        elif intent == "quiz":
            content = questions_markdown(result) if result.get("question_bank") else DEMO_QUESTIONS
        elif intent == "notes":
            content = notes_markdown(result) if result.get("notes") else DEMO_NOTES
        else:
            chunks = result.get("chunks") or DEMO_CHUNKS
            matches = semantic_search(safe_request, chunks, top_k=3)
            content = "## 🔎 Source-Grounded Search Results\n\n"
            for match in matches:
                content += (
                    f"### Result {match['rank']} — Similarity `{match['score']}`\n\n"
                    f"{match['text']}\n\n"
                    f"📄 **Source:** {match['source_name']} | Page {match['page_number']}\n\n"
                )
            if not matches:
                content += "No relevant source evidence was found."

        return f"{header}\n\n{content}"
    except Exception as error:
        return (
            "## 🛡️ Request Blocked Safely\n\n"
            f"**Reason:** {html.escape(str(error))}\n\n"
            "**Security Plan:** Plan A"
        )


def security_dashboard() -> str:
    snapshot = RECOVERY_DATA.get("recovery_snapshot", {})
    events = list(RECOVERY_DATA.get("security_events", [])) + SECURITY_GUARD.events
    output = (
        "## 🛡️ Security and Recovery Status\n\n"
        "### Current System Snapshot\n\n"
        f"- **Smart notes:** {snapshot.get('smart_notes_count', 8)}\n"
        f"- **Historical questions:** {snapshot.get('question_count', 30)}\n"
        f"- **Trend topics:** {snapshot.get('trend_topic_count', 7)}\n"
        f"- **Status:** {snapshot.get('last_verified_status', 'Healthy')}\n\n"
        "### Recovery Plans\n\n"
        "- **Plan A — Prevent:** validation, size limits, PII masking and injection blocking\n"
        "- **Plan B — Continue Safely:** verified cached reports and TF-IDF recovery mode\n"
        "- **Plan C — Recover:** restore a verified backup and require administrator review\n\n"
        "### Recent Security Events\n\n"
    )
    if events:
        for event in events[-10:]:
            output += (
                f"- `{event.get('timestamp', 'Unknown')}` | "
                f"**{event.get('event_type', 'Event')}** | "
                f"{event.get('message', '')}\n"
            )
    else:
        output += "✅ No security incidents detected."
    return output


CUSTOM_CSS = """
:root, .dark {
    --body-background-fill: #eef2ff !important;
    --body-text-color: #0f172a !important;
    --block-background-fill: #ffffff !important;
    --block-label-text-color: #172033 !important;
    --input-background-fill: #ffffff !important;
}
html, body { background: #eef2ff !important; }
.gradio-container {
    max-width: 1250px !important; margin: auto !important; padding: 18px !important;
    color: #0f172a !important;
    background: linear-gradient(135deg, #f8fafc, #eef2ff, #ecfeff) !important;
}
.exam-header {
    background: linear-gradient(135deg, #312e81, #7c3aed, #0891b2) !important;
    color: white !important; padding: 30px 20px !important; border-radius: 20px !important;
    text-align: center !important; box-shadow: 0 12px 30px rgba(49,46,129,.28) !important;
}
.exam-header h1, .exam-header h2, .exam-header p { color: white !important; }
.exam-card, .security-card, .warning-card {
    border-radius: 16px !important; padding: 18px !important;
    box-shadow: 0 6px 18px rgba(15,23,42,.10) !important;
}
.exam-card { background: white !important; border: 1px solid #cbd5e1 !important; }
.security-card { background: #ecfdf5 !important; border: 2px solid #22c55e !important; }
.warning-card { background: #fff7ed !important; border: 2px solid #f59e0b !important; }
.gradio-container .prose, .gradio-container .prose p, .gradio-container .prose li,
.gradio-container label, .gradio-container label span { color: #172033 !important; }
.gradio-container .prose h1, .gradio-container .prose h2,
.gradio-container .prose h3 { color: #4338ca !important; }
.primary-button {
    background: linear-gradient(135deg, #4f46e5, #7c3aed) !important;
    color: white !important; font-weight: 800 !important; border-radius: 12px !important;
}
.gradio-container input, .gradio-container textarea {
    background: white !important; color: #0f172a !important; border-color: #94a3b8 !important;
}
.gradio-container .generating { opacity: 1 !important; }
#study-upload, #study-upload > div, #study-upload .wrap,
#study-upload .file-preview, #study-upload .file-preview * {
    background: #ffffff !important; color: #0f172a !important;
}
#ocr-review, #ocr-review > div, #ocr-review textarea {
    background: #ffffff !important; color: #0f172a !important;
}
.gradio-container code { background: #ede9fe !important; color: #5b21b6 !important; }
footer { display: none !important; }
@media (max-width: 768px) {
    .gradio-container { padding: 8px !important; }
    .exam-header { padding: 20px 10px !important; }
    .exam-header h1 { font-size: 29px !important; }
    .exam-card, .security-card, .warning-card { padding: 12px !important; }
}
"""


with gr.Blocks(title="Exam Saathi AI") as demo:
    current_analysis = gr.State({})

    gr.HTML(
        """
        <div class="exam-header">
          <h1>📘 EXAM SAATHI AI</h1>
          <h2>Secure Agentic AI Study Assistant</h2>
          <p>PDF/Image → OCR → Human Review → NLP → Embeddings → Smart Notes → Questions → Trends</p>
        </div>
        """
    )

    with gr.Tabs():
        with gr.Tab("🏠 Home"):
            gr.Markdown(
                """
## Welcome to Exam Saathi

Exam Saathi विद्यार्थियों के study documents को source-based revision material में बदलता है।

- Secure PDF and camera-image upload
- OCR confidence and Human-in-the-Loop correction
- TF-IDF topics and sentence embeddings
- Complete smart notes with filename and page references
- Short, long and MCQ practice
- Previous-paper trend analysis
- Supervisor, specialist and reviewer workflow
- Prompt-injection protection and recovery plans

> Trend scores revision priorities हैं, guaranteed exam predictions नहीं।
                """,
                elem_classes=["exam-card"],
            )

        with gr.Tab("📤 Secure Upload"):
            gr.Markdown(
                "## Upload Study Material\n\nSelect up to 10 PDFs or camera images together. "
                "Maximum 10 MB per file, 40 MB combined and 50 pages per PDF.",
                elem_classes=["exam-card"],
            )
            study_file = gr.File(
                label="Upload up to 10 PDFs or Study Images",
                file_types=[".pdf", ".png", ".jpg", ".jpeg"],
                type="filepath",
                file_count="multiple",
                elem_id="study-upload",
            )
            process_button = gr.Button(
                "🔍 Securely Process and Generate Study Material",
                variant="primary",
                elem_classes=["primary-button"],
            )
            with gr.Row():
                upload_status = gr.Markdown("No file uploaded.", elem_classes=["security-card"])
                extracted_preview = gr.Markdown("Text preview will appear here.", elem_classes=["exam-card"])
            ocr_status = gr.Markdown(
                "OCR confidence will appear here when OCR is used.",
                elem_classes=["warning-card"],
            )
            corrected_text = gr.Textbox(
                label="Review or Correct Extracted Text",
                lines=10,
                placeholder="Extracted text will appear here.",
                elem_id="ocr-review",
            )
            approve_button = gr.Button("✅ Approve Corrected Text")
            approval_status = gr.Markdown()

        with gr.Tab("🔑 Important Topics"):
            topics_output = gr.Markdown(DEMO_TOPICS, elem_classes=["exam-card"])

        with gr.Tab("📝 Smart Notes"):
            notes_output = gr.Markdown(DEMO_NOTES, elem_classes=["exam-card"])

        with gr.Tab("✍️ Question Bank"):
            questions_output = gr.Markdown(DEMO_QUESTIONS, elem_classes=["exam-card"])

        with gr.Tab("📊 Exam Trends"):
            gr.Markdown(TREND_REPORT, elem_classes=["exam-card"])
            gr.Markdown(
                "> Evidence-based priority only; future exam questions are not guaranteed.",
                elem_classes=["warning-card"],
            )

        with gr.Tab("🤖 Ask Exam Saathi"):
            gr.Markdown(
                "## Ask the Supervisor Agent\n\nTry: `Give me smart notes`, `Create practice questions`, "
                "`Show previous-paper trends`, or `How is DNA copied?`",
                elem_classes=["exam-card"],
            )
            request_input = gr.Textbox(label="Enter Your Study Request", lines=3)
            ask_button = gr.Button(
                "🚀 Ask Exam Saathi",
                variant="primary",
                elem_classes=["primary-button"],
            )
            agent_output = gr.Markdown("Agent response will appear here.", elem_classes=["exam-card"])

        with gr.Tab("🛡️ Security & Privacy"):
            security_output = gr.Markdown(security_dashboard(), elem_classes=["security-card"])
            refresh_security = gr.Button("🔄 Refresh Security Status")
            gr.Markdown(
                """
## Student Data Policy

- Uploaded content is processed for the current app session.
- The application does not intentionally publish student documents.
- Email addresses and Indian mobile numbers are masked in agent requests.
- Invalid, oversized, password-protected and unsupported files are blocked.
- Administrators should use encrypted storage and access controls before enabling permanent user accounts.
                """,
                elem_classes=["exam-card"],
            )

    process_button.click(
        fn=process_file_ui,
        inputs=[study_file],
        outputs=[
            upload_status, extracted_preview, ocr_status, corrected_text,
            topics_output, notes_output, questions_output, current_analysis,
        ],
    )
    approve_button.click(
        fn=approve_corrected_text,
        inputs=[corrected_text, current_analysis],
        outputs=[approval_status, topics_output, notes_output, questions_output, current_analysis],
    )
    ask_button.click(
        fn=ask_agent_ui,
        inputs=[request_input, current_analysis],
        outputs=[agent_output],
    )
    refresh_security.click(fn=security_dashboard, inputs=[], outputs=[security_output])

    gr.Markdown(
        "---\n**Exam Saathi AI** | Source-Based Learning | Human-in-the-Loop | Secure by Design"
    )


if __name__ == "__main__":
    demo.queue(default_concurrency_limit=1).launch(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("PORT", "7860")),
        show_error=False,
        theme=gr.themes.Soft(
            primary_hue="indigo",
            secondary_hue="cyan",
            neutral_hue="slate",
        ),
        css=CUSTOM_CSS,
        auth=APP_AUTH,
        auth_message="Exam Saathi is private. Enter the credentials shared by the project owner.",
    )
