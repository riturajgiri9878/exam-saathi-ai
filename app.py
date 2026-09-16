"""Production-ready Gradio entrypoint for Exam Saathi AI."""

from __future__ import annotations

import html
import json
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

import gradio as gr
from study_export import export_study_guide
from study_languages import LANGUAGES, translate_analysis
from learning_modes import (profile, register_papers, prioritize_notes, teach_class,
                            export_catalog, import_catalog, catalog_summary)
from smart_chat import reply as smart_reply
from chapter_teacher import lesson_steps,render_lesson,source_signature,lesson_plain

from answer_engine import (
    ENGINE_VERSION,
    SUPPORTED_LANGUAGES,
    answer_markdown,
)
from exam_graph import run_exam_graph

from core import (
    SECURITY_GUARD,
    analyze_approved_text,
    analyze_files,
    answer_from_source_evidence,
    semantic_search,
    retrieve_uploaded_context,
    transcribe_study_audio,
)
from study_features import (
    answer_matches,
    build_exam_mode,
    build_flashcards,
    build_quiz_items,
    build_revision_plan,
    diagram_learning_markdown,
    export_friend_quiz,
    flashcard_view,
    low_data_markdown,
    progress_markdown,
    quiz_view,
)


BASE_DIR = Path(__file__).resolve().parent
REPORTS_DIR = BASE_DIR / "reports"

APP_USERNAME = os.environ.get("EXAM_SAATHI_USERNAME", "").strip()
APP_PASSWORD = os.environ.get("EXAM_SAATHI_PASSWORD", "").strip()
REQUIRE_AUTH = os.environ.get("REQUIRE_AUTH", "true").lower() in {
    "true", "1", "yes", "on"
}

if REQUIRE_AUTH and not (APP_USERNAME and APP_PASSWORD):
    raise RuntimeError(
        "Secure login is required. Set EXAM_SAATHI_USERNAME and "
        "EXAM_SAATHI_PASSWORD in the hosting environment."
    )

APP_AUTH = (APP_USERNAME, APP_PASSWORD) if APP_USERNAME and APP_PASSWORD else None
AUTH_CONTROL = (
    '<a class="logout-button" href="/logout">🔒 Logout / Change user</a>'
    if APP_AUTH else
    '<span class="auth-warning">⚠️ Private login is not configured</span>'
)


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
    diagram_pages = {
        (item.get("source_name"), item.get("page_number"))
        for item in result.get("diagrams", [])
    }
    for note in result.get("notes", []):
        diagram_line = ""
        if (note["source_name"], note["page_number"]) in diagram_pages:
            diagram_line = "📐 **Original diagram available below.**  \n"
        output += (
            f"### Note {note['note_number']}\n\n"
            f"{note['text']}\n\n"
            f"📄 **Source:** {note['source_name']} | Page {note['page_number']}  \n"
            f"{diagram_line}"
            f"🎯 **Relevance:** `{note['final_score']}`\n\n---\n\n"
        )
    return output


def diagrams_markdown(result: dict[str, Any]) -> str:
    diagrams = result.get("diagrams", [])
    if not diagrams:
        return (
            "## 📐 Important Diagrams\n\n"
            "No source-grounded diagram was detected. Text notes are still available."
        )
    output = (
        "## 📐 Important Diagrams\n\n"
        f"Found **{len(diagrams)}** useful diagram page(s). Click an image to zoom. "
        "These are original source pages, so handwritten labels and formulas are preserved.\n\n"
    )
    for number, item in enumerate(diagrams, start=1):
        output += (
            f"**{number}. {html.escape(item['source_name'])} — Page "
            f"{item['page_number']}**  \n"
            f"{html.escape(item['description'])}\n\n"
        )
    return output


def diagram_gallery_items(result: dict[str, Any]) -> list[tuple[str, str]]:
    items: list[tuple[str, str]] = []
    for diagram in result.get("diagrams", []):
        caption = (
            f"{diagram['source_name']} | Page {diagram['page_number']} — "
            f"{diagram['description']}"
        )
        items.append((diagram["image_path"], caption[:500]))
    return items


