"""Verified question answering and fresh visual exports for Exam Saathi AI.

This module deliberately separates four jobs:
1. route the question to the right tools;
2. produce a complete teaching answer;
3. independently review/correct the draft;
4. create new, cache-safe HTML and PDF files for that exact answer.

The engine never labels an answer as verified merely because a model sounded
confident. Current/unique factual claims require grounded web sources, numeric
STEM problems require code execution, and uploaded-note answers retain their
filename/page evidence.
"""

from __future__ import annotations

import base64
import hashlib
import html
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import pymupdf


ENGINE_VERSION = "4.4.0"
ANSWER_PROVIDER = os.environ.get("ANSWER_PROVIDER", "auto").strip().lower()
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_REASONING_MODEL = os.environ.get(
    "GROQ_REASONING_MODEL", "openai/gpt-oss-120b"
).strip()
GROQ_WEB_MODEL = os.environ.get("GROQ_WEB_MODEL", "groq/compound").strip()
GROQ_COMPOUND_FALLBACK_MODEL = os.environ.get(
    "GROQ_COMPOUND_FALLBACK_MODEL", "groq/compound-mini"
).strip()
GROQ_FALLBACK_MODEL = os.environ.get(
    "GROQ_FALLBACK_MODEL", "openai/gpt-oss-20b"
).strip()
GEMINI_ANSWER_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash").strip()
GEMINI_FALLBACK_MODELS = [
    item.strip()
    for item in os.environ.get("GEMINI_FALLBACK_MODELS", "gemini-3.6-flash").split(",")
    if item.strip()
]
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"
PERPLEXITY_MODEL = os.environ.get("PERPLEXITY_MODEL", "sonar").strip()
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "").strip()
ANSWER_TIMEOUT_SECONDS = int(os.environ.get("ANSWER_TIMEOUT_SECONDS", "75"))
GROQ_TIMEOUT_SECONDS = max(30, int(os.environ.get("GROQ_TIMEOUT_SECONDS", "60")))
MAX_QUESTION_CHARACTERS = int(os.environ.get("MAX_QUESTION_CHARACTERS", "12000"))
MAX_RAG_CHARACTERS = int(os.environ.get("MAX_RAG_CHARACTERS", "18000"))
ARTIFACT_DIR = Path(os.environ.get("ANSWER_ARTIFACT_DIR", "/tmp/exam_saathi_answers"))


SUPPORTED_LANGUAGES = [
    "English", "Hindi", "Hinglish", "Assamese", "Bengali", "Bodo", "Dogri",
    "Gujarati", "Kannada", "Kashmiri", "Konkani", "Maithili", "Malayalam",
    "Manipuri (Meitei)", "Marathi", "Nepali", "Odia", "Punjabi", "Sanskrit",
    "Santali", "Sindhi", "Tamil", "Telugu", "Urdu",
]


SUBJECT_PATTERNS: list[tuple[str, tuple[str, ...]]] = [
    ("Mathematics", ("solve", "equation", "integral", "derivative", "matrix", "probability", "sqrt", "sin", "cos", "tan", "algebra", "geometry", "calculus", "गणित")),
    ("Physics", ("force", "velocity", "acceleration", "charge", "electric", "magnetic", "oscillation", "time period", "momentum", "quantum", "physics", "भौतिक")),
    ("Chemistry", ("reaction", "compound", "molecule", "organic", "inorganic", "equilibrium", "molar", "acid", "base", "ozonolysis", "chemistry", "रसायन")),
    ("Biology", ("cell", "dna", "rna", "gene", "protein", "organism", "anatomy", "physiology", "biology", "जीवविज्ञान")),
    ("Geography", (
        "country", "enclave", "exclave", "river", "mountain", "climate", "desert",
        "volcano", "earthquake", "monsoon", "rain shadow", "trade wind", "ocean current",
        "latitude", "longitude", "population", "migration", "mineral", "industry",
        "plate tectonic", "drainage", "soil", "map", "geography", "भूगोल", "मानसून",
        "नदी", "पर्वत", "ज्वालामुखी", "जनसंख्या",
    )),
    ("History", ("empire", "dynasty", "war", "revolution", "history", "इतिहास")),
    ("Civics / Current Affairs", ("prime minister", "president", "chief minister", "parliament", "constitution", "government", "current affairs", "प्रधानमंत्री", "राष्ट्रपति")),
    ("Computer Science", ("algorithm", "python", "code", "database", "vector", "embedding", "computer", "programming")),
    ("English", ("grammar", "poem", "prose", "noun", "verb", "essay", "english")),
]

WEB_RISK_TERMS = (
    "current", "currently", "latest", "today", "now", "present", "recent",
    "world's only", "only remaining", "first ever", "largest", "smallest",
    "prime minister", "president", "chief minister", "ceo", "winner", "2026",
    "वर्तमान", "आज", "अभी", "प्रधानमंत्री", "राष्ट्रपति", "सबसे बड़ा", "एकमात्र",
)

GEOGRAPHY_TYPE_PATTERNS: list[tuple[str, tuple[str, ...]]] = [
    ("Political Geography", ("border", "boundary", "country", "capital", "enclave", "exclave", "territory", "sovereignty")),
    ("Current Geography", ("flood", "cyclone", "earthquake today", "eruption", "disaster", "current geography", "latest")),
    ("Human Geography", ("population", "migration", "urban", "settlement", "density", "demographic")),
    ("Economic Geography", ("mineral", "industry", "agriculture", "trade", "resource", "transport")),
    ("Indian Geography", ("india", "indian", "भारत", "गंगा", "हिमालय", "deccan", "western ghats")),
    ("Map / Location", ("map", "locate", "latitude", "longitude", "coordinate", "where is")),
    ("Physical Geography", ("volcano", "earthquake", "monsoon", "rain shadow", "climate", "desert", "river", "mountain", "plate", "ocean current")),
]

OFFICIAL_SOURCE_DOMAINS = (
    ".gov.in", "pib.gov.in", "rbi.org.in", "isro.gov.in", "eci.gov.in",
    "sci.gov.in", "ncert.nic.in", "cbse.gov.in", "censusindia.gov.in",
    "imd.gov.in", "gsi.gov.in", "bhuvan.nrsc.gov.in", "un.org",
    "worldbank.org", "nasa.gov", "usgs.gov",
)
TRUSTED_SOURCE_DOMAINS = (
    "reuters.com", "apnews.com", "bbc.com", "britannica.com", "nature.com",
    "science.org", "nationalgeographic.com",
)

CALCULATION_TERMS = (
    "calculate", "solve", "find", "evaluate", "derive", "prove", "exact value",
    "time period", "maximum speed", "rate constant", "equilibrium", "molar",
    "गणना", "हल करो", "निकालो", "मान ज्ञात",
)


@dataclass
class ToolRoute:
    subject: str
    use_web: bool
    use_code: bool
    use_rag: bool
    high_risk_fact: bool
    geography_type: str = ""
    visual_type: str = "concept"
    source_policy: str = "standard"
    freshness_required: bool = False


def detect_subject(question: str) -> str:
    lowered = question.casefold()
    scores = {
        subject: sum(1 for term in terms if term in lowered)
        for subject, terms in SUBJECT_PATTERNS
    }
    best = max(scores, key=scores.get)
    return best if scores[best] else "General Studies"


def detect_geography_type(question: str) -> str:
    lowered = question.casefold()
    scores = {
        geography_type: sum(1 for term in terms if term in lowered)
        for geography_type, terms in GEOGRAPHY_TYPE_PATTERNS
    }
    best = max(scores, key=scores.get)
    return best if scores[best] else "General Geography"


def _geography_visual_type(question: str, geography_type: str) -> str:
    lowered = question.casefold()
    if "enclave" in lowered or "exclave" in lowered:
        return "nested"
    if any(term in lowered for term in ("volcano", "rain shadow", "thermal inversion", "mountain")):
        return "cross_section"
    if any(term in lowered for term in ("monsoon", "trade wind", "ocean current", "wind")):
        return "wind_map"
    if any(term in lowered for term in ("river", "drainage", "tributary")):
        return "drainage"
    if any(term in lowered for term in ("population", "density", "distribution")):
        return "choropleth"
    if any(term in lowered for term in ("plate", "earthquake")):
        return "plates"
    if geography_type in {"Political Geography", "Map / Location", "Indian Geography"}:
        return "map"
    return "flow"


def choose_tools(question: str, rag_context: list[dict[str, Any]] | None = None) -> ToolRoute:
    lowered = question.casefold()
    subject = detect_subject(question)
    has_rag = bool(rag_context)
    current_year = int(time.strftime("%Y", time.gmtime()))
    mentioned_years = [int(value) for value in re.findall(r"\b20\d{2}\b", lowered)]
    recent_year = any(year >= current_year - 1 for year in mentioned_years)
    high_risk_fact = any(term in lowered for term in WEB_RISK_TERMS) or recent_year
    # Static textbook/general-knowledge questions do not need a slow live web
    # tool call. Current, unique, superlative and office-holder claims still do.
    use_web = high_risk_fact
    use_code = any(term in lowered for term in CALCULATION_TERMS)
    use_code = use_code or bool(re.search(r"[=+\-*/^]|\\frac|\\sqrt|\d", question)) and subject in {
        "Mathematics", "Physics", "Chemistry", "Computer Science"
    }
    geography_type = detect_geography_type(question) if subject == "Geography" else ""
    visual_type = _geography_visual_type(question, geography_type) if geography_type else "concept"
    government_fact = any(term in lowered for term in (
        "government", "prime minister", "president", "chief minister", "repo rate",
        "scheme", "minister", "सरकार", "प्रधानमंत्री", "राष्ट्रपति", "मुख्यमंत्री",
    ))
    source_policy = "official_government" if government_fact and high_risk_fact else (
        "authoritative_geography" if geography_type and high_risk_fact else (
            "multi_source" if high_risk_fact else "standard"
        )
    )
    return ToolRoute(
        subject=subject,
        use_web=use_web,
        use_code=use_code,
        use_rag=has_rag,
        high_risk_fact=high_risk_fact,
        geography_type=geography_type,
        visual_type=visual_type,
        source_policy=source_policy,
        freshness_required=recent_year or any(term in lowered for term in (
            "current", "currently", "latest", "today", "now", "present", "recent",
            "वर्तमान", "आज", "अभी",
        )),
    )


