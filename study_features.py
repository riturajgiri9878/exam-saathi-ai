"""Session-only Gen-Z study modes for Exam Saathi AI."""

from __future__ import annotations

import html
import re
import tempfile
import uuid
import unicodedata
from pathlib import Path
from typing import Any


def _source(item: dict[str, Any]) -> str:
    return f"{item.get('source_name', 'Uploaded notes')} | Page {item.get('page_number', '?')}"


def build_flashcards(result: dict[str, Any]) -> list[dict[str, str]]:
    cards: list[dict[str, str]] = []
    for note in result.get("notes", []):
        cards.append({
            "question": f"इस important point को अपने शब्दों में explain करो (Note {note['note_number']}).",
            "answer": note["text"],
            "source": _source(note),
        })
    for formula in result.get("formulas", [])[:6]:
        cards.append({
            "question": "इस source formula को पहचानो और इसका उपयोग याद करो।",
            "answer": formula["formula"],
            "source": _source(formula),
        })
    return cards[:14]


def flashcard_view(state: dict[str, Any], reveal: bool = False) -> str:
    cards = state.get("cards", [])
    if not cards:
        return "## 🃏 Flashcards\n\nपहले study material process करें।"
    index = int(state.get("index", 0)) % len(cards)
    card = cards[index]
    output = (
        f"## 🃏 Card {index + 1}/{len(cards)}\n\n"
        f"### प्रश्न\n\n{card['question']}\n\n"
    )
    if reveal:
        output += (
            f"### उत्तर\n\n{card['answer']}\n\n"
            f"📄 **Source:** {card['source']}"
        )
    else:
        output += "उत्तर सोचने के बाद **Reveal Answer** दबाएँ।"
    return output