def formulas_markdown(result: dict[str, Any]) -> str:
    formulas = result.get("formulas", [])
    output = "## 📐 Source-Based Formula Sheet\n\n"
    if not formulas:
        return output + "No reliable formula was extracted. Check Human Review before studying."
    for number, item in enumerate(formulas, start=1):
        output += (
            f"{number}. `{item['formula']}`  \n"
            f"   📄 **Source:** {item['source_name']} | Page {item['page_number']}\n\n"
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
            f"**Method:** {document['extraction_method']}  \n"
            f"**Readability:** {document.get('readability', 'UNKNOWN')}\n\n"
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
    average = confidence.get("average_confidence")
    confidence_line = (
        f"{average}%"
        if isinstance(average, (int, float))
        else "Not supplied by Gemini — verify in Human Review"
    )
    output = (
        "## 👤 OCR Confidence and Human Review\n\n"
        f"- **OCR Engine:** {confidence.get('provider', 'Local Tesseract OCR')}\n"
        f"- **Confidence:** {confidence_line}\n"
        f"- **Status:** {confidence['status']}\n"
    )
    if confidence.get("provider_error"):
        output += (
            "- **Gemini fallback:** Not used — "
            f"{html.escape(confidence['provider_error'])}\n"
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
        quality = result.get("page_quality", {})
        if quality:
            status += (
                "\n\n**Smart extraction quality:** "
                f"High {quality.get('HIGH', 0)} | Medium {quality.get('MEDIUM', 0)} | "
                f"Low {quality.get('LOW', 0)} | "
                f"Unusable skipped {quality.get('SKIPPED', 0)}"
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
            diagrams_markdown(result),
            diagram_gallery_items(result),
            formulas_markdown(result),
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
            "## 📐 Important Diagrams\n\nNo diagram preview generated.",
            [],
            "## 📐 Formula Sheet\n\nNo reliable formula extracted.",
            DEMO_QUESTIONS,
            {},
        )


def process_class_files_ui(files):
    # Reuse the validated OCR pipeline and clear the previous lesson context.
    return (*process_file_ui(files), '', '', '')


def process_pasted_ui(text):
    try:
        from core import MAX_TEXT_CHARACTERS
        if len(text or '')>MAX_TEXT_CHARACTERS:
            raise ValueError('Pasted notes exceed the text limit. Split them into smaller lessons.')
        result=analyze_approved_text(text,'Pasted_Notes.txt')
        for document in result['documents']:
            document['source_type']='Pasted Text'
            document['extraction_method']='Pasted Text'
        return ('✅ Pasted notes processed. You can now ask your question.',
                preview_markdown(result),'Pasted text: no OCR required.',text,
                topics_markdown(result),notes_markdown(result),diagrams_markdown(result),[],
                formulas_markdown(result),questions_markdown(result),result,'','','')
    except Exception as error:
        return (html.escape(str(error)), *[gr.skip() for _ in range(13)])


def smart_chat_ui(question,history,analysis,language,allow_web):
    try:
        updated,widgets=smart_reply(question,history,analysis,language,allow_web)
        return updated,widgets,''
    except Exception:
        return gr.skip(),'','Chat/search unavailable or language validation failed. Check Gemini model/access and retry. Your question has been kept.'


def _question_context(question: str, analysis: dict[str, Any]) -> list[dict[str, Any]]:
    """Return only the most relevant uploaded-note chunks for one question."""
    if not isinstance(analysis, dict):
        return []
    chunks = analysis.get("chunks", [])
    if not chunks:
        return []
    try:
        return retrieve_uploaded_context(question, chunks, top_k=6)
    except Exception:
        # The answer engine can still solve from general knowledge/web tools.
        return []


def _verification_panel(answer: dict[str, Any]) -> str:
    status = answer.get("verification_status", "REVIEW_NEEDED")
    icon = {"VERIFIED": "✅", "REVIEW_NEEDED": "⚠️", "INSUFFICIENT": "🛑"}.get(status, "⚠️")
    route = answer.get("route", {})
    checks = []
    if route.get("web_grounding"):
        checks.append("web sources")
    if route.get("code_execution"):
        checks.append("independent calculation")
    if route.get("uploaded_evidence"):
        checks.append("uploaded notes")
    if answer.get("agentic_workflow"):
        checks.append("LangGraph quality gate")
        retrieval_engine = str(answer["agentic_workflow"].get("retrieval_engine") or "")
        if "LlamaIndex" in retrieval_engine:
            checks.append("LlamaIndex document retrieval")
    check_text = ", ".join(checks) if checks else "independent reviewer"
    providers = ", ".join(
        str(model) for model in answer.get("models", [])
        if model and model != "review-unavailable"
    ) or "not reported"
    return (
        f"{icon} **{status}** · Confidence: **{answer.get('confidence', 0)}%** · "
        f"Subject: **{answer.get('subject', 'General Studies')}** · Checks: {check_text} · "
        f"Models: **{providers}** · "
        f"Engine: **v{answer.get('engine_version', ENGINE_VERSION)}**"
    )


def quick_solver_ui(
    question, history, language, subject_choice, allow_web, analysis,
    conversations, active_chat_id,
    request: gr.Request,
):
    try:
        session_id = getattr(getattr(request, "client", None), "host", "anonymous")
        safe_question = SECURITY_GUARD.check(question, session_id)
        rag_context = _question_context(safe_question, analysis)
        chat_id = str(active_chat_id or uuid4().hex)
        graph_result = run_exam_graph(
            safe_question,
            language=language,
            rag_context=rag_context,
            force_web=bool(allow_web),
            subject_override=subject_choice,
            chat_history=list(history or []),
            thread_id=chat_id,
        )
        answer = graph_result["answer"]
        rendered = answer_markdown(answer)
        updated = list(history or [])
        updated.extend([
            {"role": "user", "content": safe_question},
            {"role": "assistant", "content": rendered},
        ])
        html_file = graph_result["html_file"]
        pdf_file = graph_result["pdf_file"]
        graph_events = graph_result.get("workflow_events", [])
        status = (
            f"✅ Agentic workflow complete ({len(graph_events)} steps). "
            f"Fresh visual pack created for this exact question. "
            f"PDF is static/printable; HTML contains safe offline animation. "
            f"Files are unique, so an older answer cannot be reused from cache."
        )
        verification = _verification_panel(answer)
        saved = list(conversations or [])
        existing = next((item for item in saved if item.get("id") == chat_id), None)
        title = (
            existing.get("title", "") if existing else
            " ".join(safe_question.split())[:52]
        ) or "New question"
        record = {
            "id": chat_id,
            "title": title,
            "messages": updated,
            "verification": verification,
            "pdf_file": pdf_file,
            "html_file": html_file,
            "visual_status": status,
            "workflow_events": graph_events,
        }
        saved = [record] + [item for item in saved if item.get("id") != chat_id]
        saved = saved[:25]
        choices = [(item.get("title", "Question"), item.get("id", "")) for item in saved]
        return (
            updated, "", verification, pdf_file, html_file, status,
            saved, chat_id, gr.update(choices=choices, value=chat_id),
        )
    except Exception as error:
        return (
            gr.skip(), gr.skip(), '❌ ' + html.escape(str(error)), None, None, '',
            gr.skip(), gr.skip(), gr.skip(),
        )


def new_quick_chat_ui(conversations):
    """Clear the active conversation while keeping this session's history."""
    choices = [
        (item.get("title", "Question"), item.get("id", ""))
        for item in (conversations or [])
    ]
    return [], "", "", None, None, "", conversations or [], "", gr.update(
        choices=choices, value=None,
    )


def open_quick_chat_ui(selected_chat_id, conversations):
    """Restore a solved question from the current browser session."""
    for item in conversations or []:
        if item.get("id") == selected_chat_id:
            return (
                item.get("messages", []),
                "",
                item.get("verification", ""),
                item.get("pdf_file"),
                item.get("html_file"),
                item.get("visual_status", ""),
                selected_chat_id,
            )
    return [], "", "", None, None, "", ""


def process_home_attachment_ui(file_paths):
    """Run the secure document pipeline from the Home chat composer."""
    values = process_file_ui(file_paths)
    return (*values, values[0])


def approve_corrected_text(edited_text: str, current_state: dict[str, Any]):
    try:
        source_name = (
            current_state.get("file_info", {}).get("file_name", "Human_Approved_OCR.txt")
            if isinstance(current_state, dict)
            else "Human_Approved_OCR.txt"
        )
        result = analyze_approved_text(edited_text, source_name)
        if isinstance(current_state, dict):
            result["diagrams"] = current_state.get("diagrams", [])
        return (
            "## ✅ Human Review Approved\n\nCorrected text was accepted and NLP results were regenerated.",
            topics_markdown(result),
            notes_markdown(result),
            diagrams_markdown(result),
            diagram_gallery_items(result),
            formulas_markdown(result),
            questions_markdown(result),
            result,
        )
    except Exception as error:
        return (
            f"## ❌ Approval Failed\n\n{html.escape(str(error))}",
            gr.skip(),
            gr.skip(),
            gr.skip(),
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


def transcribe_voice_ui(audio_path: str | None, language: str):
    try:
        transcript = transcribe_study_audio(audio_path, language)
        return transcript, "✅ Voice question is ready. Review it, then press **Send**."
    except Exception as error:
        return gr.skip(), f"❌ {html.escape(str(error))}"


def start_flashcards_ui(result: dict[str, Any], progress: dict[str, Any]):
    state = {"cards": build_flashcards(result or {}), "index": 0}
    return state, flashcard_view(state), progress_markdown(progress or {})


def reveal_flashcard_ui(state: dict[str, Any], progress: dict[str, Any]):
    progress = dict(progress or {})
    if state.get("cards"):
        progress["xp"] = int(progress.get("xp", 0)) + 2
    return flashcard_view(state or {}, reveal=True), progress_markdown(progress), progress


def next_flashcard_ui(state: dict[str, Any]):
    state = dict(state or {})
    cards = state.get("cards", [])
    if cards:
        state["index"] = (int(state.get("index", 0)) + 1) % len(cards)
    return state, flashcard_view(state)


def start_quiz_ui(result: dict[str, Any], progress: dict[str, Any]):
    state = {"items": build_quiz_items(result or {}), "index": 0, "checked": False}
    return state, quiz_view(state), "", "", progress_markdown(progress or {})


def check_quiz_ui(answer: str, state: dict[str, Any], progress: dict[str, Any]):
    state = dict(state or {})
    items = state.get("items", [])
    if not items:
        return "पहले quiz शुरू करें।", progress_markdown(progress or {}), progress or {}, state
    if state.get("checked"):
        return "इस question को check कर चुके हैं। अब **Next Question** दबाएँ।", progress_markdown(progress or {}), progress or {}, state
    item = items[int(state.get("index", 0)) % len(items)]
    correct = any(
        answer_matches(answer, accepted)
        for accepted in item.get("accepted_answers", [item["answer"]])
    )
    progress = dict(progress or {})
    progress["attempted"] = int(progress.get("attempted", 0)) + 1
    if correct:
        progress["correct"] = int(progress.get("correct", 0)) + 1
        progress["xp"] = int(progress.get("xp", 0)) + 10
        heading = "✅ Correct! +10 XP"
    else:
        progress["xp"] = int(progress.get("xp", 0)) + 2
        weak = list(progress.get("weak_topics", []))
        weak.append(item["answer"][:80])
        progress["weak_topics"] = weak[-10:]
        heading = "🔁 Needs Review +2 XP"
    state["checked"] = True
    feedback = (
        f"### {heading}\n\n**Expected answer:** {item['answer']}\n\n"
        f"📄 **Source:** {item['source']}"
    )
    return feedback, progress_markdown(progress), progress, state


def next_quiz_ui(state: dict[str, Any]):
    state = dict(state or {})
    items = state.get("items", [])
    if items:
        state["index"] = (int(state.get("index", 0)) + 1) % len(items)
    state["checked"] = False
    return state, quiz_view(state), "", ""


def export_friend_quiz_ui(result: dict[str, Any]):
    try:
        return export_friend_quiz(result or {}), "✅ Quiz file ready. इसे WhatsApp/email से दोस्त को भेज सकते हैं।"
    except Exception as error:
        return gr.skip(), f"❌ {html.escape(str(error))}"


def add_papers_ui(files, catalog, board, level, course, subject, syllabus, year, kind):
    try:
        identity = profile(board,level,course,subject,syllabus)
        if not files: raise ValueError('Choose previous-paper PDFs first.')
        analysis = analyze_files(files)
        catalog = register_papers(catalog,analysis,identity,year,kind)
        warnings = '; '.join(analysis.get('batch_warnings',[]))
        return catalog, '✅ '+catalog_summary(catalog)+' '+html.escape(warnings)
    except Exception as error:
        return gr.skip(), html.escape(str(error))


def export_paper_catalog_ui(catalog):
    try:
        return export_catalog(catalog), '✅ Portable catalog ready. Keep this file and import it after a restart or deployment.'
    except Exception as error:
        return gr.skip(), '❌ '+html.escape(str(error))


def import_paper_catalog_ui(path):
    try:
        catalog=import_catalog(path)
        return catalog, '✅ Catalog restored: '+catalog_summary(catalog)
    except Exception as error:
        return gr.skip(), '❌ '+html.escape(str(error))


def paper_priority_ui(analysis,catalog,board,level,course,subject,syllabus,year):
    try:
        if not analysis.get('documents'): raise ValueError('Upload your class notes in Secure Upload first.')
        identity=profile(board,level,course,subject,syllabus)
        updated,report=prioritize_notes(analysis,catalog,identity,year)
        return updated,report,notes_markdown(updated),topics_markdown(updated)
    except Exception as error:
        return gr.skip(),html.escape(str(error)),gr.skip(),gr.skip()


def class_teacher_ui(analysis,question,language,previous,answer):
    try:
        response=teach_class(analysis,question,language,previous,answer)
        return response,response
    except Exception as error:
        return html.escape(str(error)),gr.skip()


def build_chapter_ui(analysis,question,language,previous_lesson):
    try:
        for lesson in lesson_steps(analysis,language,question,previous_lesson):
            done=len(lesson['batches']); total=lesson['total_batches']
            status=f'{done}/{total} source batches explained · {lesson["status"]}. '
            status+='Every extracted section is listed in Source coverage below.'
            if lesson.get('errors'):
                latest=lesson['errors'][sorted(lesson['errors'],key=int)[-1]]
                status+=' Why it stopped: '+latest
            file=None
            if lesson['status'] in ('complete','partial') and done:
                exported=dict(analysis,detailed_lesson=lesson,study_language=language)
                try:
                    file=export_study_guide(exported,'Detailed Chapter Study Guide',True)
                except Exception:
                    status+=' Lesson is retained, but HTML creation failed. Retry the download in Low Data & Share.'
            yield (render_lesson(lesson),lesson_plain(lesson),lesson,status,file,diagram_gallery_items(analysis))
    except Exception:
        yield (gr.skip(),gr.skip(),gr.skip(),
               'Could not build this lesson. Process notes first, then retry. Earlier completed sections are retained.',
               None,gr.skip())


def lesson_feedback_ui(analysis,question,language,lesson,answer):
    if not lesson or lesson.get('source_signature')!=source_signature(analysis):
        return 'Build the lesson for your current notes before checking your answer.'
    if not str(answer or '').strip(): return 'Write your answer and mention the topic or question first.'
    text,_=class_teacher_ui(analysis,question+'\nQuestion/topic and student answer: '+answer[:2000],language,lesson_plain(lesson),answer)
    return text


def reset_lesson_for_source(analysis,lesson):
    if lesson and lesson.get('source_signature')==source_signature(analysis):
        return tuple(gr.skip() for _ in range(8))
    return {},'', '', '',None,[], '', ''


def export_study_guide_ui(result, title, include_diagrams, language, lesson):
    try:
        if lesson and lesson.get('source_signature')==source_signature(result):
            if lesson.get('language')!=language:
                raise ValueError('Select the lesson language here, or rebuild the detailed lesson in your new language first.')
            if not lesson.get('batches'):
                raise ValueError('No lesson section is ready yet. Build / Resume the chapter first.')
            exported=dict(result,detailed_lesson=lesson,study_language=language)
            return export_study_guide(exported,title,include_diagrams),f'HTML includes the detailed lesson ({lesson["status"]}), diagrams and short/long model answers.'
        if result.get('study_language') != language:
            result = translate_analysis(result.get('_original_analysis', result), language)
        return export_study_guide(result, title, include_diagrams), 'Quick guide ready. For detailed stories, concept diagrams and model answers, build the full chapter in Understand Today’s Class first.'
    except Exception as error:
        return gr.skip(), f"❌ {html.escape(str(error))}"


def notes_language_ui(result: dict[str, Any], language: str):
    result = result or {}
    if not result.get("notes"):
        return "## 📝 Smart Notes\n\nपहले study material process करें।"
    if language == "Exam English":
        return notes_markdown(result)
    evidence = [
        {
            "text": note["text"],
            "source_name": note["source_name"],
            "page_number": note["page_number"],
        }
        for note in result["notes"]
    ]
    request = (
        "Rewrite every supplied smart note as a short, exam-useful numbered note. "
        "Preserve formulas and facts exactly. Keep the filename and page number beside each note."
    )
    generated = answer_from_source_evidence(request, evidence, language)
    if generated:
        return f"## 📝 Smart Notes — {language}\n\n{generated}"
    return (
        notes_markdown(result)
        + "\n\n> Language conversion अभी उपलब्ध नहीं है; Gemini API configuration check करें।"
    )


def translate_study_ui(result, language):
    try:
        original = result.get('_original_analysis', result)
        translated = translate_analysis(original, language)
        translated['_original_analysis'] = original
        return (translated, notes_markdown(translated), topics_markdown(translated),
                questions_markdown(translated), '✅ '+language+' ready. Restart cards/quiz to load the translated questions.')
    except Exception:
        return (gr.skip(), gr.skip(), gr.skip(), gr.skip(),
                'Translation unavailable or incomplete. Original study material is unchanged. Check Gemini access and retry.')


def ask_agent_ui(
    request_text: str,
    current_state: dict[str, Any],
    language: str,
    request: gr.Request,
):
    session_id = getattr(getattr(request, "client", None), "host", "anonymous")
    try:
        safe_request = SECURITY_GUARD.check(request_text, session_id)
        result = current_state if isinstance(current_state, dict) else {}
        rag_context = _question_context(safe_request, result)
        answer = solve_question(
            safe_request,
            language=language,
            rag_context=rag_context,
        )
        html_file, pdf_file = create_answer_artifacts(answer)
        return (
            answer_markdown(answer),
            _verification_panel(answer),
            pdf_file,
            html_file,
        )
    except Exception as error:
        blocked = (
            "## 🛡️ Request Blocked Safely\n\n"
            f"**Reason:** {html.escape(str(error))}\n\n"
            "**Security Plan:** Plan A"
        )
        # Always clear old downloads when a new request fails.
        return blocked, "", None, None


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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Noto+Sans:wght@400;500;600;700&display=swap');
:root, .dark {
    --body-background-fill: #eef2ff !important;
    --body-text-color: #0f172a !important;
    --background-fill-primary: #ffffff !important;
    --background-fill-secondary: #eef2ff !important;
    --block-background-fill: #ffffff !important;
    --block-label-text-color: #172033 !important;
    --input-background-fill: #ffffff !important;
    --border-color-primary: #cbd5e1 !important;
    --loader-color: #4f46e5 !important;
    --color-accent: #4f46e5 !important;
}
html, body, .gradio-container,
.gradio-container :is(button, input, textarea, select, label, p, li, a, summary, h1, h2, h3, h4, h5, h6) {
    font-family: "Inter", "Noto Sans", Arial, sans-serif !important;
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
.logout-button, .auth-warning {
    display: inline-block !important; margin-top: 10px !important;
    padding: 8px 14px !important; border-radius: 10px !important;
    background: rgba(255,255,255,.18) !important; color: white !important;
    font-weight: 800 !important; text-decoration: none !important;
}
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
.gradio-container .generating,
.gradio-container .generating > div,
.gradio-container .generating textarea,
.gradio-container .generating .wrap,
.gradio-container .generating .file-preview,
.gradio-container .generating .file-preview * {
    background: #ffffff !important;
    color: #0f172a !important;
    opacity: 1 !important;
}
.gradio-container .eta-bar,
.gradio-container .progress-level,
.gradio-container .progress-level-inner {
    background: #eef2ff !important;
    color: #0f172a !important;
    opacity: .96 !important;
}
.gradio-container .meta-text,
.gradio-container .meta-text-center,
.gradio-container .generating span {
    color: #0f172a !important;
}
#study-upload, #study-upload > div, #study-upload .wrap,
#study-upload .file-preview, #study-upload .file-preview *,
#study-upload .upload-container, #study-upload .upload-container *,
#study-upload [data-testid="file"], #study-upload [data-testid="file"] * {
    background: #ffffff !important; color: #0f172a !important;
}
#study-upload button, #study-upload a {
    color: #0f172a !important;
}
#study-upload .progress-text, #study-upload .eta-bar,
#study-upload .progress-level, #study-upload .progress-level-inner {
    background: #eef2ff !important; color: #0f172a !important;
}
#ocr-review, #ocr-review > div, #ocr-review textarea {
    background: #ffffff !important; color: #0f172a !important;
}
#diagram-gallery, #diagram-gallery > div {
    background: #ffffff !important; color: #0f172a !important;
}
#diagram-gallery img {
    background: #ffffff !important; object-fit: contain !important;
}
.gradio-container code { background: #ede9fe !important; color: #5b21b6 !important; }
footer { display: none !important; }
/* Student palette, scoped to the Gradio root so OS dark mode cannot
   override nested file rows and download controls. */
html, body {
    background: #e8ddfa !important;
    background-image: radial-gradient(ellipse at 8% 10%, #d6c3ff 0, transparent 48%),
        radial-gradient(ellipse at 92% 35%, #bcf0e3 0, transparent 48%),
        linear-gradient(150deg, #eee5ff, #e0f4ef 62%, #ffe3d6) !important;
    background-attachment: fixed !important;
}
.gradio-container, .gradio-container.dark, .dark .gradio-container {
    color-scheme: light !important;
    --body-background-fill: #eee5ff !important;
    --body-text-color: #20233e !important;
    --background-fill-primary: #f3edff !important;
    --background-fill-secondary: #e7f5ef !important;
    --block-background-fill: #f3edff !important;
    --block-label-background-fill: #e2d5fa !important;
    --block-label-text-color: #35215e !important;
    --block-title-text-color: #35215e !important;
    --input-background-fill: #faf6ff !important;
    --input-background-fill-focus: #faf6ff !important;
    --input-text-color: #20233e !important;
    --link-text-color: #433087 !important;
    --button-secondary-background-fill: #dcd3f4 !important;
    --button-secondary-background-fill-hover: #cfc1ef !important;
    --button-secondary-text-color: #30204f !important;
    --border-color-primary: #c6b6df !important;
    background: transparent !important;
}
.gradio-container .exam-card {
    background: linear-gradient(125deg, #f1e8ff, #e5f3f0) !important;
    border-color: #cbbbe5 !important;
}
.gradio-container .security-card { background: #dff4e9 !important; }
.gradio-container .warning-card { background: #fff0dc !important; }
.gradio-container input, .gradio-container textarea,
#ocr-review, #ocr-review > div, #ocr-review textarea {
    background: #faf6ff !important; color: #20233e !important;
}
/* Keep Quick Solver readable even when the browser/OS requests dark mode. */
#quick-solver-chat, #quick-solver-chat .wrap,
#quick-solver-chat .bubble-wrap, #quick-solver-chat .message,
#quick-solver-chat .message-wrap, #quick-solver-chat .prose,
#quick-solver-chat .prose :is(p,li,h1,h2,h3,h4,strong,em,span) {
    color: #172033 !important;
}
#quick-solver-chat .message,
#quick-solver-chat [data-testid="bot"],
#quick-solver-chat [data-testid="user"] {
    background: #faf6ff !important;
    border-color: #c6b6df !important;
}
#quick-solver-chat .message.user {
    background: #e7f5ef !important;
}
.gradio-container button.secondary {
    background: #dcd3f4 !important; color: #30204f !important;
}
.gradio-container .study-file,
.gradio-container .study-file :is(div,table,thead,tbody,tr,td,th,a,button,span),
#study-upload, #study-upload :is(div,table,thead,tbody,tr,td,th,a,button,span) {
    background: #e7f5ef !important;
    color: #193d38 !important;
}
.gradio-container .study-file a, #study-upload a {
    text-decoration: underline !important;
    overflow-wrap: anywhere !important;
}
.gradio-container .study-file svg, #study-upload svg {
    color: #315b51 !important;
}
.gradio-container :is(button,a,input,summary):focus-visible {
    outline: 3px solid #7351b8 !important; outline-offset: 3px;
}
.exam-header strong { color: #fff !important; }
/* File pickers use transparent overlays. Do not paint every nested div:
   doing so can cover the native upload prompt. */
#study-upload :is(div,span,button),
.gradio-container .study-file :is(div,span,button) {
    background: transparent !important;
}
#study-upload :is(p,label,span,button,a),
.gradio-container .study-file :is(p,label,span,button,a) {
    color: #193d38 !important;
}
.gradio-container input[type="file"] {
    background: transparent !important;
    opacity: 0 !important;
}
#choose-study-files {
    background: #5b36b4 !important; color: #fff !important;
    min-height: 54px; border: 2px solid #452487 !important;
    font-size: 18px !important; font-weight: 800 !important;
}
#choose-study-files :is(span,p,svg) { color: #fff !important; }
.study-sky { pointer-events: none; position: fixed; inset: 0; z-index: 0; overflow: hidden; }
.study-sky span { position: absolute; font-size: 36px; opacity: .65;
    animation: study-drift 9s ease-in-out infinite alternate; }
