"""Self-contained, offline study guides. Uploaded text is always escaped."""
from __future__ import annotations

import base64
import html
import io
import tempfile
import uuid
from pathlib import Path

from PIL import Image, ImageOps

from study_features import build_flashcards, build_quiz_items


def esc(value):
    return html.escape(str(value))


def source(item):
    return f"{esc(item.get('source_name', 'Uploaded notes'))} · Page {esc(item.get('page_number', '?'))}"


def build_study_html(result, title="My Smart Revision Guide", include_diagrams=True):
    if not result or not any(result.get(k) for k in ('notes', 'documents', 'diagrams')):
        raise ValueError('पहले PDF/images process करें, फिर study guide बनाएँ।')
    sections = []
    def section(key, heading, body):
        sections.append(f'<section id="{key}"><h2>{heading}</h2>{body}</section>')

    topics = ''.join(f'<span class="badge">{esc(t["topic"])}</span>' for t in result.get('topics', []))
    section('sprint', '01 · 15-Minute Revision', '<p>5 min: priority topics · 4 min: formulas & diagrams · 6 min: recall practice.</p><p>Revision priorities, not guaranteed exam predictions.</p>'+topics)
    notes = ''.join(f'<article class="card"><h3>Note {i}</h3><p>{esc(n["text"])}</p><small>{source(n)}</small></article>' for i,n in enumerate(result.get('notes', []),1))
    section('notes', '02 · Source-Based Smart Notes', notes or '<p>No reliable notes extracted. Check the source and human review.</p>')
    formulas = ''.join(f'<article class="card"><pre>{esc(f["formula"])}</pre><small>{source(f)}</small></article>' for f in result.get('formulas', []))
    section('formulas', '03 · Formula Sheet', formulas or '<p>No reliable formulas extracted.</p>')
    figures, embedded, skipped, total = [], 0, 0, 0
    if include_diagrams:
        for d in result.get('diagrams', []):
            try:
                with Image.open(d['image_path']) as image:
                    picture = ImageOps.exif_transpose(image).convert('RGB')
                    picture.thumbnail((1600,1600))
                    buffer = io.BytesIO()
                    picture.save(buffer, 'JPEG', quality=85, optimize=True)
                payload = buffer.getvalue()
                if total+len(payload)>18*1024*1024:
                    raise ValueError('Guide image budget reached')
                total += len(payload)
                url = 'data:image/jpeg;base64,'+base64.b64encode(payload).decode('ascii')
                figures.append(f'<figure class="card"><button class="zoom" type="button" aria-label="Zoom source diagram"><img loading="lazy" src="{url}" alt="Source diagram: {source(d)}"></button><figcaption>{source(d)} — original source page; tap to zoom.</figcaption><details><summary>Recall the concept, then reveal description</summary><p>{esc(d.get("description", "Inspect the original labels."))}</p></details></figure>')
                embedded += 1
            except (OSError, ValueError, KeyError):
                skipped += 1
    message = f'<p>{embedded} source images embedded. '
    message += f'{skipped} image(s) unavailable or omitted to limit download size.' if skipped else ''
    message += '</p>'
    if not include_diagrams:
        message = '<p>Text-only export: diagrams excluded to reduce download size.</p>'
    elif not figures:
        message += '<p>No diagrams available in this analysis. This guide does not invent diagrams.</p>'
    section('diagrams', '04 · Diagram Learning', message+''.join(figures))
    cards = ''.join(f'<article class="card"><h3>{esc(c["question"])}</h3><details><summary>Reveal answer</summary><p>{esc(c["answer"])}</p><small>{esc(c["source"])}</small></details></article>' for c in build_flashcards(result))
    section('cards', '05 · Active Recall Cards', cards or '<p>No cards available.</p>')
    quiz = ''.join(f'<article class="card"><h3>Question {i}</h3><p>{esc(q["question"])}</p><details><summary>Check the source answer</summary><p>{esc(q["answer"])}</p><small>{esc(q["source"])}</small></details><label><input type="checkbox"> I need to revise this again</label></article>' for i,q in enumerate(build_quiz_items(result),1))
    section('quiz', '06 · Practice Questions', quiz or '<p>No verified quiz items available.</p>')
    warnings = result.get('batch_warnings', [])
    section('review', '07 · Coverage & Review', '<p>This is the current extracted analysis, not a guarantee that every PDF page was read. Check unclear handwriting, equations and labels against the original. Formula notation is preserved as source text, not automatically re-typeset.</p>'+''.join(f'<p class="warning">{esc(w)}</p>' for w in warnings))
    nav = ''.join(f'<a href="#{key}">{name}</a>' for key,name in [('sprint','Revision'),('notes','Notes'),('formulas','Formulas'),('diagrams','Diagrams'),('cards','Cards'),('quiz','Quiz'),('review','Review')])
    return '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="referrer" content="no-referrer"><title>'''+esc(title)+'''</title><style>
:root{color-scheme:light}*{box-sizing:border-box}body{margin:0;background:#f5f1e9;color:#172033;font:17px/1.7 system-ui,sans-serif}header{background:#17372f;color:#fff;padding:52px max(6vw,20px)}header p{color:#dce9e2}h1{font:700 clamp(30px,5vw,54px)/1.15 Georgia,serif;margin:12px 0}h2{font:700 30px/1.3 Georgia,serif;color:#17372f}nav{display:flex;gap:12px;flex-wrap:wrap;padding:16px;background:#fff;border-bottom:1px solid #ddd}nav a{color:#17372f;font-weight:700}main{max-width:1050px;margin:auto;padding:24px}section{scroll-margin-top:16px;margin-bottom:50px}.card{background:#fff;padding:24px;border:1px solid #dadfd8;border-radius:14px;margin:18px 0;overflow-wrap:anywhere}.card p{white-space:pre-wrap}small,figcaption{color:#45574e}pre{white-space:pre-wrap;font-size:18px}.badge{display:inline-block;background:#dce8dd;border-radius:20px;padding:5px 15px;margin:4px}button,summary{cursor:pointer}button{padding:10px 16px;border:1px solid #6c8277;border-radius:8px;background:#fff;color:#17372f;font:inherit}summary{font-weight:700;color:#315e43}img{max-width:100%;height:auto}.zoom{display:block;width:100%;border:0;padding:0}details{margin:16px 0}label{display:block}.warning{background:#fff0c5;padding:12px}dialog{max-width:96vw;max-height:96vh;padding:12px;border-radius:12px}dialog img{display:block;max-height:80vh}dialog::backdrop{background:#000a}footer{padding:25px;text-align:center}@media print{nav,header button,.zoom+button,dialog{display:none}body{background:#fff}.card{break-inside:avoid}details>*{display:block}main{padding:0}header{background:white;color:#17372f}}
</style></head><body><header><p>EXAM SAATHI · OFFLINE STUDY GUIDE</p><h1>'''+esc(title)+'''</h1><p>Revise · Recall · Understand diagrams</p><button id="print" type="button">Print / Save as PDF</button><p>Private study content: share only with permission. Embedded page images may include handwriting and personal details.</p></header><nav>'''+nav+'''</nav><main>'''+''.join(sections)+'''</main><footer>No internet, account or API key required to read this downloaded guide. AI answers and microphone features stay in the online app.</footer><dialog id="viewer"><button id="close" type="button">Close image</button><img alt="Enlarged original source page"></dialog><script>
const viewer=document.getElementById('viewer');
document.querySelectorAll('.zoom').forEach(b=>b.addEventListener('click',()=>{viewer.querySelector('img').src=b.querySelector('img').src;viewer.showModal()}));
document.getElementById('close').addEventListener('click',()=>viewer.close());
document.getElementById('print').addEventListener('click',()=>{const ds=[...document.querySelectorAll('details')];const opened=ds.map(d=>d.open);ds.forEach(d=>d.open=true);window.print();ds.forEach((d,i)=>d.open=opened[i])});
</script></body></html>'''


def export_study_guide(result, title='My Smart Revision Guide', include_diagrams=True):
    document = build_study_html(result, title.strip()[:160] or 'My Smart Revision Guide', include_diagrams)
    directory = Path(tempfile.gettempdir()) / 'exam_saathi_exports'
    directory.mkdir(exist_ok=True)
    target = directory / f'study_guide_{uuid.uuid4().hex}.html'
    target.write_text(document, encoding='utf-8')
    return str(target)