def _clean_question(question: str) -> str:
    value = (question or "").strip()
    if not value:
        raise ValueError("Please enter a question.")
    if len(value) > MAX_QUESTION_CHARACTERS:
        raise ValueError(f"Question is too long. Maximum {MAX_QUESTION_CHARACTERS} characters.")
    return value


def _safe_language(language: str) -> str:
    return language if language in SUPPORTED_LANGUAGES else "Hinglish"


def _rag_block(rag_context: list[dict[str, Any]] | None) -> tuple[str, list[dict[str, str]]]:
    if not rag_context:
        return "No uploaded source evidence was supplied for this question.", []
    blocks: list[str] = []
    sources: list[dict[str, str]] = []
    used = 0
    for item in rag_context:
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        source_name = str(item.get("source_name", "Uploaded material"))
        page = str(item.get("page_number", "?"))
        block = f"[SOURCE: {source_name} | PAGE: {page}]\n{text}"
        if used + len(block) > MAX_RAG_CHARACTERS:
            break
        blocks.append(block)
        sources.append({"title": f"{source_name} - page {page}", "uri": ""})
        used += len(block)
    return "\n\n".join(blocks) or "No usable uploaded evidence was found.", sources


def _payload_schema_instruction() -> str:
    return """
Return ONLY one valid JSON object with these keys:
{
  "title": "short useful title",
  "subject": "subject",
  "direct_answer": "direct answer, or clearly state inconsistent/insufficient data",
  "beginner_explanation": "simple story/mental model without replacing scientific proof",
  "steps": [{"heading": "Step 1", "body": "complete reasoning with readable equations"}],
  "worked_example": "worked example/application, or Not applicable",
  "key_facts": ["fact"],
  "why_it_matters": "why this matters for the student or exam",
  "exam_perspective": "how the topic is commonly tested",
  "common_mistakes": ["mistake and correction"],
  "final_answer": "concise exam-ready answer",
  "short_questions": ["2 to 4 useful short practice questions"],
  "long_questions": ["1 to 3 important long-answer questions"],
  "mcqs": [{"question": "question", "options": ["A", "B", "C", "D"], "answer": "correct option with reason"}],
  "geography": {
    "type": "Physical|Political|Human|Economic|Indian|Map|Current|Not applicable",
    "important_locations": ["location and why it matters"],
    "data_year": "year for population/climate/current data, or Not applicable",
    "boundary_note": "neutral note for disputed or changing boundaries, or Not applicable",
    "map_note": "Verified map data used, or Schematic/not to scale"
  },
  "diagram": {
    "kind": "nested|flow|force|reaction|cycle|timeline|equation|concept|cross_section|wind_map|drainage|choropleth|plates|map",
    "title": "diagram title",
    "nodes": ["short accurate label"],
    "edges": ["short relationship label"],
    "accuracy_note": "Schematic/not to scale unless verified coordinates or geometry were actually used"
  },
  "verification_status": "VERIFIED|REVIEW_NEEDED|INSUFFICIENT",
  "confidence": 0,
  "verification_notes": ["what was independently checked"]
}
Do not add Markdown fences around the JSON.
"""


def _build_solver_prompt(
    question: str,
    language: str,
    route: ToolRoute,
    rag_text: str,
) -> str:
    return f"""You are Exam Saathi's senior teacher and careful problem solver.

QUESTION:
{question}

REQUESTED ANSWER LANGUAGE: {language}
DETECTED SUBJECT: {route.subject}
GEOGRAPHY TYPE: {route.geography_type or 'Not applicable'}
RECOMMENDED VISUAL: {route.visual_type}
SOURCE POLICY: {route.source_policy}
FRESHNESS REQUIRED: {route.freshness_required}
CURRENT DATE (UTC): {time.strftime('%Y-%m-%d', time.gmtime())}
UPLOADED EVIDENCE:
{rag_text}

Non-negotiable rules:
1. First test whether the question's premise and given data are internally consistent.
2. Never force a numerical or structural answer from contradictory or insufficient data.
3. For mathematics/physics/chemistry, check every expansion, unit, sign, stoichiometric change,
   domain restriction and final substitution. Use code execution when available.
4. For current, superlative, unique, office-holder or political/geography facts, use web search
   and cross-check with authoritative sources. Do not trust the wording of the question.
5. If uploaded evidence is used, cite its exact filename and page in the answer. Distinguish
   evidence from general knowledge and never invent a page number.
6. Explain beginner-to-exam level: direct answer -> mental model -> rigorous steps -> worked
   example -> mistakes -> final answer -> short and long practice.
7. Use {language}. Keep standard technical terms in English in parentheses where helpful.
8. Equations must be valid readable LaTeX using $...$ or $$...$$. Recalculate arithmetic.
9. The diagram labels must be specific to this exact question, never generic labels such as
   Core idea, Mechanism or Application.
10. Confidence is not proof. Set VERIFIED only when the requested checks actually succeeded.
11. For Geography, identify the exact geography type. Include named locations, controlling
    physical/human processes, scale and data year. Use a cross-section, wind map, drainage,
    choropleth, plate or nesting visual when appropriate.
12. Never invent a political boundary or pretend a schematic SVG is a surveyed map. If exact
    verified coordinates/geometry were not supplied by a source, label the visual Schematic / not
    to scale. Treat disputed boundaries neutrally.
13. For current affairs, include why it matters, exam perspective, the verification date and
    source-supported facts. Do not answer a current fact from model memory alone.

{_payload_schema_instruction()}"""


def _build_review_prompt(
    question: str,
    language: str,
    route: ToolRoute,
    rag_text: str,
    draft: dict[str, Any],
) -> str:
    return f"""Act as an independent examiner and fact-checker. Correct the draft below before
it reaches a student. Do not merely agree with it.

ORIGINAL QUESTION:
{question}

REQUESTED LANGUAGE: {language}
SUBJECT: {route.subject}
GEOGRAPHY TYPE: {route.geography_type or 'Not applicable'}
SOURCE POLICY: {route.source_policy}
UPLOADED EVIDENCE:
{rag_text}

DRAFT JSON:
{json.dumps(draft, ensure_ascii=False)}

Audit requirements:
- Re-solve the problem independently.
- Explicitly challenge words like only, always, first, largest, current and unique.
- For numeric STEM, independently compute the final result and inspect every intermediate step.
- For chemistry, verify formulae, named tests, reaction feasibility, products and whether the
  supplied observations uniquely determine a structure.
- For physics, verify vector direction, sign, dimensions, approximations and assumptions.
- For factual/current questions, search and prefer official/primary sources; compare at least
  two sources when the claim is exceptional or disputed.
- If data conflict, the correct answer is to explain the conflict, not invent missing facts.
- Return a corrected, complete teaching payload, not just a list of criticisms.
- Preserve exact uploaded filename/page citations when they truly support a claim.
- Produce a question-specific diagram specification.
- For Geography, reject invented borders, locations, directions and data years. Check the visual
  type and require Schematic / not to scale unless source-backed geometry was actually used.
- For current affairs, ensure every changing claim is tied to a source and date.

{_payload_schema_instruction()}"""