.study-sky .rainbow { left: 1%; top: 20%; font-size: 64px; }
.study-sky .butterfly { right: 2%; top: 42%; animation-delay: -3s; }
.study-sky .books { left: 2%; bottom: 12%; animation-delay: -6s; }
.study-sky .star { right: 3%; bottom: 15%; animation-delay: -1s; }
.exam-header { position: relative; }
@keyframes study-drift { from { transform: translateY(0) rotate(-5deg); }
    to { transform: translateY(-18px) rotate(6deg); } }
@media (prefers-reduced-motion: reduce) { .study-sky span { animation: none; } }
@media (max-width: 768px) { .study-sky span { font-size: 22px; opacity: .22; }
    .study-sky .rainbow { font-size: 36px; } }
@media (max-width: 768px) {
    .gradio-container { padding: 8px !important; }
    .exam-header { padding: 20px 10px !important; }
    .exam-header h1 { font-size: 29px !important; }
    .exam-card, .security-card, .warning-card { padding: 12px !important; }
}
/* Chat-first Home */
#chat-history-sidebar {
    background: rgba(247, 244, 255, .98) !important;
    border-right: 1px solid #cfc3e5 !important;
}
#chat-history-sidebar .sidebar-brand {
    color: #35215e !important; font-size: 20px; font-weight: 900;
    margin: 2px 0 12px;
}
#chat-history-sidebar label { font-weight: 800 !important; }
.exam-header {
    padding: 14px 20px !important; border-radius: 16px !important;
    text-align: left !important; display: flex; align-items: center;
    justify-content: space-between; gap: 16px;
}
.exam-header h1 { margin: 0 !important; font-size: 25px !important; }
.exam-header p { margin: 2px 0 0 !important; font-size: 13px !important; }
.exam-header .header-copy { min-width: 0; }
.exam-header .header-copy p { opacity: .9; }
.exam-header .logout-button, .exam-header .auth-warning {
    flex: 0 0 auto; margin-top: 0 !important;
}
.chat-home-hero { text-align: center; margin: 18px auto 12px; }
.chat-home-hero h1 { color: #312e81 !important; font-size: clamp(28px, 4vw, 43px); margin: 0; }
.chat-home-hero p { color: #5b5670 !important; margin-top: 7px; }
.chat-composer {
    background: rgba(255,255,255,.94) !important;
    border: 1px solid #c6b6df !important; border-radius: 20px !important;
    padding: 12px !important; box-shadow: 0 12px 28px rgba(49,46,129,.12) !important;
}
.chat-composer textarea { min-height: 92px !important; border-radius: 14px !important; }
.chat-tools { align-items: end !important; }
#home-attach-button {
    min-height: 46px !important; border-radius: 12px !important;
    background: #e7f5ef !important; color: #193d38 !important; font-weight: 800 !important;
}
#home-attach-button :is(span,p,svg) { color: #193d38 !important; }
.download-accordion { margin-top: 12px !important; }
@media (max-width: 768px) {
    .exam-header { display: block; text-align: center !important; }
    .exam-header .logout-button, .exam-header .auth-warning { margin-top: 8px !important; }
    .chat-home-hero { margin-top: 10px; }
}
"""


with gr.Blocks(title="Exam Saathi AI") as demo:
    paper_catalog = gr.State([])
    teacher_history = gr.State('')
    detailed_lesson = gr.State({})
    current_analysis = gr.State({})
    flashcard_state = gr.State({"cards": [], "index": 0})
    quiz_state = gr.State({"items": [], "index": 0, "checked": False})
    progress_state = gr.State({"xp": 0, "attempted": 0, "correct": 0, "weak_topics": []})
    quick_conversations = gr.State([])
    quick_active_chat = gr.State("")

    with gr.Sidebar(label="Study chats", open=True, width=270, elem_id="chat-history-sidebar"):
        gr.HTML('<div class="sidebar-brand">📘 Exam Saathi</div>')
        sidebar_new_chat = gr.Button("✏️ New chat", variant="primary")
        history_picker = gr.Radio(
            choices=[], label="Recent questions", interactive=True,
        )
        gr.Markdown(
            "**Study tools**\n\nUpload notes, learn a chapter, revise with flashcards, "
            "or open Previous Papers from the top menu."
        )

    gr.HTML(
        f"""
        <div class="study-sky" aria-hidden="true"><span class="rainbow">🌈</span>
        <span class="butterfly">🦋</span><span class="books">📚</span><span class="star">⭐</span></div>
        <div class="exam-header">
          <div class="header-copy">
            <h1>📘 EXAM SAATHI AI</h1>
            <p><strong>Agentic Learning Graph · Verified Multilingual Engine · v{ENGINE_VERSION}</strong></p>
          </div>
          {AUTH_CONTROL}
        </div>
        """
    )

    with gr.Tabs():
        with gr.Tab("🏠 Home"):
            gr.HTML(
                '<div class="chat-home-hero"><h1>What do you want to learn?</h1>'
                '<p>Ask one question, attach your notes, or speak in your preferred language.</p></div>'
            )
            quick_chat = gr.Chatbot(
                label="Your conversation", height=460, elem_id="quick-solver-chat",
                latex_delimiters=[
                    {"left": "$$", "right": "$$", "display": True},
                    {"left": r"\(", "right": r"\)", "display": False},
                ],
            )
            with gr.Group(elem_classes=["chat-composer"]):
                quick_question = gr.Textbox(
                    label="Message Exam Saathi",
                    placeholder="Ask any question — Maths, Physics, Chemistry, Biology, Geography, GK...",
                    lines=3,
                    autofocus=True,
                )
                with gr.Row(elem_classes=["chat-tools"]):
                    quick_attachment = gr.UploadButton(
                        "📎 Add PDF / image",
                        file_types=[".pdf", ".html", ".htm", ".txt", ".png", ".jpg", ".jpeg"],
                        file_count="multiple", type="filepath", elem_id="home-attach-button",
                    )
                    quick_mic = gr.Audio(
                        sources=["microphone"], type="filepath", label="🎙️ Speak",
                    )
                    quick_transcribe = gr.Button("Use voice")
                    quick_send = gr.Button("➤ Send", variant="primary", elem_classes=["primary-button"])
                quick_attachment_status = gr.Markdown()
                quick_voice_status = gr.Markdown()
            with gr.Accordion("Language, subject and verification", open=False):
                with gr.Row():
                    quick_language = gr.Dropdown(
                        choices=SUPPORTED_LANGUAGES, value="Hinglish", label="Answer language",
                    )
                    quick_subject = gr.Dropdown(
                        choices=["Auto", "Mathematics", "Physics", "Chemistry", "Biology", "Geography", "History", "General Studies"],
                        value="Auto", label="Subject",
                    )
                quick_web = gr.Checkbox(
                    label="Force online verification (current facts use it automatically)", value=False,
                )
            quick_error = gr.Markdown()
            with gr.Accordion("📥 Download this visual answer", open=False, elem_classes=["download-accordion"]):
                gr.Markdown(
                    "Download a colorful printable PDF or an animated offline HTML lesson. "
                    "Each file is generated fresh for the current answer."
                )
                with gr.Row():
                    quick_pdf = gr.File(
                        label="Download colorful PDF", interactive=False, elem_classes=["study-file"],
                    )
                    quick_html = gr.File(
                        label="Download animated HTML", interactive=False, elem_classes=["study-file"],
                    )
                quick_visual_status = gr.Markdown()

        with gr.Tab("📤 Secure Upload"):
            gr.Markdown("## 📚 Upload Study Material", elem_classes=["exam-card"])
            gr.Markdown(
            "Select up to 10 PDFs or camera images together. "
                "Maximum 10 MB per file, 40 MB combined and 50 pages per PDF. "
                "Difficult handwriting automatically uses fast Gemini Vision OCR when configured. "
                "Large scanned PDFs normally need about 30–150 seconds; requests are now time-limited.",
                elem_classes=["exam-card"],
            )
            choose_files = gr.UploadButton(
                "📂 Choose PDF, HTML or Photos",
                file_types=[".pdf", ".html", ".htm", ".txt", ".png", ".jpg", ".jpeg"],
                file_count="multiple",
                type="filepath",
                elem_id="choose-study-files",
            )
            pasted_notes = gr.Textbox(label='Or paste copied subject notes here',lines=8)
            paste_process = gr.Button('📝 Process Pasted Notes',variant='primary')
            paste_status = gr.Markdown()
            study_file = gr.File(
                label="Upload up to 10 PDFs or Study Images",
                file_types=[".pdf", ".html", ".htm", ".txt", ".png", ".jpg", ".jpeg"],
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
                interactive=True,
            )
            approve_button = gr.Button("✅ Approve Corrected Text")
            approval_status = gr.Markdown()

        with gr.Tab("📖 Understand Today’s Class"):
            gr.Markdown('## Understand Today’s Class\n\n**1. Choose your PDF or notebook photos → 2. Process Class Notes → 3. Ask your question.**\n\nAlready processed notes in Secure Upload? You can ask directly below. Both tabs use the latest processed material. Source diagrams are in Smart Notes.')
            class_choose_files = gr.UploadButton(
                '📂 Choose Class PDF / HTML / Notebook Photos',
                file_types=['.pdf','.html','.htm','.txt','.png','.jpg','.jpeg'],file_count='multiple',
                type='filepath',variant='primary',
            )
            class_files = gr.File(label='Selected class files (up to 10)',
                file_types=['.pdf','.html','.htm','.txt','.png','.jpg','.jpeg'],file_count='multiple',
                type='filepath',elem_classes=['study-file'])
            class_process = gr.Button('🔍 Process Class Notes',variant='primary')
            class_upload_status = gr.Markdown('Choose files above, then press Process Class Notes. Wait for confirmation before asking.')
            class_paste = gr.Textbox(label='Or paste today’s class notes here',lines=8)
            class_paste_process = gr.Button('📝 Process Pasted Class Notes',variant='primary')
            gr.Markdown('HTML files are read as text without running scripts or loading external images. HTML source references use document 1, not actual PDF page numbers. For diagrams, also upload a PDF or image.')
            gr.Markdown('### Learn the whole chapter\n\nStories, step-by-step explanations, concept diagrams, examples and short/long practice answers. Stories are illustrative analogies, not source evidence.')
            teacher_language = gr.Dropdown(choices=LANGUAGES,value='Hinglish',label='Teaching language')
            teacher_mic = gr.Audio(sources=['microphone'],type='filepath',label='Speak your doubt')
            teacher_transcribe = gr.Button('🎙️ Convert Voice to Question')
            teacher_voice_status = gr.Markdown()
            teacher_question = gr.Textbox(label='How should I teach this chapter? (optional)',placeholder='Explain the whole chapter with stories, examples and comparisons. Give extra help with assessment vs evaluation.',lines=3)
            gr.Markdown('Full Chapter mode reads every extracted source section in order, not only the top search results. Longer chapters take multiple steps. Keep this page open; completed sections appear as they finish. A retry resumes the same notes, language and request.')
            teacher_start = gr.Button('📖 Build / Resume Full Chapter',variant='primary')
            teacher_progress = gr.Markdown()
            teacher_output = gr.HTML()
            teacher_download = gr.File(label='Download this detailed lesson as HTML',interactive=False,elem_classes=['study-file'])
            teacher_source_diagrams = gr.Gallery(label='Original source diagrams — click to zoom',columns=2,object_fit='contain')
            teacher_answer = gr.Textbox(label='Your answer — include the topic and question you are answering')
            teacher_check = gr.Button('Check my answer / give a hint')
            teacher_feedback = gr.Markdown()

        with gr.Tab("📚 Previous Papers"):
            gr.Markdown('## Match your notes with previous papers\n\nAdd verified papers with matching metadata, then compare them with your Secure Upload notes. Question-level matches include year, filename and page evidence. Files from one upload must share year, subject and syllabus. Class 7 onward only.')
            paper_board = gr.Textbox(label='Board / University (any Indian board or university)')
            paper_level = gr.Dropdown(choices=['7','8','9','10','11','12','Graduation'],value='10',label='Class / Level')
            paper_course = gr.Textbox(label='Stream / Degree / Semester',placeholder='General, Science, Commerce, Arts, BSc semester 2…')
            paper_subject = gr.Textbox(label='Subject')
            paper_syllabus = gr.Textbox(label='Syllabus version / course code — match your current syllabus')
            paper_year = gr.Number(value=2025,precision=0,label='Uploaded papers’ year')
            paper_kind = gr.Dropdown(choices=['Previous exam paper','Sample / practice paper'],value='Previous exam paper',label='Paper type (verify before selecting)')
            paper_files = gr.File(file_count='multiple',type='filepath',file_types=['.pdf','.png','.jpg','.jpeg','.txt','.html','.htm'],label='Choose verified past papers (up to 10)',elem_classes=['study-file'])
            paper_add = gr.Button('Add and extract questions',variant='primary')
            paper_status = gr.Markdown()
            with gr.Row():
                paper_catalog_export = gr.Button('⬇️ Save paper catalog')
                paper_catalog_import_file = gr.File(label='Restore saved catalog (.json.gz)',file_types=['.gz','.json'],type='filepath',elem_classes=['study-file'])
                paper_catalog_import = gr.Button('⬆️ Restore catalog')
            paper_catalog_download = gr.File(label='Download portable paper catalog',interactive=False,elem_classes=['study-file'])
            paper_catalog_transfer_status = gr.Markdown('Save the catalog after adding papers. Restore it after a Render deployment or browser restart; original paper files should still be archived separately.')
            target_exam_year = gr.Number(value=2026,precision=0,label='Target exam year')
            paper_compare = gr.Button('Prioritize my uploaded notes',variant='primary')
            paper_report = gr.Markdown()

        with gr.Tab("⚡ Exam Mode"):
            gr.Markdown(
                "## Last-Minute Exam Mode\n\nअपना available time चुनें। App केवल highest-priority revision देगा।",
                elem_classes=["exam-card"],
            )
            exam_minutes = gr.Slider(10, 60, value=15, step=5, label="Available minutes")
            exam_mode_button = gr.Button("⚡ Build My Exam Sprint", variant="primary")
            exam_mode_output = gr.Markdown("Process study material first.", elem_classes=["exam-card"])

        with gr.Tab("🃏 Flashcards"):
            flashcard_output = gr.Markdown(
                "## Swipe Flashcards\n\nProcess material, then start flashcards.",
                elem_classes=["exam-card"],
            )
            with gr.Row():
                start_flashcards = gr.Button("▶️ Start Cards")
                reveal_flashcard = gr.Button("👀 Reveal Answer", variant="primary")
                next_flashcard = gr.Button("➡️ Next Card")
            flash_progress = gr.Markdown(progress_markdown({}), elem_classes=["security-card"])

        with gr.Tab("🧠 Active Recall"):
            quiz_question = gr.Markdown(
                "## Active Recall Quiz\n\nProcess material, then start the quiz.",
                elem_classes=["exam-card"],
            )
            quiz_answer = gr.Textbox(
                label="Your answer (option number, keyword or short answer)",
                lines=2,
            )
            with gr.Row():
                start_quiz = gr.Button("▶️ Start Quiz")
                check_quiz = gr.Button("✅ Check Answer", variant="primary")
                next_quiz = gr.Button("➡️ Next Question")
            quiz_feedback = gr.Markdown()
            quiz_progress = gr.Markdown(progress_markdown({}), elem_classes=["security-card"])

        with gr.Tab("🔑 Important Topics"):
            topics_output = gr.Markdown(DEMO_TOPICS, elem_classes=["exam-card"])

        with gr.Tab("📝 Smart Notes"):
            notes_output = gr.Markdown(DEMO_NOTES, elem_classes=["exam-card"])
            with gr.Row():
                notes_language = gr.Dropdown(
                    choices=LANGUAGES,
                    value="English",
                    label="Notes language",
                )
                notes_language_button = gr.Button("🌐 Convert Notes Language")
            translation_status = gr.Markdown('AI translation: check terminology and equations against the source. Mic/OCR accuracy varies by language.')
            diagram_info = gr.Markdown(
                "## 📐 Important Diagrams\n\nUpload study material to detect source diagrams.",
                elem_classes=["exam-card"],
            )
            diagram_gallery = gr.Gallery(
                label="Original Source Diagrams — click to zoom",
                columns=2,
                object_fit="contain",
                elem_id="diagram-gallery",
            )
            diagram_challenge_button = gr.Button("🧠 Start Diagram Challenge")
            diagram_challenge = gr.Markdown(
                "Diagram process होने के बाद challenge शुरू करें।",
                elem_classes=["exam-card"],
            )

        with gr.Tab("📐 Formula Sheet"):
            formulas_output = gr.Markdown(
                "## Formula Sheet\n\nUpload study material to extract source-based formulas.",
                elem_classes=["exam-card"],
            )

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
                f"## Ask Exam Saathi · Verified Engine v{ENGINE_VERSION}\n\n"
                "Ask any standalone question or first process your PDF/photo/text for source-grounded answers. "
                "Provider routing is automatic: Perplexity (when configured) or Groq/Gemini grounds current facts; "
                "Groq/OpenAI handle detailed reasoning; Gemini remains the OCR/vision backup. Geography answers "
                "include a labelled educational SVG and clearly mark schematic maps as not to scale.",
                elem_classes=["exam-card"],
            )
            answer_language = gr.Dropdown(
                choices=SUPPORTED_LANGUAGES,
                value="Hinglish",
                label="Answer language",
            )
            voice_input = gr.Audio(
                sources=["microphone"],
                type="filepath",
                label="🎙️ Record your question — typing is optional",
            )
            transcribe_button = gr.Button("🎙️ Convert Voice to Question")
            voice_status = gr.Markdown()
            request_input = gr.Textbox(label="Your Study Question", lines=3)
            ask_button = gr.Button(
                "🚀 Ask Exam Saathi",
                variant="primary",
                elem_classes=["primary-button"],
            )
            agent_output = gr.Markdown("Agent response will appear here.", elem_classes=["exam-card"])
            agent_verification = gr.Markdown()
            with gr.Row():
                agent_pdf = gr.File(label="Download colorful PDF", interactive=False, elem_classes=["study-file"])
                agent_html = gr.File(label="Download animated HTML", interactive=False, elem_classes=["study-file"])

        with gr.Tab('💬 Smart Study Chat'):
            gr.Markdown('Ask follow-up questions about your latest processed PDF, HTML, photos or pasted notes. For images, upload/process them in Secure Upload first. Web results are labelled separately from notes.')
            chat_language=gr.Dropdown(choices=LANGUAGES,value='Hinglish',label='Answer language')
            chat_web=gr.Checkbox(value=True,label='Search online if notes are insufficient (question sent to Google; API usage applies)')
            chat_box=gr.Chatbot(label='Study conversation',height=450)
            chat_suggestions=gr.HTML()
            chat_error=gr.Markdown()
            chat_mic=gr.Audio(sources=['microphone'],type='filepath',label='Speak your question')
            chat_transcribe=gr.Button('Convert voice to question')
            chat_voice_status=gr.Markdown()
            chat_question=gr.Textbox(label='Message Exam Saathi',lines=3)
            chat_send=gr.Button('Send',variant='primary')
            chat_clear=gr.Button('New conversation')

        with gr.Tab("📅 Revision Planner"):
            planner_days = gr.Slider(1, 14, value=5, step=1, label="Days remaining")
            planner_minutes = gr.Slider(15, 180, value=45, step=15, label="Minutes per day")
            planner_button = gr.Button("📅 Create Revision Plan", variant="primary")
            planner_output = gr.Markdown("Process study material first.", elem_classes=["exam-card"])

        with gr.Tab("📱 Low Data & Share"):
            gr.Markdown("## 📘 Download Complete HTML Study Guide\n\nNotes, formulas, revision cards, questions और source diagrams एक offline file में। Sharing में source-page images भी दिखेंगी; personal details पहले check करें।")
            guide_title = gr.Textbox(label="Study guide title", value="My Smart Revision Guide")
            guide_language = gr.Dropdown(choices=LANGUAGES, value="English", label="HTML guide content language")
            guide_images = gr.Checkbox(label="Include original diagram pages (larger download)", value=True)
            guide_button = gr.Button("📘 Create Complete HTML Guide", variant="primary")
            guide_status = gr.Markdown()
            guide_file = gr.File(label="Download HTML Study Guide", interactive=False, elem_classes=["study-file"])
            gr.Markdown(
                "## Lightweight Study Pack\n\nNo diagram loading—only important text, formulas and questions.",
                elem_classes=["exam-card"],
            )
            low_data_button = gr.Button("📱 Generate Low-Data Notes")
            low_data_output = gr.Markdown(elem_classes=["exam-card"])
            friend_quiz_button = gr.Button("📤 Create Friend Quiz File")
            friend_quiz_status = gr.Markdown()
            friend_quiz_file = gr.File(label="Download and share this quiz", interactive=False, elem_classes=["study-file"])

        with gr.Tab("🛡️ Security & Privacy"):
            security_output = gr.Markdown(security_dashboard(), elem_classes=["security-card"])
            refresh_security = gr.Button("🔄 Refresh Security Status")
            gr.Markdown(
                """
## Student Data Policy

- Uploaded content is processed for the current app session.
- Low-confidence scanned documents are sent to Google Gemini for OCR when GEMINI_API_KEY is configured.
- Typed questions use automatic provider routing. Depending on configured keys, they may be sent to Groq, OpenAI, Gemini or Perplexity.
- LangGraph controls question classification, answer generation, deterministic verification, bounded retry and human-review routing.
- LangSmith tracing is optional and OFF unless `LANGSMITH_TRACING=true` is configured. Student inputs and outputs remain hidden unless an administrator explicitly enables trace content.
- Current-fact questions automatically request web grounding. Perplexity Sonar is tried first when configured, followed by Groq/Gemini web tools; online sources and verification time are listed.
- Geography SVGs are educational schematics unless exact source-backed geometry is available; they never claim surveyed boundary accuracy.
- Recorded voice is sent to Google Gemini only when the student presses Convert Voice; it is used to create the question transcript.
- The application does not intentionally publish student documents.
- Friend quiz export contains generated questions, answers and source references—not the original uploaded PDF.
- XP and weak-topic progress are session-only and are cleared when the session ends.
- Email addresses and Indian mobile numbers are masked in agent requests.
- Invalid, oversized, password-protected and unsupported files are blocked.
- Administrators should use encrypted storage and access controls before enabling permanent user accounts.
                """,
                elem_classes=["exam-card"],
            )

    teacher_transcribe.click(fn=transcribe_voice_ui,inputs=[teacher_mic,teacher_language],outputs=[teacher_question,teacher_voice_status])
    lesson_reset_outputs=[detailed_lesson,teacher_output,teacher_history,teacher_progress,
                          teacher_download,teacher_source_diagrams,teacher_feedback,teacher_answer]
    for paste_button,paste_input,paste_result in [(paste_process,pasted_notes,paste_status),(class_paste_process,class_paste,class_upload_status)]:
        paste_button.click(fn=process_pasted_ui,inputs=[paste_input],outputs=[
            paste_result,extracted_preview,ocr_status,corrected_text,topics_output,notes_output,
            diagram_info,diagram_gallery,formulas_output,questions_output,current_analysis,
            teacher_output,teacher_history,teacher_answer],show_progress='minimal').then(
                fn=reset_lesson_for_source,inputs=[current_analysis,detailed_lesson],outputs=lesson_reset_outputs)
    chat_transcribe.click(fn=transcribe_voice_ui,inputs=[chat_mic,chat_language],outputs=[chat_question,chat_voice_status])
    quick_transcribe.click(
        fn=transcribe_voice_ui,
        inputs=[quick_mic, quick_language],
        outputs=[quick_question, quick_voice_status],
        show_progress='minimal',
    )
    quick_outputs=[
        quick_chat,quick_question,quick_error,quick_pdf,quick_html,quick_visual_status,
        quick_conversations,quick_active_chat,history_picker,
    ]
    quick_inputs=[
        quick_question,quick_chat,quick_language,quick_subject,quick_web,current_analysis,
        quick_conversations,quick_active_chat,
    ]
    quick_send.click(fn=quick_solver_ui,inputs=quick_inputs,outputs=quick_outputs,show_progress='minimal')
    quick_question.submit(fn=quick_solver_ui,inputs=quick_inputs,outputs=quick_outputs,show_progress='minimal')
    sidebar_new_chat.click(
        fn=new_quick_chat_ui,inputs=[quick_conversations],outputs=quick_outputs,
    )
    history_picker.change(
        fn=open_quick_chat_ui,
        inputs=[history_picker,quick_conversations],
        outputs=[
            quick_chat,quick_question,quick_error,quick_pdf,quick_html,
            quick_visual_status,quick_active_chat,
        ],
    )
    for trigger in [chat_send.click,chat_question.submit]:
        trigger(fn=smart_chat_ui,inputs=[chat_question,chat_box,current_analysis,chat_language,chat_web],outputs=[chat_box,chat_suggestions,chat_error],show_progress='minimal')
    chat_clear.click(fn=lambda:([], '', ''),outputs=[chat_box,chat_suggestions,chat_error])
    class_choose_files.upload(fn=lambda files: files,inputs=[class_choose_files],outputs=[class_files])
    class_process.click(fn=process_class_files_ui,inputs=[class_files],outputs=[
        class_upload_status,extracted_preview,ocr_status,corrected_text,
        topics_output,notes_output,diagram_info,diagram_gallery,formulas_output,
        questions_output,current_analysis,teacher_output,teacher_history,teacher_answer,
    ],show_progress='minimal').then(fn=reset_lesson_for_source,inputs=[current_analysis,detailed_lesson],outputs=lesson_reset_outputs)
    teacher_start.click(fn=build_chapter_ui,inputs=[current_analysis,teacher_question,teacher_language,detailed_lesson],outputs=[teacher_output,teacher_history,detailed_lesson,teacher_progress,teacher_download,teacher_source_diagrams],show_progress='minimal')
    teacher_check.click(fn=lesson_feedback_ui,inputs=[current_analysis,teacher_question,teacher_language,detailed_lesson,teacher_answer],outputs=[teacher_feedback])
    paper_add.click(fn=add_papers_ui,inputs=[paper_files,paper_catalog,paper_board,paper_level,paper_course,paper_subject,paper_syllabus,paper_year,paper_kind],outputs=[paper_catalog,paper_status])
    paper_catalog_export.click(fn=export_paper_catalog_ui,inputs=[paper_catalog],outputs=[paper_catalog_download,paper_catalog_transfer_status])
    paper_catalog_import.click(fn=import_paper_catalog_ui,inputs=[paper_catalog_import_file],outputs=[paper_catalog,paper_catalog_transfer_status])
    paper_compare.click(fn=paper_priority_ui,inputs=[current_analysis,paper_catalog,paper_board,paper_level,paper_course,paper_subject,paper_syllabus,target_exam_year],outputs=[current_analysis,paper_report,notes_output,topics_output])
    choose_files.upload(fn=lambda files: files, inputs=[choose_files], outputs=[study_file])
    quick_attachment.upload(
        fn=process_home_attachment_ui,
        inputs=[quick_attachment],
        outputs=[
            upload_status, extracted_preview, ocr_status, corrected_text,
            topics_output, notes_output, diagram_info, diagram_gallery,
            formulas_output, questions_output, current_analysis,
            quick_attachment_status,
        ],
        show_progress="minimal",
    ).then(
        fn=reset_lesson_for_source,
        inputs=[current_analysis,detailed_lesson],
        outputs=lesson_reset_outputs,
    )
    process_button.click(
        fn=process_file_ui,
        inputs=[study_file],
        outputs=[
            upload_status, extracted_preview, ocr_status, corrected_text,
            topics_output, notes_output, diagram_info, diagram_gallery,
            formulas_output, questions_output, current_analysis,
        ],
        show_progress="minimal",
    ).then(fn=reset_lesson_for_source,inputs=[current_analysis,detailed_lesson],outputs=lesson_reset_outputs)
    approve_button.click(
        fn=approve_corrected_text,
        inputs=[corrected_text, current_analysis],
        outputs=[
            approval_status, topics_output, notes_output, diagram_info,
            diagram_gallery, formulas_output, questions_output, current_analysis,
        ],
        show_progress="minimal",
    ).then(fn=reset_lesson_for_source,inputs=[current_analysis,detailed_lesson],outputs=lesson_reset_outputs)
    exam_mode_button.click(
        fn=build_exam_mode,
        inputs=[current_analysis, exam_minutes],
        outputs=[exam_mode_output],
        show_progress="minimal",
    )
    start_flashcards.click(
        fn=start_flashcards_ui,
        inputs=[current_analysis, progress_state],
        outputs=[flashcard_state, flashcard_output, flash_progress],
    )
    reveal_flashcard.click(
        fn=reveal_flashcard_ui,
        inputs=[flashcard_state, progress_state],
        outputs=[flashcard_output, flash_progress, progress_state],
    )
    next_flashcard.click(
        fn=next_flashcard_ui,
        inputs=[flashcard_state],
        outputs=[flashcard_state, flashcard_output],
    )
    start_quiz.click(
        fn=start_quiz_ui,
        inputs=[current_analysis, progress_state],
        outputs=[quiz_state, quiz_question, quiz_answer, quiz_feedback, quiz_progress],
    )
    check_quiz.click(
        fn=check_quiz_ui,
        inputs=[quiz_answer, quiz_state, progress_state],
        outputs=[quiz_feedback, quiz_progress, progress_state, quiz_state],
    )
    next_quiz.click(
        fn=next_quiz_ui,
        inputs=[quiz_state],
        outputs=[quiz_state, quiz_question, quiz_answer, quiz_feedback],
    )
    diagram_challenge_button.click(
        fn=diagram_learning_markdown,
        inputs=[current_analysis],
        outputs=[diagram_challenge],
    )
    notes_language_button.click(
        fn=translate_study_ui,
        inputs=[current_analysis, notes_language],
        outputs=[current_analysis, notes_output, topics_output, questions_output, translation_status],
        show_progress="minimal",
    )
    transcribe_button.click(
        fn=transcribe_voice_ui,
        inputs=[voice_input, answer_language],
        outputs=[request_input, voice_status],
        show_progress="minimal",
    )
    ask_button.click(
        fn=ask_agent_ui,
        inputs=[request_input, current_analysis, answer_language],
        outputs=[agent_output, agent_verification, agent_pdf, agent_html],
        show_progress="minimal",
    )
    request_input.submit(
        fn=ask_agent_ui,
        inputs=[request_input, current_analysis, answer_language],
        outputs=[agent_output, agent_verification, agent_pdf, agent_html],
        show_progress="minimal",
    )
    planner_button.click(
        fn=build_revision_plan,
        inputs=[current_analysis, planner_days, planner_minutes],
        outputs=[planner_output],
    )
    low_data_button.click(
        fn=low_data_markdown,
        inputs=[current_analysis],
        outputs=[low_data_output],
    )
    friend_quiz_button.click(
        fn=export_friend_quiz_ui,
        inputs=[current_analysis],
        outputs=[friend_quiz_file, friend_quiz_status],
    )
    guide_button.click(
        fn=export_study_guide_ui,
        inputs=[current_analysis, guide_title, guide_images, guide_language,detailed_lesson],
        outputs=[guide_file, guide_status],
        show_progress="minimal",
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
            font=[
                gr.themes.GoogleFont("Inter"),
                gr.themes.GoogleFont("Noto Sans"),
                "Arial",
                "sans-serif",
            ],
        ),
        css=CUSTOM_CSS,
        auth=APP_AUTH,
        auth_message="Exam Saathi is private. Enter the credentials shared by the project owner.",
    )