def build_quiz_items(result: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for item in result.get("question_bank", {}).get("mcq_questions", []):
        raw_options = item.get("options", [])
        options = "\n".join(
            f"{number}. {option}" for number, option in enumerate(raw_options, 1)
        )
        accepted_answers = [item["answer"]]
        for number, option in enumerate(raw_options, 1):
            if str(option).strip().lower() == str(item["answer"]).strip().lower():
                accepted_answers.append(str(number))
        items.append({
            "question": f"{item['question']}\n\n{options}",
            "answer": item["answer"],
            "accepted_answers": accepted_answers,
            "source": _source(item),
        })
    if not items:
        notes = result.get("notes", [])
        questions = result.get("question_bank", {}).get("short_questions", [])
        for index, question in enumerate(questions):
            if notes:
                note = notes[index % len(notes)]
                items.append({
                    "question": question,
                    "answer": note["text"],
                    "accepted_answers": [note["text"]],
                    "source": _source(note),
                })
    return items[:10]


def quiz_view(state: dict[str, Any]) -> str:
    items = state.get("items", [])
    if not items:
        return "## 🧠 Active Recall Quiz\n\nपहले study material process करें।"
    index = int(state.get("index", 0)) % len(items)
    return f"## 🧠 Question {index + 1}/{len(items)}\n\n{items[index]['question']}"


def answer_matches(student_answer: str, expected_answer: str) -> bool:
    # Quiz options need exact matches; partial token overlap incorrectly awards
    # marks to answers such as 'not Newton'. Keep all Indian-script marks.
    def normalize(value):
        return ' '.join(unicodedata.normalize('NFC', value or '').casefold().split()).strip(' .।')
    student, expected = normalize(student_answer), normalize(expected_answer)
    return bool(student and expected and student == expected)


def progress_markdown(progress: dict[str, Any]) -> str:
    attempted = int(progress.get("attempted", 0))
    correct = int(progress.get("correct", 0))
    accuracy = round(correct * 100 / attempted) if attempted else 0
    weak = progress.get("weak_topics", [])[-5:]
    weak_line = ", ".join(weak) if weak else "अभी कोई weak topic नहीं"
    return (
        "## 🔥 Session Progress\n\n"
        f"- **XP:** {int(progress.get('xp', 0))}\n"
        f"- **Questions attempted:** {attempted}\n"
        f"- **Accuracy:** {accuracy}%\n"
        f"- **Review again:** {weak_line}\n\n"
        "Progress इस browser session तक रहता है; permanent student accounts अगले phase में आएँगे।"
    )


def build_exam_mode(result: dict[str, Any], minutes: int) -> str:
    if not result.get("documents"):
        return "## ⚡ Exam Mode\n\nपहले PDF या notebook images process करें।"
    minutes = int(minutes)
    limits = (3, 2, 2) if minutes <= 15 else (6, 4, 4) if minutes <= 30 else (8, 6, 6)
    topics = result.get("topics", [])[:limits[0]]
    formulas = result.get("formulas", [])[:limits[1]]
    questions = result.get("question_bank", {}).get("short_questions", [])[:limits[2]]
    notes = result.get("notes", [])[:limits[0]]
    output = (
        f"## ⚡ {minutes}-Minute Exam Mode\n\n"
        "### अभी इसी order में पढ़ें\n\n"
        f"1. **{max(3, minutes // 3)} min:** Important topics और notes\n"
        f"2. **{max(2, minutes // 4)} min:** Formulas/diagrams\n"
        "3. **बाकी समय:** Active recall questions\n\n"
        "### Priority Topics\n\n"
    )
    output += "\n".join(f"- **{item['topic']}**" for item in topics) or "- No topics"
    output += "\n\n### Quick Notes\n\n"
    output += "\n".join(
        f"- {item['text']}  \n  📄 {_source(item)}" for item in notes
    ) or "- No notes"
    output += "\n\n### Formula Sprint\n\n"
    output += "\n".join(f"- `{item['formula']}` — {_source(item)}" for item in formulas) or "- No formula"
    output += "\n\n### Test Yourself\n\n"
    output += "\n".join(f"{number}. {question}" for number, question in enumerate(questions, 1)) or "No questions"
    return output


def build_revision_plan(result: dict[str, Any], days: int, minutes_per_day: int) -> str:
    topics = [item["topic"] for item in result.get("topics", [])]
    if not topics:
        return "## 📅 Revision Plan\n\nपहले study material process करें।"
    days = max(1, int(days))
    minutes_per_day = max(10, int(minutes_per_day))
    output = f"## 📅 {days}-Day Smart Revision Plan\n\n"
    for day in range(1, days + 1):
        first = topics[(day - 1) % len(topics)]
        second = topics[day % len(topics)] if len(topics) > 1 else first
        output += (
            f"### Day {day}\n\n"
            f"- **{minutes_per_day // 2} min:** {first}\n"
            f"- **{minutes_per_day // 4} min:** {second}\n"
            f"- **{minutes_per_day - (minutes_per_day // 2 + minutes_per_day // 4)} min:** "
            "Flashcards + Active Recall\n\n"
        )
    return output


def diagram_learning_markdown(result: dict[str, Any]) -> str:
    diagrams = result.get("diagrams", [])
    if not diagrams:
        return "## 📐 Diagram Learning\n\nकोई diagram page उपलब्ध नहीं है।"
    output = "## 📐 Diagram Challenge\n\nImage को पहले देखें, फिर answer खोलें।\n\n"
    for index, item in enumerate(diagrams[:8], 1):
        answer = html.escape(item.get("description", "Original source diagram"))
        output += (
            f"### Challenge {index}\n\n"
            f"**{html.escape(item['source_name'])} — Page {item['page_number']} में बने "
            "diagram का concept और visible labels पहचानो।**\n\n"
            f"<details><summary>Answer / Explanation देखें</summary>{answer}</details>\n\n"
        )
    return output


def low_data_markdown(result: dict[str, Any]) -> str:
    if not result.get("documents"):
        return "## 📱 Low-Data Notes\n\nपहले material process करें।"
    output = "## 📱 Low-Data Revision Pack\n\n"
    output += "### Topics\n" + "\n".join(
        f"- {item['topic']}" for item in result.get("topics", [])[:8]
    )
    output += "\n\n### Notes\n" + "\n".join(
        f"- {item['text']} ({_source(item)})" for item in result.get("notes", [])[:8]
    )
    output += "\n\n### Formulas\n" + "\n".join(
        f"- {item['formula']}" for item in result.get("formulas", [])[:8]
    )
    return output


def export_friend_quiz(result: dict[str, Any]) -> str:
    items = build_quiz_items(result)
    if not items:
        raise ValueError("Generate study material before exporting a friend quiz.")
    output_dir = Path(tempfile.gettempdir()) / "exam_saathi_exports"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"friend_quiz_{uuid.uuid4().hex[:10]}.html"
    cards = ""
    for index, item in enumerate(items, 1):
        cards += (
            f"<section><h2>Question {index}</h2><p>{html.escape(item['question'])}</p>"
            f"<details><summary>Show answer</summary><p>{html.escape(item['answer'])}</p>"
            f"<small>Source: {html.escape(item['source'])}</small></details></section>"
        )
    document = f"""<!doctype html><html><head><meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Exam Saathi Friend Quiz</title><style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Noto+Sans:wght@400;500;600;700&display=swap');body{{font-family:Inter,"Noto Sans",Arial,sans-serif;max-width:760px;margin:auto;padding:20px;background:#eef2ff;color:#172033}}
section{{background:white;padding:18px;margin:16px 0;border-radius:16px;border:1px solid #cbd5e1}}
summary{{cursor:pointer;font-weight:800;color:#4338ca}}small{{color:#475569}}
</style></head><body><h1>🧠 Exam Saathi Friend Quiz</h1>{cards}</body></html>"""
    output_path.write_text(document, encoding="utf-8")
    return str(output_path)