def _parse_json(text: str) -> dict[str, Any]:
    raw = (text or "").strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\s*```$", "", raw)
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("The model did not return a structured answer.")
        value = json.loads(raw[start:end + 1])
    if not isinstance(value, dict):
        raise ValueError("The model returned an invalid answer object.")
    return value


def _response_sources(response: Any) -> list[dict[str, str]]:
    sources: list[dict[str, str]] = []
    try:
        metadata = response.candidates[0].grounding_metadata
        chunks = getattr(metadata, "grounding_chunks", None) or []
        for chunk in chunks:
            web = getattr(chunk, "web", None)
            uri = str(getattr(web, "uri", "") or "")
            title = str(getattr(web, "title", "") or uri)
            if uri and urlparse(uri).scheme in {"http", "https"}:
                item = {"title": title, "uri": uri}
                if item not in sources:
                    sources.append(item)
    except (AttributeError, IndexError, TypeError):
        pass
    return sources


def _response_used_code(response: Any) -> bool:
    try:
        parts = response.candidates[0].content.parts or []
        return any(getattr(part, "code_execution_result", None) is not None for part in parts)
    except (AttributeError, IndexError, TypeError):
        return False


def _groq_sources(response: dict[str, Any]) -> list[dict[str, str]]:
    """Extract citation URLs from current and older Compound response shapes."""
    sources: list[dict[str, str]] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            uri = str(value.get("url") or value.get("uri") or "").strip()
            title = str(value.get("title") or value.get("name") or uri).strip()
            if uri and urlparse(uri).scheme in {"http", "https"}:
                item = {"title": title or uri, "uri": uri}
                if item not in sources:
                    sources.append(item)
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    try:
        message = response["choices"][0]["message"]
    except (KeyError, IndexError, TypeError):
        message = {}
    walk(message.get("citations", []))
    walk(message.get("executed_tools", []))
    walk(response.get("citations", []))
    return sources


def _groq_used_code(response: dict[str, Any]) -> bool:
    try:
        tools = response["choices"][0]["message"].get("executed_tools", [])
    except (KeyError, IndexError, TypeError, AttributeError):
        return False
    for item in tools if isinstance(tools, list) else []:
        item_text = json.dumps(item, ensure_ascii=False).casefold()
        if any(term in item_text for term in (
            "code_interpreter", "code execution", '"type": "code"', "wolfram_alpha"
        )):
            return True
    return False


def _provider_error_text(error: Exception) -> str:
    """Return a short, actionable error without leaking credentials."""
    raw = str(error).replace("\n", " ")
    if isinstance(error, HTTPError):
        try:
            raw = error.read().decode("utf-8", errors="replace")
        except Exception:
            raw = str(error)
    lowered = raw.casefold()
    if "429" in raw or "resource_exhausted" in lowered or "rate limit" in lowered or "quota" in lowered:
        return "free quota/rate limit reached"
    if "401" in raw or "403" in raw or "api key" in lowered or "unauthorized" in lowered:
        return "API key is missing, invalid, or not permitted"
    if isinstance(error, (TimeoutError, URLError)) or "timed out" in lowered or "timeout" in lowered:
        return "provider timed out"
    if "404" in raw or "not_found" in lowered or "not found" in lowered:
        return "configured model is unavailable"
    return re.sub(
        r"(?i)(bearer\s+|api[_ -]?key[=: ]+)[^\s,;]+", r"\1[hidden]", raw
    )[:180]


def _groq_generate(prompt: str, use_web: bool, use_code: bool) -> tuple[str, list[dict[str, str]], bool, str]:
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured.")

    # The free GPT-OSS tier has a smaller per-minute token budget than Compound.
    # Route long uploaded-note/reviewer prompts to Compound as well, so a valid
    # answer is not rejected merely because the context is large.
    compound_request = use_web or use_code or len(prompt) > 16000
    if use_web and not use_code:
        # Compound Mini needs only one web-search call for a current fact and
        # is substantially faster than starting the full multi-tool system.
        models = [GROQ_COMPOUND_FALLBACK_MODEL, GROQ_WEB_MODEL]
    elif compound_request:
        models = [GROQ_WEB_MODEL, GROQ_COMPOUND_FALLBACK_MODEL]
    else:
        models = [GROQ_REASONING_MODEL, GROQ_FALLBACK_MODEL]
    errors: list[str] = []
    for model in list(dict.fromkeys(item for item in models if item)):
        payload: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_completion_tokens": 6500 if compound_request else 3200,
            "response_format": {"type": "json_object"},
            "citation_options": "enabled",
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Groq-Model-Version": "latest",
            "User-Agent": f"Exam-Saathi/{ENGINE_VERSION}",
        }
        if model.startswith("groq/compound"):
            enabled_tools: list[str] = []
            if use_web:
                enabled_tools.append("web_search")
            if use_code:
                enabled_tools.extend(["code_interpreter", "wolfram_alpha"])
            if enabled_tools:
                payload["compound_custom"] = {
                    "tools": {"enabled_tools": list(dict.fromkeys(enabled_tools))}
                }
        elif model.startswith("openai/gpt-oss"):
            payload["reasoning_effort"] = "medium"

        request = Request(
            GROQ_API_URL,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urlopen(request, timeout=GROQ_TIMEOUT_SECONDS) as response:
                value = json.loads(response.read().decode("utf-8"))
            message = value["choices"][0]["message"]
            content = str(message.get("content", "")).strip()
            if not content:
                raise RuntimeError("empty model response")
            return content, _groq_sources(value), _groq_used_code(value), f"groq:{model}"
        except Exception as error:
            errors.append(f"{model}: {_provider_error_text(error)}")
    raise RuntimeError("Groq unavailable. " + " | ".join(errors))


def _gemini_generate(prompt: str, use_web: bool, use_code: bool) -> tuple[str, list[dict[str, str]], bool, str]:
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured.")
    from google import genai
    from google.genai import types

    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=ANSWER_TIMEOUT_SECONDS * 1000),
    )
    tools: list[Any] = []
    if use_web:
        tools.append(types.Tool(google_search=types.GoogleSearch()))
    if use_code:
        tools.append(types.Tool(code_execution=types.ToolCodeExecution))

    config = types.GenerateContentConfig(
        temperature=0.1,
        max_output_tokens=12000,
        response_mime_type="application/json",
        tools=tools or None,
    )
    errors: list[str] = []
    models = list(dict.fromkeys([GEMINI_ANSWER_MODEL, *GEMINI_FALLBACK_MODELS]))[:2]
    for model in models:
        try:
            response = client.models.generate_content(model=model, contents=prompt, config=config)
            if not getattr(response, "text", ""):
                raise RuntimeError("empty model response")
            return response.text, _response_sources(response), _response_used_code(response), f"gemini:{model}"
        except Exception as error:  # provider exceptions vary across SDK releases
            errors.append(f"{model}: {_provider_error_text(error)}")
    raise RuntimeError("Gemini unavailable. " + " | ".join(errors))


def _perplexity_sources(response: dict[str, Any]) -> list[dict[str, str]]:
    sources: list[dict[str, str]] = []
    search_results = response.get("search_results", [])
    if isinstance(search_results, list):
        for item in search_results:
            if not isinstance(item, dict):
                continue
            uri = str(item.get("url") or item.get("uri") or "").strip()
            title = str(item.get("title") or uri).strip()
            if uri and urlparse(uri).scheme in {"http", "https"}:
                sources.append({"title": title or uri, "uri": uri})
    citations = response.get("citations", [])
    if isinstance(citations, list):
        for citation in citations:
            if isinstance(citation, str):
                uri, title = citation.strip(), citation.strip()
            elif isinstance(citation, dict):
                uri = str(citation.get("url") or citation.get("uri") or "").strip()
                title = str(citation.get("title") or uri).strip()
            else:
                continue
            if uri and urlparse(uri).scheme in {"http", "https"}:
                sources.append({"title": title or uri, "uri": uri})
    return _dedupe_sources(sources)


def _perplexity_generate(prompt: str, use_web: bool, use_code: bool) -> tuple[str, list[dict[str, str]], bool, str]:
    """Ground current/GK/geography claims with Perplexity Sonar when configured."""
    api_key = os.environ.get("PERPLEXITY_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("PERPLEXITY_API_KEY is not configured.")
    payload = {
        "model": PERPLEXITY_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 6500,
    }
    request = Request(
        PERPLEXITY_API_URL,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": f"Exam-Saathi/{ENGINE_VERSION}",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=ANSWER_TIMEOUT_SECONDS) as response:
            value = json.loads(response.read().decode("utf-8"))
        content = str(value["choices"][0]["message"].get("content", "")).strip()
        if not content:
            raise RuntimeError("empty model response")
        return content, _perplexity_sources(value), False, f"perplexity:{PERPLEXITY_MODEL}"
    except Exception as error:
        raise RuntimeError("Perplexity unavailable: " + _provider_error_text(error)) from error


def _openai_generate(prompt: str, use_web: bool, use_code: bool) -> tuple[str, list[dict[str, str]], bool, str]:
    """Use the OpenAI API as an optional reasoning fallback, never ChatGPT cookies/login."""
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    model = os.environ.get("OPENAI_MODEL", OPENAI_MODEL).strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured.")
    if not model:
        raise RuntimeError("OPENAI_MODEL is not configured.")
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_completion_tokens": 6500,
        "response_format": {"type": "json_object"},
    }
    request = Request(
        OPENAI_API_URL,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": f"Exam-Saathi/{ENGINE_VERSION}",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=ANSWER_TIMEOUT_SECONDS) as response:
            value = json.loads(response.read().decode("utf-8"))
        content = str(value["choices"][0]["message"].get("content", "")).strip()
        if not content:
            raise RuntimeError("empty model response")
        # This endpoint is used as a reasoning fallback. Current claims still
        # remain REVIEW_NEEDED unless another web-grounded provider supplied URLs.
        return content, [], False, f"openai:{model}"
    except Exception as error:
        raise RuntimeError("OpenAI unavailable: " + _provider_error_text(error)) from error


def _default_generate(prompt: str, use_web: bool, use_code: bool) -> tuple[str, list[dict[str, str]], bool, str]:
    """Route across optional providers without exposing secret-bearing raw errors."""
    allowed = {"auto", "groq", "gemini", "perplexity", "openai"}
    provider = ANSWER_PROVIDER if ANSWER_PROVIDER in allowed else "auto"
    attempts: list[tuple[str, Callable[..., tuple[str, list[dict[str, str]], bool, str]]]] = []
    if provider == "auto":
        if use_web:
            attempts.extend([
                ("Perplexity", _perplexity_generate),
                ("Groq", _groq_generate),
                ("Gemini", _gemini_generate),
                ("OpenAI", _openai_generate),
            ])
        elif use_code:
            attempts.extend([
                ("Groq", _groq_generate),
                ("Gemini", _gemini_generate),
                ("OpenAI", _openai_generate),
            ])
        else:
            attempts.extend([
                ("Groq", _groq_generate),
                ("OpenAI", _openai_generate),
                ("Gemini", _gemini_generate),
            ])
    else:
        attempts.append({
            "groq": ("Groq", _groq_generate),
            "gemini": ("Gemini", _gemini_generate),
            "perplexity": ("Perplexity", _perplexity_generate),
            "openai": ("OpenAI", _openai_generate),
        }[provider])

    errors: list[str] = []
    for name, generate in attempts:
        key_name = {
            "Groq": "GROQ_API_KEY",
            "Gemini": "GEMINI_API_KEY",
            "Perplexity": "PERPLEXITY_API_KEY",
            "OpenAI": "OPENAI_API_KEY",
        }[name]
        if not os.environ.get(key_name, "").strip():
            errors.append(f"{name}: {key_name} not configured")
            continue
        try:
            return generate(prompt, use_web, use_code)
        except Exception as error:
            errors.append(f"{name}: {_provider_error_text(error)}")
    raise RuntimeError(
        "Answer service is temporarily unavailable. "
        + " | ".join(errors)
        + ". Check Render keys/limits, wait for quota reset, then retry."
    )


def _normalise_payload(payload: dict[str, Any], subject: str, language: str) -> dict[str, Any]:
    def text_value(key: str, fallback: str) -> str:
        value = str(payload.get(key, "")).strip()
        return value or fallback

    def string_list(key: str) -> list[str]:
        value = payload.get(key, [])
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()]

    steps: list[dict[str, str]] = []
    for index, item in enumerate(payload.get("steps", []) if isinstance(payload.get("steps"), list) else []):
        if isinstance(item, dict):
            body = str(item.get("body", "")).strip()
            if body:
                steps.append({
                    "heading": str(item.get("heading", f"Step {index + 1}")).strip(),
                    "body": body,
                })

    diagram = payload.get("diagram", {}) if isinstance(payload.get("diagram"), dict) else {}
    kind = str(diagram.get("kind", "concept")).lower()
    if kind not in {
        "nested", "flow", "force", "reaction", "cycle", "timeline", "equation",
        "concept", "cross_section", "wind_map", "drainage", "choropleth", "plates", "map",
    }:
        kind = "concept"
    nodes = [str(item).strip()[:90] for item in diagram.get("nodes", []) if str(item).strip()][:7]
    edges = [str(item).strip()[:55] for item in diagram.get("edges", []) if str(item).strip()][:7]

    geography = payload.get("geography", {}) if isinstance(payload.get("geography"), dict) else {}
    important_locations = geography.get("important_locations", [])
    if not isinstance(important_locations, list):
        important_locations = []
    mcqs: list[dict[str, Any]] = []
    for item in payload.get("mcqs", []) if isinstance(payload.get("mcqs"), list) else []:
        if not isinstance(item, dict):
            continue
        mcq_question = str(item.get("question", "")).strip()
        options = item.get("options", [])
        if not isinstance(options, list):
            options = []
        if mcq_question:
            mcqs.append({
                "question": mcq_question,
                "options": [str(option).strip() for option in options if str(option).strip()][:4],
                "answer": str(item.get("answer", "")).strip(),
            })

    return {
        "title": text_value("title", "Exam Saathi Answer"),
        "subject": text_value("subject", subject),
        "language": language,
        "direct_answer": text_value("direct_answer", "A direct answer could not be verified."),
        "beginner_explanation": text_value("beginner_explanation", "No beginner explanation was generated."),
        "steps": steps,
        "worked_example": text_value("worked_example", "Not applicable."),
        "key_facts": string_list("key_facts"),
        "why_it_matters": text_value("why_it_matters", "This topic supports concept clarity and exam revision."),
        "exam_perspective": text_value("exam_perspective", "Revise the direct answer, evidence and common mistakes."),
        "common_mistakes": string_list("common_mistakes"),
        "final_answer": text_value("final_answer", "The answer needs human review."),
        "short_questions": string_list("short_questions")[:4],
        "long_questions": string_list("long_questions")[:3],
        "mcqs": mcqs[:3],
        "geography": {
            "type": str(geography.get("type", "Not applicable")).strip() or "Not applicable",
            "important_locations": [
                str(item).strip() for item in important_locations if str(item).strip()
            ][:8],
            "data_year": str(geography.get("data_year", "Not applicable")).strip() or "Not applicable",
            "boundary_note": str(geography.get("boundary_note", "Not applicable")).strip() or "Not applicable",
            "map_note": str(geography.get("map_note", "Schematic / not to scale")).strip() or "Schematic / not to scale",
        },
        "diagram": {
            "kind": kind,
            "title": str(diagram.get("title", "Concept diagram")).strip()[:120],
            "nodes": nodes or [subject, "Evidence", "Verified answer"],
            "edges": edges,
            "accuracy_note": str(diagram.get("accuracy_note", "Schematic / not to scale")).strip()[:180],
        },
        "verification_status": str(payload.get("verification_status", "REVIEW_NEEDED")).upper(),
        "confidence": max(0, min(100, int(float(payload.get("confidence", 0) or 0)))),
        "verification_notes": string_list("verification_notes"),
    }


def _offline_stable_fact_answer(
    question: str, language: str, subject: str
) -> tuple[dict[str, Any], list[dict[str, str]]] | None:
    """Small curated fallback for stable facts when every provider is down.

    This is intentionally narrow. Current office holders and arbitrary facts
    must never be guessed from an offline cache.
    """
    lowered = question.casefold()
    facts = [
        {
            "match": lambda text: ("india" in text or "भारत" in text) and (
                "national bird" in text or "राष्ट्रीय पक्षी" in text
            ),
            "title": "India's National Bird",
            "direct_en": "India's national bird is the Indian peacock (scientific name: Pavo cristatus).",
            "direct_hi": "भारत का राष्ट्रीय पक्षी भारतीय मोर (Indian peacock; वैज्ञानिक नाम: Pavo cristatus) है।",
            "final_en": "Final answer: Indian peacock (Pavo cristatus).",
            "final_hi": "अंतिम उत्तर: भारतीय मोर (Indian peacock / Pavo cristatus)।",
            "facts": ["Common exam name: Indian peacock.", "Scientific name: Pavo cristatus.", "Declared India's national bird in 1963."],
            "nodes": ["India", "National bird", "Indian peacock", "Pavo cristatus"],
            "source_title": "National Portal of India - National Bird",
            "source_uri": "https://knowindia.india.gov.in/national-identity-elements/national-bird.php",
        },
        {
            "match": lambda text: ("india" in text or "भारत" in text) and (
                "capital" in text or "राजधानी" in text
            ),
            "title": "Capital of India",
            "direct_en": "The capital of India is New Delhi.",
            "direct_hi": "भारत की राजधानी नई दिल्ली (New Delhi) है।",
            "final_en": "Final answer: New Delhi.",
            "final_hi": "अंतिम उत्तर: नई दिल्ली।",
            "facts": ["Country: India.", "National capital: New Delhi."],
            "nodes": ["India", "National capital", "New Delhi"],
            "source_title": "National Portal of India - India at a Glance",
            "source_uri": "https://knowindia.india.gov.in/profile/india-at-a-glance.php",
        },
        {
            "match": lambda text: ("constitution" in text or "संविधान" in text) and (
                "india" in text or "भारत" in text or "came into force" in text or "लागू" in text
            ),
            "title": "Constitution of India",
            "direct_en": "The Constitution of India came into force on 26 January 1950.",
            "direct_hi": "भारत का संविधान 26 जनवरी 1950 को लागू हुआ।",
            "final_en": "Final answer: 26 January 1950.",
            "final_hi": "अंतिम उत्तर: 26 जनवरी 1950।",
            "facts": ["Adopted: 26 November 1949.", "Came into force: 26 January 1950."],
            "nodes": ["Constitution adopted", "26 November 1949", "Came into force", "26 January 1950"],
            "source_title": "Legislative Department - Constitution of India",
            "source_uri": "https://legislative.gov.in/constitution-of-india/",
        },
        {
            "match": lambda text: ("largest ocean" in text or "सबसे बड़ा महासागर" in text),
            "title": "World's Largest Ocean",
            "direct_en": "The Pacific Ocean is the world's largest ocean.",
            "direct_hi": "प्रशांत महासागर (Pacific Ocean) दुनिया का सबसे बड़ा महासागर है।",
            "final_en": "Final answer: Pacific Ocean.",
            "final_hi": "अंतिम उत्तर: प्रशांत महासागर।",
            "facts": ["The Pacific is the largest and deepest ocean basin."],
            "nodes": ["World oceans", "Largest ocean", "Pacific Ocean"],
            "source_title": "NOAA Ocean Service - How big is the Pacific Ocean?",
            "source_uri": "https://oceanservice.noaa.gov/facts/pacific.html",
        },
    ]
    fact = next((item for item in facts if item["match"](lowered)), None)
    if fact is None:
        return None

    hindi_mode = language in {"Hindi", "Hinglish"}
    direct = str(fact["direct_hi"] if hindi_mode else fact["direct_en"])
    beginner = (
        "इसे country/topic → official fact → exam-ready name की छोटी chain की तरह याद रखें।"
        if hindi_mode else
        "Remember it as a short chain: country/topic → official fact → exam-ready name."
    )
    final = str(fact["final_hi"] if hindi_mode else fact["final_en"])

    answer = _normalise_payload({
        "title": fact["title"],
        "subject": subject,
        "direct_answer": direct,
        "beginner_explanation": beginner,
        "steps": [
            {"heading": "Identify the exact fact", "body": "Separate the entity being asked about from related facts."},
            {"heading": "Use the curated reference", "body": direct},
            {"heading": "Write the exam-ready answer", "body": final},
        ],
        "worked_example": f"Question: {question} Answer: {final}",
        "key_facts": fact["facts"],
        "why_it_matters": "This is a frequently tested stable general-knowledge fact.",
        "exam_perspective": "Write the exact name/date requested; do not replace it with a related fact.",
        "common_mistakes": ["Do not confuse a related national, geographic or historical fact with the exact fact asked."],
        "final_answer": final,
        "short_questions": [f"State one related fact about {fact['title']}."],
        "long_questions": [f"Explain {fact['title']} with its relevant context."],
        "mcqs": [],
        "diagram": {
            "kind": "flow",
            "title": fact["title"],
            "nodes": fact["nodes"],
            "edges": ["asks", "verified as", "exam detail"],
            "accuracy_note": "Curated stable-fact diagram.",
        },
        "verification_status": "VERIFIED",
        "confidence": 99,
        "verification_notes": [
            "Served from Exam Saathi's narrow curated stable-fact fallback because online providers were unavailable.",
            "No current office-holder or time-sensitive fact is stored in this fallback.",
        ],
    }, subject, language)
    sources = [{
        "title": fact["source_title"],
        "uri": fact["source_uri"],
    }]
    return answer, sources


def _enforce_specific_diagram(
    question: str, payload: dict[str, Any], route: ToolRoute | None = None
) -> None:
    lowered = question.casefold()
    diagram = payload["diagram"]
    generic = {"core idea", "mechanism", "application", "evidence", "verified answer"}
    node_words = {node.casefold() for node in diagram.get("nodes", [])}
    if "enclave" in lowered and (diagram.get("kind") != "nested" or node_words & generic):
        diagram.update({
            "kind": "nested",
            "title": "Territory inside an enclave inside another country",
            "nodes": ["Outer territory", "Enclave / exclave", "Counter-enclave"],
            "edges": ["surrounds", "contains"],
            "accuracy_note": "Schematic nesting diagram; not a surveyed political map.",
        })
    elif "volcano" in lowered and (diagram.get("kind") in {"concept", "flow"} or node_words & generic):
        diagram.update({
            "kind": "cross_section",
            "title": "Volcano cross-section and eruption pathway",
            "nodes": ["Magma chamber", "Main vent", "Crater", "Lava flow", "Ash cloud"],
            "edges": ["pressure rises", "magma ascends", "eruption", "surface flow"],
            "accuracy_note": "Educational cross-section; schematic and not to scale.",
        })
    elif "rain shadow" in lowered and (diagram.get("kind") in {"concept", "flow"} or node_words & generic):
        diagram.update({
            "kind": "cross_section",
            "title": "Orographic uplift and rain-shadow formation",
            "nodes": ["Moist wind", "Windward uplift", "Cooling and rain", "Mountain crest", "Dry leeward air"],
            "edges": ["rises", "cools", "loses moisture", "descends and warms"],
            "accuracy_note": "Process cross-section; schematic and not to scale.",
        })
    elif any(term in lowered for term in ("monsoon", "trade wind", "ocean current")) and (
        diagram.get("kind") in {"concept", "flow"} or node_words & generic
    ):
        diagram.update({
            "kind": "wind_map",
            "title": "Atmospheric and ocean-flow pathway",
            "nodes": ["Source region", "Pressure gradient", "Wind/current direction", "Land interaction", "Weather outcome"],
            "edges": ["drives", "moves", "reaches", "produces"],
            "accuracy_note": "Directional process map; schematic and not to scale.",
        })
    elif any(term in lowered for term in ("river", "drainage", "tributary")) and (
        diagram.get("kind") in {"concept", "flow"} or node_words & generic
    ):
        diagram.update({
            "kind": "drainage",
            "title": "River-basin drainage relationship",
            "nodes": ["Source", "Upper course", "Tributary", "Main channel", "Mouth / basin outlet"],
            "edges": ["flows", "joins", "carries water", "reaches"],
            "accuracy_note": "Drainage concept sketch; schematic and not to scale.",
        })
    elif any(term in lowered for term in ("plate", "earthquake")) and (
        diagram.get("kind") in {"concept", "flow"} or node_words & generic
    ):
        diagram.update({
            "kind": "plates",
            "title": "Plate boundary and crustal movement",
            "nodes": ["Plate A", "Boundary", "Plate B", "Stress release", "Surface effect"],
            "edges": ["moves", "interacts", "stores stress", "causes"],
            "accuracy_note": "Tectonic process cross-section; schematic and not to scale.",
        })
    elif any(term in lowered for term in ("reaction", "compound", "ozonolysis")) and diagram.get("kind") == "concept":
        diagram["kind"] = "reaction"
    elif any(term in lowered for term in ("force", "electric field", "magnetic field")) and diagram.get("kind") == "concept":
        diagram["kind"] = "force"

    if route and route.subject == "Geography":
        if diagram.get("kind") == "concept":
            diagram["kind"] = route.visual_type
        diagram.setdefault("accuracy_note", "Schematic / not to scale.")
        geography = payload.setdefault("geography", {})
        if geography.get("type") in {"", "Not applicable", None}:
            geography["type"] = route.geography_type or "General Geography"
        # v4.4 draws offline educational SVGs, not surveyed boundary geometry.
        # Never let model wording turn a schematic into a claimed exact map.
        geography["map_note"] = "Educational schematic / not to scale; use the cited map source for exact boundaries."
        diagram["accuracy_note"] = diagram.get("accuracy_note") or "Schematic / not to scale."


def _source_domain(uri: str) -> str:
    try:
        return (urlparse(uri).hostname or "").casefold().removeprefix("www.")
    except ValueError:
        return ""


def _source_tier(uri: str) -> tuple[int, str]:
    domain = _source_domain(uri)
    if not domain:
        return 0, "Uploaded evidence"
    if domain.endswith(".gov") or any(
        domain == item.lstrip(".") or domain.endswith(item if item.startswith(".") else "." + item)
        for item in OFFICIAL_SOURCE_DOMAINS
    ):
        return 1, "Official / primary"
    if domain.endswith(".edu") or domain.endswith(".ac.in") or domain.endswith(".edu.in"):
        return 1, "Academic / primary"
    if any(domain == item or domain.endswith("." + item) for item in TRUSTED_SOURCE_DOMAINS):
        return 2, "Trusted reference / news"
    return 3, "Other web source"


def _annotate_sources(items: list[dict[str, str]]) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    for item in items:
        enriched = dict(item)
        tier, source_type = _source_tier(str(item.get("uri", "")))
        enriched["domain"] = _source_domain(str(item.get("uri", "")))
        enriched["source_tier"] = str(tier)
        enriched["source_type"] = source_type
        output.append(enriched)
    return output


def _apply_verification_gate(
    payload: dict[str, Any],
    route: ToolRoute,
    web_sources: list[dict[str, str]],
    used_code: bool,
) -> None:
    status = payload.get("verification_status", "REVIEW_NEEDED")
    if status not in {"VERIFIED", "REVIEW_NEEDED", "INSUFFICIENT"}:
        status = "REVIEW_NEEDED"
    notes = payload["verification_notes"]
    actual_web_sources = [item for item in web_sources if item.get("uri")]
    distinct_domains = {item.get("domain") or _source_domain(item.get("uri", "")) for item in actual_web_sources}
    distinct_domains.discard("")
    source_tiers = {
        int(str(item.get("source_tier", _source_tier(item.get("uri", ""))[0])))
        for item in actual_web_sources
    }
    if route.use_web and len(actual_web_sources) < 1:
        status = "REVIEW_NEEDED"
        notes.append("Web verification was required but no grounded web source was returned.")
    if route.high_risk_fact and len(distinct_domains) < 2:
        status = "REVIEW_NEEDED"
        notes.append("An exceptional/current claim requires at least two independent source domains.")
    if route.source_policy == "official_government" and 1 not in source_tiers:
        status = "REVIEW_NEEDED"
        notes.append("A current government claim needs at least one official or primary source.")
    if route.source_policy == "authoritative_geography" and not ({1, 2} & source_tiers):
        status = "REVIEW_NEEDED"
        notes.append("Current/political geography needs an authoritative geography, government or trusted reference source.")
    if route.use_code and not used_code:
        status = "REVIEW_NEEDED"
        notes.append("Independent code execution was requested but no execution result was returned.")
    payload["verification_status"] = status
    if status != "VERIFIED":
        payload["confidence"] = min(payload["confidence"], 69)


def _dedupe_sources(items: list[dict[str, str]]) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for item in items:
        title = str(item.get("title", "Source")).strip()
        uri = str(item.get("uri", "")).strip()
        key = (title, uri)
        if key not in seen:
            seen.add(key)
            output.append({"title": title, "uri": uri})
    return output


def solve_question(
    question: str,
    language: str = "Hinglish",
    rag_context: list[dict[str, Any]] | None = None,
    generate_fn: Callable[[str, bool, bool], tuple[str, list[dict[str, str]], bool, str]] | None = None,
    force_web: bool = False,
    subject_override: str | None = None,
) -> dict[str, Any]:
    """Solve, independently review and gate one question."""
    question = _clean_question(question)
    language = _safe_language(language)
    route = choose_tools(question, rag_context)
    if subject_override and subject_override != "Auto":
        route.subject = str(subject_override)
        if route.subject == "Geography":
            route.geography_type = detect_geography_type(question)
            route.visual_type = _geography_visual_type(question, route.geography_type)
            if route.high_risk_fact:
                route.source_policy = "authoritative_geography"
    if force_web:
        route.use_web = True
    rag_text, rag_sources = _rag_block(rag_context)
    generator = generate_fn or _default_generate

    try:
        draft_text, draft_sources, draft_code, draft_model = generator(
            _build_solver_prompt(question, language, route, rag_text), route.use_web, route.use_code
        )
        draft = _normalise_payload(_parse_json(draft_text), route.subject, language)
    except Exception:
        offline = None
        if not (route.use_web or route.use_code or route.use_rag or force_web):
            offline = _offline_stable_fact_answer(question, language, route.subject)
        if offline is None:
            raise
        answer, offline_sources = offline
        _enforce_specific_diagram(question, answer, route)
        answer.update({
            "question": question,
            "sources": _annotate_sources(offline_sources),
            "route": {
                "subject": route.subject,
                "web_grounding": False,
                "code_execution": False,
                "uploaded_evidence": False,
                "high_risk_fact": False,
                "geography_type": route.geography_type,
                "visual_type": route.visual_type,
                "source_policy": route.source_policy,
                "freshness_required": route.freshness_required,
            },
            "models": ["offline:curated-stable-facts"],
            "engine_version": ENGINE_VERSION,
            "checked_at": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
        })
        return answer

    review_sources: list[dict[str, str]] = []
    review_code = False
    review_model = "review-unavailable"
    try:
        review_text, review_sources, review_code, review_model = generator(
            _build_review_prompt(question, language, route, rag_text, draft),
            route.use_web,
            route.use_code,
        )
        answer = _normalise_payload(_parse_json(review_text), route.subject, language)
    except Exception as review_error:
        # A free tier can run out between pass 1 and pass 2. Keep the useful
        # first pass, but never label it as independently verified.
        answer = draft
        answer["verification_status"] = "REVIEW_NEEDED"
        answer["confidence"] = min(answer.get("confidence", 0), 69)
        answer["verification_notes"].append(
            "Independent review pass could not finish: "
            + _provider_error_text(review_error)
            + ". The draft is shown instead of being discarded."
        )
    _enforce_specific_diagram(question, answer, route)
    sources = _annotate_sources(_dedupe_sources([*rag_sources, *draft_sources, *review_sources]))
    _apply_verification_gate(answer, route, sources, draft_code or review_code)
    answer.update({
        "question": question,
        "sources": sources,
        "route": {
            "subject": route.subject,
            "web_grounding": route.use_web,
            "code_execution": route.use_code,
            "uploaded_evidence": route.use_rag,
            "high_risk_fact": route.high_risk_fact,
            "geography_type": route.geography_type,
            "visual_type": route.visual_type,
            "source_policy": route.source_policy,
            "freshness_required": route.freshness_required,
        },
        "models": [draft_model, review_model],
        "engine_version": ENGINE_VERSION,
        "checked_at": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
    })
    return answer


def answer_markdown(answer: dict[str, Any]) -> str:
    status_icons = {"VERIFIED": "✅", "REVIEW_NEEDED": "⚠️", "INSUFFICIENT": "🛑"}
    status = answer.get("verification_status", "REVIEW_NEEDED")
    lines = [
        f"# {answer.get('title', 'Exam Saathi Answer')}",
        "",
        f"**{status_icons.get(status, '⚠️')} Verification:** `{status}` · "
        f"**Confidence:** `{answer.get('confidence', 0)}%` · **Subject:** {answer.get('subject', '')}",
        f"**Verified/checked on:** {answer.get('checked_at', 'Current request')}",
        "",
        "## Original Question",
        "",
        answer.get("question", ""),
        "",
        "## 1. Direct Answer",
        "",
        answer.get("direct_answer", ""),
        "",
        "## 2. Beginner Mental Model",
        "",
        answer.get("beginner_explanation", ""),
        "",
        "## 3. Step-by-Step Solution",
        "",
    ]
    for item in answer.get("steps", []):
        lines += [f"### {item['heading']}", "", item["body"], ""]
    lines += ["## 4. Worked Example / Application", "", answer.get("worked_example", ""), ""]
    lines += ["## 5. Key Facts", ""]
    lines += [f"- {item}" for item in answer.get("key_facts", [])] or ["- No separate key facts."]
    lines += ["", "## 6. Why It Matters", "", answer.get("why_it_matters", ""), ""]
    lines += ["## 7. Exam Perspective", "", answer.get("exam_perspective", ""), ""]
    if answer.get("subject") == "Geography":
        geography = answer.get("geography", {})
        lines += ["## Geography Map & Location Check", ""]
        lines += [f"- **Type:** {geography.get('type', 'General Geography')}"]
        lines += [f"- **Data year:** {geography.get('data_year', 'Not applicable')}"]
        lines += [f"- **Map note:** {geography.get('map_note', 'Schematic / not to scale')}"]
        lines += [f"- **Boundary note:** {geography.get('boundary_note', 'Not applicable')}"]
        locations = geography.get("important_locations", [])
        if locations:
            lines += ["- **Important locations:**"] + [f"  - {item}" for item in locations]
        lines.append("")
    lines += ["## 8. Common Mistakes", ""]
    lines += [f"- {item}" for item in answer.get("common_mistakes", [])] or ["- No specific mistake listed."]
    lines += ["", "## 9. Exam-Ready Final Answer", "", answer.get("final_answer", ""), ""]
    lines += ["## 10. Practice Questions", "", "### Short Answer", ""]
    lines += [f"{index}. {item}" for index, item in enumerate(answer.get("short_questions", []), 1)] or ["No short questions generated."]
    lines += ["", "### Long Answer", ""]
    lines += [f"{index}. {item}" for index, item in enumerate(answer.get("long_questions", []), 1)] or ["No long questions generated."]
    if answer.get("mcqs"):
        lines += ["", "### MCQ", ""]
        for index, item in enumerate(answer["mcqs"], 1):
            lines.append(f"{index}. {item['question']}")
            lines += [f"   - {option}" for option in item.get("options", [])]
            lines.append(f"   - **Answer:** {item.get('answer', '')}")
    lines += ["", "## Verification Notes", ""]
    lines += [f"- {item}" for item in answer.get("verification_notes", [])] or ["- No verification note returned."]
    lines += ["", "## Sources", ""]
    for item in answer.get("sources", []):
        source_label = item.get("source_type", "Source")
        lines.append(
            f"- [{item['title']}]({item['uri']}) — {source_label}"
            if item.get("uri") else f"- {item['title']} — {source_label}"
        )
    if not answer.get("sources"):
        route = answer.get("route", {})
        if route.get("code_execution"):
            lines.append("- No external citation was required; the calculation route used independent code/reviewer checks.")
        elif answer.get("verification_status") == "VERIFIED":
            lines.append("- No external citation was required for this answer; see the verification notes above.")
        else:
            lines.append("- No external or uploaded source was available; review the answer before relying on it.")
    lines += ["", f"Generated by Exam Saathi Verified Answer Engine v{ENGINE_VERSION}."]
    return "\n".join(lines)


def _svg_label_lines(label: str, max_characters: int, max_lines: int = 3) -> list[str]:
    """Wrap an SVG label at word boundaries so PDF labels never get clipped."""
    words = str(label).split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and len(candidate) > max_characters:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1][:max(1, max_characters - 1)].rstrip() + "…"
    return lines or [""]


def _svg_text(label: str, x: int, y: int, max_characters: int) -> str:
    lines = _svg_label_lines(label, max_characters)
    first_y = y - ((len(lines) - 1) * 13)
    tspans = "".join(
        f'<tspan x="{x}" y="{first_y + index * 26}">{html.escape(line)}</tspan>'
        for index, line in enumerate(lines)
    )
    return f'<text x="{x}" y="{y}" text-anchor="middle" font-size="18" font-weight="700" fill="#172033">{tspans}</text>'


def _svg_edge_text(label: str, x: int, y: int) -> str:
    lines = _svg_label_lines(label, 22, max_lines=2)
    first_y = y - ((len(lines) - 1) * 8)
    tspans = "".join(
        f'<tspan x="{x}" y="{first_y + index * 17}">{html.escape(line)}</tspan>'
        for index, line in enumerate(lines)
    )
    return (
        f'<rect x="{x - 86}" y="{first_y - 15}" width="172" height="{24 + (len(lines) - 1) * 17}" '
        f'rx="11" fill="#eef2ff"/><text x="{x}" y="{y}" text-anchor="middle" '
        f'font-size="13" fill="#4338ca">{tspans}</text>'
    )


def _svg_diagram(diagram: dict[str, Any]) -> str:
    kind = diagram.get("kind", "concept")
    title = html.escape(str(diagram.get("title", "Concept diagram")))
    nodes = [str(item) for item in diagram.get("nodes", [])][:7]
    edges = [str(item) for item in diagram.get("edges", [])][:7]
    while len(nodes) < 3:
        nodes.append("Evidence")

    head = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1100 620" role="img" aria-label="{title}">
<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#312e81"/><stop offset=".55" stop-color="#7c3aed"/><stop offset="1" stop-color="#0891b2"/></linearGradient><filter id="shadow"><feDropShadow dx="0" dy="8" stdDeviation="8" flood-opacity=".20"/></filter><marker id="arrow" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto"><path d="M0,0 L12,6 L0,12 z" fill="#4f46e5"/></marker></defs>
<style>.node{{filter:url(#shadow);animation:pulse 3s ease-in-out infinite alternate}}.n2{{animation-delay:-1s}}.n3{{animation-delay:-2s}}@keyframes pulse{{to{{transform:translateY(-8px)}}}}text{{font-family:Arial,sans-serif}}</style>
<rect width="1100" height="620" rx="34" fill="#eef2ff"/><rect width="1100" height="92" rx="34" fill="#4338ca"/><rect y="58" width="1100" height="34" fill="#4338ca"/><text x="550" y="58" text-anchor="middle" font-size="32" font-weight="700" fill="white">{title}</text>'''

    if kind == "nested":
        colors = ["#c7d2fe", "#a7f3d0", "#fde68a"]
        rects = []
        for index, node in enumerate(nodes[:3]):
            inset = 80 + index * 105
            rects.append(f'<g class="node n{index + 1}"><rect x="{inset}" y="{130 + index * 65}" width="{1100 - 2 * inset}" height="{420 - index * 130}" rx="32" fill="{colors[index]}" stroke="#3730a3" stroke-width="4"/>{_svg_text(node, 550, 178 + index * 65, 42)}</g>')
        body = "".join(rects)
    elif kind == "cross_section":
        labels = (nodes + ["Source", "Slope", "Crest", "Leeward side", "Outcome"])[:5]
        if any("magma" in label.casefold() or "volcano" in label.casefold() for label in labels):
            body = (
                '<path d="M120,510 L350,510 L535,185 L565,185 L770,510 L1020,510" fill="#d1fae5" stroke="#0f766e" stroke-width="5"/>'
                '<ellipse cx="550" cy="475" rx="125" ry="55" fill="#fb923c" stroke="#c2410c" stroke-width="5"/>'
                '<path d="M550,430 C540,355 565,300 550,205" fill="none" stroke="#dc2626" stroke-width="18"/>'
                '<path d="M542,192 Q550,178 575,192" fill="none" stroke="#7f1d1d" stroke-width="8"/>'
                '<path d="M568,220 C650,260 650,335 735,390" fill="none" stroke="#f97316" stroke-width="12"/>'
                '<g fill="#94a3b8" stroke="#475569" stroke-width="3"><circle cx="550" cy="135" r="35"/><circle cx="600" cy="135" r="42"/><circle cx="645" cy="150" r="31"/><circle cx="585" cy="105" r="28"/></g>'
                + _svg_text(labels[0], 550, 480, 18)
                + _svg_text(labels[1], 505, 330, 16)
                + _svg_text(labels[2], 490, 175, 15)
                + _svg_text(labels[3], 720, 360, 16)
                + _svg_text(labels[4], 720, 120, 16)
            )
        else:
            body = (
                '<path d="M40,500 L250,500 L470,175 L650,500 L1060,500" fill="#d1fae5" stroke="#0f766e" stroke-width="5"/>'
                '<path d="M40,500 L40,390 Q140,350 250,395 L250,500 Z" fill="#67e8f9"/>'
                '<path d="M110,350 C245,260 330,260 420,245" fill="none" stroke="#2563eb" stroke-width="8" marker-end="url(#arrow)"/>'
                '<path d="M565,250 C700,300 790,365 900,390" fill="none" stroke="#f59e0b" stroke-width="8" marker-end="url(#arrow)"/>'
                + _svg_text(labels[0], 135, 445, 18)
                + _svg_text(labels[1], 325, 335, 18)
                + _svg_text(labels[2], 490, 150, 18)
                + _svg_text(labels[3], 720, 410, 20)
                + _svg_text(labels[4], 920, 465, 18)
            )
    elif kind == "wind_map":
        labels = (nodes + ["Source", "Pressure", "Flow", "Land", "Outcome"])[:5]
        arrows = "".join(
            f'<path d="M{100 + i * 40},{220 + i * 60} C{350 + i * 25},{120 + i * 75} {650 + i * 20},{190 + i * 55} {920},{170 + i * 75}" fill="none" stroke="{color}" stroke-width="8" marker-end="url(#arrow)"/>'
            for i, color in enumerate(("#2563eb", "#0891b2", "#7c3aed"))
        )
        body = (
            '<path d="M610,135 Q780,110 1000,200 L960,470 Q760,520 590,430 Q670,320 610,135 Z" fill="#bbf7d0" stroke="#0f766e" stroke-width="4"/>'
            + arrows
            + _svg_text(labels[0], 150, 170, 18)
            + _svg_text(labels[1], 315, 455, 18)
            + _svg_text(labels[2], 515, 205, 18)
            + _svg_text(labels[3], 790, 335, 18)
            + _svg_text(labels[4], 915, 505, 18)
        )
    elif kind == "drainage":
        labels = (nodes + ["Source", "Upper course", "Tributary", "Main channel", "Mouth"])[:5]
        body = (
            '<path d="M120,160 C260,250 350,240 500,345 S790,390 1000,500" fill="none" stroke="#0284c7" stroke-width="18"/>'
            '<path d="M235,145 C315,220 370,250 480,330 M390,145 C430,220 460,270 520,350 M620,190 C650,270 690,330 760,395" fill="none" stroke="#38bdf8" stroke-width="10"/>'
            + _svg_text(labels[0], 130, 135, 18)
            + _svg_text(labels[1], 300, 305, 18)
            + _svg_text(labels[2], 420, 130, 18)
            + _svg_text(labels[3], 690, 435, 18)
            + _svg_text(labels[4], 970, 535, 18)
        )
    elif kind == "plates":
        labels = (nodes + ["Plate A", "Boundary", "Plate B", "Stress", "Surface effect"])[:5]
        body = (
            '<path d="M80,280 L510,280 L550,410 L80,410 Z" fill="#fde68a" stroke="#a16207" stroke-width="4"/>'
            '<path d="M1020,280 L590,280 L550,410 L1020,410 Z" fill="#fecaca" stroke="#b91c1c" stroke-width="4"/>'
            '<path d="M250,235 L475,235" stroke="#4f46e5" stroke-width="9" marker-end="url(#arrow)"/>'
            '<path d="M850,235 L625,235" stroke="#4f46e5" stroke-width="9" marker-end="url(#arrow)"/>'
            '<path d="M550,160 L520,220 L585,215 L545,270" fill="none" stroke="#ef4444" stroke-width="7"/>'
            + _svg_text(labels[0], 260, 350, 20)
            + _svg_text(labels[1], 550, 455, 18)
            + _svg_text(labels[2], 840, 350, 20)
            + _svg_text(labels[3], 550, 145, 18)
            + _svg_text(labels[4], 550, 535, 20)
        )
    elif kind in {"map", "choropleth"}:
        labels = (nodes + ["Location A", "Location B", "Region", "Pattern", "Result"])[:5]
        shades = ("#c7d2fe", "#a7f3d0", "#fde68a", "#fecaca")
        regions = "".join(
            f'<path d="{path}" fill="{shades[index]}" stroke="#4338ca" stroke-width="4"/>'
            for index, path in enumerate((
                "M220,170 L470,145 L500,300 L280,335 Z",
                "M500,160 L780,180 L745,345 L505,300 Z",
                "M285,340 L505,305 L565,500 L250,475 Z",
                "M510,305 L750,350 L820,485 L565,500 Z",
            ))
        )
        body = (
            regions
            + '<circle cx="390" cy="260" r="13" fill="#dc2626"/><circle cx="665" cy="275" r="13" fill="#dc2626"/>'
            + _svg_text(labels[0], 385, 235, 18)
            + _svg_text(labels[1], 675, 250, 18)
            + _svg_text(labels[2], 405, 420, 18)
            + _svg_text(labels[3], 665, 420, 18)
            + _svg_text(labels[4], 550, 550, 22)
        )
    else:
        shown = nodes[:5]
        gap = 880 / max(1, len(shown) - 1)
        start_x = 550 - gap * (len(shown) - 1) / 2
        box_width = min(220, max(145, int(gap * .72)))
        boxes = []
        arrows = []
        for index, node in enumerate(shown):
            x = int(start_x + index * gap)
            y = 300 if index % 2 == 0 else 210
            boxes.append(f'<g class="node n{index % 3 + 1}"><rect x="{x - box_width // 2}" y="{y - 66}" width="{box_width}" height="132" rx="24" fill="white" stroke="#4f46e5" stroke-width="4"/>{_svg_text(node, x, y, max(14, box_width // 10))}</g>')
            if index:
                px = int(start_x + (index - 1) * gap)
                py = 300 if (index - 1) % 2 == 0 else 210
                label = edges[index - 1] if index - 1 < len(edges) else ""
                edge_start = px + box_width // 2 + 6
                edge_end = x - box_width // 2 - 10
                edge_x = (px + x) // 2
                edge_y = min(py, y) - 22
                arrows.append(f'<path d="M{edge_start},{py} C{edge_start + 35},{py} {edge_end - 35},{y} {edge_end},{y}" fill="none" stroke="#4f46e5" stroke-width="5" marker-end="url(#arrow)"/>{_svg_edge_text(label, edge_x, edge_y)}')
        kind_label = html.escape(kind.title())
        body = "".join(arrows + boxes) + f'<text x="550" y="535" text-anchor="middle" font-size="22" font-weight="700" fill="#0f766e">{kind_label} diagram - follow the labelled relationship</text>'
    accuracy_note = html.escape(str(diagram.get("accuracy_note", "")))
    if accuracy_note:
        body += f'<text x="550" y="600" text-anchor="middle" font-size="15" font-weight="700" fill="#475569">{accuracy_note}</text>'
    return head + body + "</svg>"


def _read_latex_group(value: str, start: int) -> tuple[str, int] | None:
    if start >= len(value) or value[start] != "{":
        return None
    depth = 0
    for index in range(start, len(value)):
        if value[index] == "{":
            depth += 1
        elif value[index] == "}":
            depth -= 1
            if depth == 0:
                return value[start + 1:index], index + 1
    return None


def _latex_to_html(value: str) -> str:
    """Render common school-level LaTeX without depending on online MathJax."""
    command_map = {
        "\\pi": "π", "\\epsilon": "ε", "\\omega": "ω", "\\alpha": "α",
        "\\beta": "β", "\\theta": "θ", "\\Delta": "Δ", "\\times": "×",
        "\\cdot": "·", "\\approx": "≈", "\\le": "≤", "\\ge": "≥",
        "\\ll": "≪", "\\rightarrow": "→", "\\rightleftharpoons": "⇌",
    }
    output: list[str] = []
    index = 0
    while index < len(value):
        if value.startswith("\\frac", index):
            numerator = _read_latex_group(value, index + 5)
            if numerator:
                denominator = _read_latex_group(value, numerator[1])
                if denominator:
                    output.append(
                        "(" + _latex_to_html(numerator[0]) + ")/("
                        + _latex_to_html(denominator[0]) + ")"
                    )
                    index = denominator[1]
                    continue
        if value.startswith("\\sqrt", index):
            group = _read_latex_group(value, index + 5)
            if group:
                output.append("√(" + _latex_to_html(group[0]) + ")")
                index = group[1]
                continue
        if value.startswith("\\text", index):
            group = _read_latex_group(value, index + 5)
            if group:
                output.append(_latex_to_html(group[0]))
                index = group[1]
                continue
        if value[index] in {"^", "_"}:
            group = _read_latex_group(value, index + 1)
            if group:
                tag = "sup" if value[index] == "^" else "sub"
                output.append(f"<{tag}>{_latex_to_html(group[0])}</{tag}>")
                index = group[1]
                continue
            if index + 1 < len(value):
                tag = "sup" if value[index] == "^" else "sub"
                output.append(f"<{tag}>{html.escape(value[index + 1])}</{tag}>")
                index += 2
                continue
        matched = False
        for command, symbol in sorted(command_map.items(), key=lambda item: -len(item[0])):
            if value.startswith(command, index):
                output.append(symbol)
                index += len(command)
                matched = True
                break
        if matched:
            continue
        if value.startswith("\\left", index) or value.startswith("\\right", index):
            index += 5 if value.startswith("\\left", index) else 6
            continue
        output.append(html.escape(value[index]))
        index += 1
    return "".join(output).replace("\\,", " ").replace("\\ ", " ")


def _inline_format(value: str) -> str:
    math_blocks: list[str] = []

    def store_math(match: re.Match[str]) -> str:
        token = f"@@EXAMSAATHIMATH{len(math_blocks)}@@"
        math_blocks.append(f'<span class="math">{_latex_to_html(match.group(1))}</span>')
        return token

    with_tokens = re.sub(r"\${1,2}(.+?)\${1,2}", store_math, value)
    safe = html.escape(with_tokens)
    safe = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", safe)
    safe = re.sub(r"`(.+?)`", r"<code>\1</code>", safe)
    safe = re.sub(r"\[(.+?)\]\((https?://[^\s)]+)\)", r'<a href="\2" target="_blank" rel="noopener">\1</a>', safe)
    for index, math_block in enumerate(math_blocks):
        safe = safe.replace(f"@@EXAMSAATHIMATH{index}@@", math_block)
    return safe


def _markdown_to_safe_html(markdown_text: str) -> str:
    output: list[str] = []
    in_list = False
    for raw in markdown_text.splitlines():
        line = raw.strip()
        if not line:
            if in_list:
                output.append("</ul>")
                in_list = False
            continue
        heading = re.match(r"^(#{1,4})\s+(.+)$", line)
        if heading:
            if in_list:
                output.append("</ul>")
                in_list = False
            level = min(4, len(heading.group(1)) + 1)
            output.append(f"<h{level}>{_inline_format(heading.group(2))}</h{level}>")
        elif line.startswith("- "):
            if not in_list:
                output.append("<ul>")
                in_list = True
            output.append(f"<li>{_inline_format(line[2:])}</li>")
        else:
            if in_list:
                output.append("</ul>")
                in_list = False
            output.append(f"<p>{_inline_format(line)}</p>")
    if in_list:
        output.append("</ul>")
    return "\n".join(output)


def _html_document(answer: dict[str, Any], markdown_text: str, svg: str) -> str:
    title = html.escape(str(answer.get("title", "Exam Saathi Answer")))
    status = html.escape(str(answer.get("verification_status", "REVIEW_NEEDED")))
    body = _markdown_to_safe_html(markdown_text)
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="exam-saathi-engine" content="{ENGINE_VERSION}"><title>{title}</title><style>
:root{{color-scheme:light}}*{{box-sizing:border-box}}body{{margin:0;background:radial-gradient(circle at 10% 8%,#ddd6fe,transparent 34%),radial-gradient(circle at 90% 22%,#a5f3fc,transparent 32%),linear-gradient(145deg,#f8fafc,#fff7ed);color:#172033;font:17px/1.72 "Noto Sans",Arial,sans-serif}}header{{padding:46px max(5vw,20px);background:linear-gradient(120deg,#312e81,#7c3aed,#0891b2);color:white}}h1{{font-size:clamp(30px,5vw,54px);margin:.15em 0}}main{{max-width:1040px;margin:auto;padding:26px}}section{{background:#ffffffea;border:1px solid #c7d2fe;border-radius:24px;padding:26px;margin:24px 0;box-shadow:0 14px 36px #312e8122}}h2,h3,h4{{color:#4338ca}}.diagram svg{{width:100%;height:auto}}.badge{{display:inline-block;background:#ecfdf5;color:#065f46;border:2px solid #10b981;border-radius:999px;padding:6px 14px;font-weight:800}}code{{background:#ede9fe;color:#5b21b6;padding:2px 5px;border-radius:5px}}.math{{font-family:"DejaVu Sans",Arial,sans-serif;font-weight:600;color:#312e81}}.frac{{display:inline-flex;vertical-align:middle;flex-direction:column;text-align:center;line-height:1.15;margin:0 .15em}}.frac>span:first-child{{border-bottom:1px solid currentColor;padding:0 .15em}}a{{color:#3730a3;overflow-wrap:anywhere}}button{{background:#172033;color:white;border:0;border-radius:12px;padding:12px 18px;font-weight:800;cursor:pointer}}.spark{{position:fixed;font-size:32px;animation:float 5s ease-in-out infinite alternate;pointer-events:none}}.s1{{left:2%;top:18%}}.s2{{right:2%;top:48%;animation-delay:-2s}}@keyframes float{{to{{transform:translateY(-45px) rotate(16deg)}}}}@media print{{.spark,button{{display:none}}body{{background:white}}section{{box-shadow:none;break-inside:avoid}}}}</style></head><body><span class="spark s1">✨</span><span class="spark s2">📚</span><header><small>EXAM SAATHI AI · Verified Answer Engine v{ENGINE_VERSION}</small><h1>{title}</h1><span class="badge">{status}</span> <button onclick="window.print()">Print / Save as PDF</button></header><main><section class="diagram"><h2>Animated Concept Diagram</h2>{svg}<p><strong>Note:</strong> HTML motion is a learning aid. The downloadable PDF contains a clear static diagram.</p></section><section>{body}</section></main></body></html>'''


def _pdf_document(answer: dict[str, Any], markdown_text: str, svg: str) -> str:
    """Build a compact print layout without browser-only decorations."""
    title = html.escape(str(answer.get("title", "Exam Saathi Answer")))
    status = html.escape(str(answer.get("verification_status", "REVIEW_NEEDED")))
    body = _markdown_to_safe_html(markdown_text)
    return f'''<!doctype html><html><head><meta charset="utf-8"><style>
body{{color:#172033;font:12pt/1.55 Arial,sans-serif;margin:0}}.cover{{border:2px solid #4338ca;padding:18px;border-radius:14px;margin-bottom:18px}}.brand{{font-size:10pt;font-weight:700;color:#0f766e;letter-spacing:1px}}h1{{font-size:27pt;color:#312e81;margin:8px 0}}h2{{font-size:19pt;color:#4338ca;margin-top:20px;break-after:avoid;page-break-after:avoid}}h3{{font-size:15pt;color:#0f766e;break-after:avoid;page-break-after:avoid}}h4{{font-size:13pt;color:#4338ca;break-after:avoid;page-break-after:avoid}}.badge{{display:inline-block;border:2px solid #10b981;background:#ecfdf5;color:#065f46;padding:5px 10px;font-weight:700}}.diagram{{border:1px solid #c7d2fe;padding:14px;margin:14px 0}}.diagram svg{{width:92%;height:auto;display:block;margin:auto}}code{{background:#ede9fe;color:#5b21b6;padding:2px 4px}}.math{{font-family:"DejaVu Sans",Arial,sans-serif;font-weight:600;color:#312e81}}.frac{{display:inline-flex;vertical-align:middle;flex-direction:column;text-align:center;line-height:1.05;margin:0 .12em}}.frac>span:first-child{{border-bottom:1px solid currentColor;padding:0 .12em}}a{{color:#3730a3}}li{{margin-bottom:5px}}p{{margin:6px 0 10px;orphans:2;widows:2}}</style></head><body><div class="cover"><div class="brand">EXAM SAATHI AI - VERIFIED ANSWER ENGINE v{ENGINE_VERSION}</div><h1>{title}</h1><span class="badge">{status}</span></div><div class="diagram"><h2>Question-Specific Concept Diagram</h2>{svg}<p><strong>PDF note:</strong> This is the clear static frame. Open the HTML guide for animation.</p></div>{body}</body></html>'''


def _write_pdf_from_html(html_text: str, pdf_path: Path) -> None:
    writer = pymupdf.DocumentWriter(str(pdf_path))
    story = pymupdf.Story(html=html_text)
    page_box = pymupdf.Rect(0, 0, 595, 842)
    content_box = pymupdf.Rect(38, 38, 557, 804)
    more = 1
    pages = 0
    while more and pages < 80:
        device = writer.begin_page(page_box)
        more, _ = story.place(content_box)
        story.draw(device)
        writer.end_page()
        pages += 1
    writer.close()
    if more:
        raise RuntimeError("PDF exceeded the safe 80-page export limit.")
    # Story output is intentionally high fidelity but can be several megabytes.
    # Re-save with deduplication/compression so Render and low-data students do
    # not repeatedly transfer an unnecessarily heavy file.
    optimized_path = pdf_path.with_name(f"{pdf_path.stem}.optimized.pdf")
    document = pymupdf.open(str(pdf_path))
    try:
        document.save(
            str(optimized_path),
            garbage=4,
            clean=True,
            deflate=True,
            deflate_images=True,
            deflate_fonts=True,
        )
    finally:
        document.close()
    os.replace(optimized_path, pdf_path)


def create_answer_artifacts(answer: dict[str, Any]) -> tuple[str, str]:
    """Create unique HTML/PDF paths so a browser cannot return yesterday's file."""
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    # Keep temporary Render storage bounded. Only this engine's generated files
    # are eligible; uploaded student files and project files are never touched.
    generated = sorted(
        ARTIFACT_DIR.glob("exam_saathi_v*_*.*"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    now = time.time()
    for index, old_path in enumerate(generated):
        if index >= 100 or now - old_path.stat().st_mtime > 24 * 60 * 60:
            if old_path.suffix.lower() in {".html", ".pdf"}:
                old_path.unlink(missing_ok=True)
    markdown_text = answer_markdown(answer)
    svg = _svg_diagram(answer.get("diagram", {}))
    unique = f"{answer.get('question', '')}|{time.time_ns()}|{ENGINE_VERSION}"
    digest = hashlib.sha256(unique.encode("utf-8")).hexdigest()[:14]
    stem = f"exam_saathi_v{ENGINE_VERSION.replace('.', '_')}_{digest}"
    html_path = ARTIFACT_DIR / f"{stem}.html"
    pdf_path = ARTIFACT_DIR / f"{stem}.pdf"
    html_text = _html_document(answer, markdown_text, svg)
    html_path.write_text(html_text, encoding="utf-8")
    _write_pdf_from_html(_pdf_document(answer, markdown_text, svg), pdf_path)
    return str(html_path), str(pdf_path)
