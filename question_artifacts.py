"""Safe, offline visual study packs for a single Quick Solver answer."""
from __future__ import annotations

import base64
import html
import re
import tempfile
import uuid
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape


SUBJECT_SIGNALS = {
    "Physics": ("force", "electric", "magnetic", "velocity", "oscillation", "current", "circuit", "wave", "lens", "momentum", "energy", "भौतिक", "बल", "विद्युत", "चुंबक", "ବଳ", "ବିଦ୍ୟୁତ", "বল", "বিদ্যুৎ", "விசை", "மின்சாரம்", "బలం", "విద్యుత్"),
    "Chemistry": ("reaction", "compound", "reagent", "molecule", "organic", "acid", "base", "equilibrium", "iodoform", "ozonolysis", "रसायन", "अभिक्रिया", "अम्ल", "ରସାୟନ", "অম্ল", "வேதியியல்", "రసాయన"),
    "Biology": ("cell", "dna", "gene", "photosynthesis", "respiration", "organ", "blood", "neuron", "enzyme", "ecology", "जीवविज्ञान", "कोशिका", "प्रकाश संश्लेषण", "ଜୀବବିଜ୍ଞାନ", "କୋଷ", "জীববিজ্ঞান", "কোষ", "உயிரியல்", "செல்", "జీవశాస్త్ర", "కణం"),
    "Geography": ("climate", "desert", "river", "mountain", "monsoon", "volcano", "earthquake", "plate", "ocean", "current", "rainfall", "भूगोल", "जलवायु", "मरुस्थल", "ज्वालामुखी", "भूकंप", "मानसून", "ଭୂଗୋଳ", "ଜଳବାୟୁ", "ଆଗ୍ନେୟଗିରି", "ভূগোল", "জলবায়ু", "আগ্নেয়গিরি", "புவியியல்", "எரிமலை", "భూగోళ", "అగ్నిపర్వతం"),
    "Mathematics": ("calculate", "equation", "sqrt", "integral", "derivative", "matrix", "geometry", "probability", "theorem", "fraction", "गणित", "समीकरण", "ଜ୍ୟାମିତି", "গণিত", "கணிதம்", "గణితం"),
    "History": ("empire", "war", "revolution", "dynasty", "independence", "civilization", "century", "treaty", "इतिहास", "साम्राज्य", "क्रांति", "ଇତିହାସ", "ইতিহাস", "வரலாறு", "చరిత్ర"),
}


def detect_subject(question: str) -> str:
    text=str(question or "").casefold()
    scores={name:sum(token in text for token in tokens) for name,tokens in SUBJECT_SIGNALS.items()}
    best=max(scores,key=scores.get)
    return best if scores[best] else "General Studies"


def diagram_kind(question: str, subject: str) -> str:
    text=str(question or "").casefold()
    if any(x in text for x in ("volcano","volcanic","ज्वालामुखी","ଆଗ୍ନେୟଗିରି","আগ্নেয়গিরি","எரிமலை","అగ్నిపర్వతం")): return "volcano"
    if subject=="Geography" and any(x in text for x in ("climate","desert","rain","current","monsoon")): return "climate"
    if subject=="Physics" and "ring" in text and any(x in text for x in ("charge","electric","axis")): return "charged_ring"
    if subject=="Physics" and "circuit" in text: return "circuit"
    if subject=="Biology" and any(x in text for x in ("cell","organelle","mitochond")): return "cell"
    if subject=="Biology" and any(x in text for x in ("dna","gene","chromosom")): return "dna"
    return "concept_map"


def _svg_shell(title: str, body: str, animation: str="") -> str:
    safe=xml_escape(title[:100])
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="650" viewBox="0 0 1200 650" role="img" aria-label="{safe}">
<defs><marker id="a" markerWidth="10" markerHeight="10" refX="9" refY="5" orient="auto"><path d="M0 0L10 5L0 10Z" fill="#4f46e5"/></marker></defs>
<style>.t{{font:700 34px Arial,sans-serif;fill:#fff}}.h{{font:700 24px Arial,sans-serif;fill:#172033}}.p{{font:500 18px Arial,sans-serif;fill:#24324a}}.card{{fill:#fff;stroke:#c7d2fe;stroke-width:2}}{animation}</style>
<rect width="1200" height="650" rx="28" fill="#eef2ff"/><rect width="1200" height="86" rx="28" fill="#4338ca"/><rect y="58" width="1200" height="28" fill="#4338ca"/><text x="600" y="55" text-anchor="middle" class="t">{safe}</text>{body}</svg>'''


def _volcano_svg(animated: bool) -> str:
    anim='''.smoke{animation:rise 3s ease-in-out infinite}.lava{animation:pulse 1.6s ease-in-out infinite alternate}@keyframes rise{0%{transform:translateY(15px);opacity:.35}50%{opacity:.9}100%{transform:translateY(-30px);opacity:.1}}@keyframes pulse{to{stroke-width:18;opacity:.7}}''' if animated else ""
    body='''<path d="M225 555L470 175L610 330L720 210L995 555Z" fill="#69534a" stroke="#46372f" stroke-width="5"/><path d="M470 175L430 238L505 220L560 275L610 330L642 285L720 210L750 260L680 285L615 365L560 305L500 263Z" fill="#f7f7fb"/><ellipse cx="610" cy="332" rx="82" ry="25" fill="#2c2020"/><path class="lava" d="M610 505L610 340M610 505C550 525 525 550 500 580" fill="none" stroke="#ff542f" stroke-width="12"/><ellipse cx="610" cy="520" rx="105" ry="55" fill="#ff8a35" opacity=".75"/><g class="smoke" fill="#687386" opacity=".75"><circle cx="610" cy="260" r="43"/><circle cx="570" cy="225" r="35"/><circle cx="650" cy="215" r="50"/><circle cx="620" cy="165" r="42"/></g><g class="p"><text x="760" y="190">Ash cloud</text><line x1="750" y1="198" x2="665" y2="218" stroke="#4f46e5" stroke-width="3" marker-end="url(#a)"/><text x="785" y="320">Crater</text><line x1="775" y1="326" x2="690" y2="333" stroke="#4f46e5" stroke-width="3" marker-end="url(#a)"/><text x="800" y="442">Main vent</text><line x1="790" y1="448" x2="625" y2="440" stroke="#4f46e5" stroke-width="3" marker-end="url(#a)"/><text x="785" y="545">Magma chamber</text><line x1="775" y1="548" x2="700" y2="530" stroke="#4f46e5" stroke-width="3" marker-end="url(#a)"/></g><rect x="65" y="130" width="265" height="165" rx="18" fill="#ffffff" stroke="#c7d2fe" stroke-width="2"/><text x="90" y="170" class="h">Process</text><text x="90" y="207" class="p">1. Magma rises</text><text x="90" y="239" class="p">2. Gas pressure grows</text><text x="90" y="271" class="p">3. Eruption releases it</text>'''
    return _svg_shell("Volcano - structure and eruption",body,anim)


def _climate_svg(animated: bool) -> str:
    anim='''.air{animation:flow 3s ease-in-out infinite alternate}.fog{animation:drift 5s linear infinite alternate}@keyframes flow{to{transform:translateY(22px)}}@keyframes drift{to{transform:translateX(35px)}}''' if animated else ""
    body='''<rect x="0" y="455" width="390" height="195" fill="#2188b8"/><path d="M390 455L690 490L940 175L1200 470V650H390Z" fill="#d6a15c"/><path d="M760 430L940 175L1120 430" fill="#7a5a49"/><path d="M895 240L940 175L985 240" fill="#fff"/><path d="M70 565C175 610 285 590 355 520" fill="none" stroke="#8de2ff" stroke-width="15" marker-end="url(#a)"/><text x="65" y="620" class="p" fill="#fff">Cold current + upwelling</text><g class="fog" fill="#fff" opacity=".88"><ellipse cx="250" cy="420" rx="90" ry="30"/><ellipse cx="345" cy="420" rx="90" ry="32"/><ellipse cx="430" cy="430" rx="75" ry="25"/></g><path d="M35 350C250 330 470 345 690 325" fill="none" stroke="#ef5b4c" stroke-width="9" stroke-dasharray="18 10"/><text x="70" y="310" class="h">Thermal inversion cap</text><g class="air"><path d="M420 135V285M555 135V285" stroke="#ffb52d" stroke-width="10" marker-end="url(#a)"/><text x="350" y="120" class="h">Subtropical sinking air</text></g><path d="M1150 120C1080 120 1035 150 1000 205" fill="none" stroke="#4f46e5" stroke-width="9" marker-end="url(#a)"/><text x="880" y="112" class="h">Easterly moisture</text><path d="M865 315C805 350 760 390 730 440" fill="none" stroke="#ef8c32" stroke-width="9" marker-end="url(#a)"/><text x="645" y="535" class="h">Dry west slope</text><text x="140" y="460" class="p">Camanchaca fog</text><text x="900" y="525" class="p">Rain on east side</text>'''
    return _svg_shell("Coastal desert climate system",body,anim)


def _ring_svg(animated: bool) -> str:
    anim='''.particle{animation:osc 2.4s ease-in-out infinite alternate}.force{animation:fade 1.2s ease-in-out infinite alternate}@keyframes osc{to{transform:translateX(-260px)}}@keyframes fade{to{opacity:.35}}''' if animated else ""
    body='''<ellipse cx="600" cy="370" rx="115" ry="255" fill="none" stroke="#ef5b4c" stroke-width="20"/><text x="535" y="625" class="h">Ring: +Q, radius R</text><line x1="115" y1="370" x2="1080" y2="370" stroke="#64748b" stroke-width="4" stroke-dasharray="10 8"/><text x="1010" y="345" class="p">axis z</text><g class="particle"><circle cx="855" cy="370" r="26" fill="#2563eb"/><text x="842" y="378" class="h" fill="#fff">-q</text></g><path class="force" d="M815 315L700 315" stroke="#4f46e5" stroke-width="9" marker-end="url(#a)"/><text x="735" y="285" class="h">restoring force</text><rect x="65" y="125" width="320" height="180" rx="18" fill="#ffffff" stroke="#c7d2fe" stroke-width="2"/><text x="90" y="165" class="h">Small displacement</text><text x="90" y="205" class="p">F ≈ -(kₑQq/R³)z</text><text x="90" y="240" class="p">ω² = kₑQq/(mR³)</text><text x="90" y="275" class="p">vₘₐₓ = ω × amplitude</text>'''
    return _svg_shell("Charged ring - axial SHM",body,anim)


def _cell_svg(animated: bool) -> str:
    anim='''.mito{animation:pulse 2s ease-in-out infinite alternate}.dot{animation:float 3s ease-in-out infinite alternate}@keyframes pulse{to{transform:scale(1.04);transform-origin:center}}@keyframes float{to{transform:translateY(-16px)}}''' if animated else ""
    body='''<ellipse cx="610" cy="370" rx="400" ry="235" fill="#d7f4d8" stroke="#20845a" stroke-width="10"/><circle cx="610" cy="365" r="105" fill="#a78bfa" stroke="#5b21b6" stroke-width="7"/><circle cx="635" cy="350" r="32" fill="#6d28d9"/><g class="mito" fill="#f59e0b" stroke="#b45309" stroke-width="5"><ellipse cx="390" cy="300" rx="85" ry="45"/><ellipse cx="825" cy="430" rx="85" ry="45"/></g><g class="dot" fill="#38bdf8"><circle cx="405" cy="455" r="25"/><circle cx="780" cy="270" r="22"/><circle cx="515" cy="510" r="18"/></g><text x="575" y="235" class="h">Nucleus</text><line x1="610" y1="245" x2="610" y2="275" stroke="#4f46e5" stroke-width="4" marker-end="url(#a)"/><text x="245" y="250" class="h">Mitochondrion</text><line x1="340" y1="260" x2="380" y2="285" stroke="#4f46e5" stroke-width="4" marker-end="url(#a)"/><text x="850" y="480" class="h">Cell membrane</text><line x1="845" y1="463" x2="955" y2="455" stroke="#4f46e5" stroke-width="4" marker-end="url(#a)"/><text x="840" y="245" class="h">Cytoplasm</text>'''
    return _svg_shell("Cell - visual concept map",body,anim)


def _generic_svg(subject: str, animated: bool) -> str:
    color={"Physics":"#2563eb","Chemistry":"#7c3aed","Biology":"#059669","Geography":"#d97706","Mathematics":"#dc2626","History":"#8b5e34"}.get(subject,"#4f46e5")
    anim='''.node{animation:bob 2.7s ease-in-out infinite alternate}@keyframes bob{to{transform:translateY(-10px)}}''' if animated else ""
    body=f'''<rect x="450" y="140" width="300" height="90" rx="22" fill="{color}"/><text x="600" y="195" text-anchor="middle" class="h" fill="#fff">{xml_escape(subject)}</text><path d="M600 230V300M600 300L270 390M600 300L600 390M600 300L930 390" fill="none" stroke="#4f46e5" stroke-width="6" marker-end="url(#a)"/><g class="node"><rect x="90" y="390" width="300" height="145" rx="20" fill="#ffffff" stroke="#c7d2fe" stroke-width="2"/><text x="240" y="440" text-anchor="middle" class="h">Core idea</text><text x="240" y="480" text-anchor="middle" class="p">What is happening?</text><rect x="450" y="390" width="300" height="145" rx="20" fill="#ffffff" stroke="#c7d2fe" stroke-width="2"/><text x="600" y="440" text-anchor="middle" class="h">Mechanism</text><text x="600" y="480" text-anchor="middle" class="p">Why and how?</text><rect x="810" y="390" width="300" height="145" rx="20" fill="#ffffff" stroke="#c7d2fe" stroke-width="2"/><text x="960" y="440" text-anchor="middle" class="h">Application</text><text x="960" y="480" text-anchor="middle" class="p">Example and exam use</text></g>'''
    return _svg_shell(f"{subject} - learn from beginner to exam level",body,anim)


def build_diagram_svg(question: str, subject: str, animated: bool=True) -> str:
    kind=diagram_kind(question,subject)
    if kind=="volcano": return _volcano_svg(animated)
    if kind=="climate": return _climate_svg(animated)
    if kind=="charged_ring": return _ring_svg(animated)
    if kind=="cell": return _cell_svg(animated)
    return _generic_svg(subject,animated)


def _inline_markup(text: str) -> str:
    # Preserve citation usefulness as readable text while never copying raw HTML
    # into the offline artifact.
    text=re.sub(r'<a\s+href="(https?://[^"\s]+)"[^>]*>(.*?)</a>',
                lambda m:re.sub('<[^>]+>','',m.group(2))+' ('+m.group(1)+')',
                text,flags=re.I)
    text=re.sub(r'\[([^\]]+)\]\((https?://[^)\s]+)\)',r'\1 (\2)',text)
    value=html.escape(text)
    value=re.sub(r'\*\*(.+?)\*\*',r'<strong>\1</strong>',value)
    value=re.sub(r'`([^`]+)`',r'<code>\1</code>',value)
    return value


def markdown_to_safe_html(markdown: str) -> str:
    text=re.sub(r'```(?:math|latex)\s*\n?(.*?)```',r'$$\n\1\n$$',str(markdown or ''),flags=re.I|re.S)
    equations=[]
    def hold(match):
        equations.append(html.escape(match.group(1).strip()))
        return f'\n@@EQ{len(equations)-1}@@\n'
    text=re.sub(r'\$\$(.*?)\$\$',hold,text,flags=re.S)
    output=[]; list_tag=None
    def close_list():
        nonlocal list_tag
        if list_tag: output.append(f'</{list_tag}>'); list_tag=None
    for raw in text.splitlines():
        line=raw.strip()
        if not line: close_list(); continue
        eq=re.fullmatch(r'@@EQ(\d+)@@',line)
        if eq:
            close_list(); output.append(f'<div class="equation" dir="ltr">{equations[int(eq.group(1))]}</div>'); continue
        heading=re.match(r'^(#{1,4})\s+(.+)$',line)
        if heading:
            close_list(); level=min(len(heading.group(1))+1,4); output.append(f'<h{level}>{_inline_markup(heading.group(2))}</h{level}>'); continue
        ordered=re.match(r'^\d+[.)]\s+(.+)$',line)
        bullet=re.match(r'^[-*]\s+(.+)$',line)
        if ordered or bullet:
            wanted='ol' if ordered else 'ul'
            if list_tag!=wanted: close_list(); output.append(f'<{wanted}>'); list_tag=wanted
            output.append(f'<li>{_inline_markup((ordered or bullet).group(1))}</li>'); continue
        close_list(); output.append(f'<p>{_inline_markup(line)}</p>')
    close_list()
    return ''.join(output)


def build_question_html(question: str, answer: str, language: str, subject: str) -> str:
    diagram=build_diagram_svg(question,subject,True)
    svg64=base64.b64encode(diagram.encode()).decode()
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="referrer" content="no-referrer"><title>Exam Saathi Visual Lesson</title><style>
:root{{color-scheme:light}}*{{box-sizing:border-box}}body{{margin:0;background:linear-gradient(145deg,#ede9fe,#ecfeff 55%,#fff1f2);color:#172033;font:17px/1.7 "Noto Sans",system-ui,sans-serif}}header{{padding:48px max(5vw,20px);background:linear-gradient(120deg,#312e81,#7c3aed,#0891b2);color:#fff}}h1{{font-size:clamp(30px,5vw,54px);margin:.2em 0}}main{{max-width:1050px;margin:auto;padding:26px}}section{{background:#ffffffdd;border:1px solid #c7d2fe;border-radius:22px;padding:26px;margin:24px 0;box-shadow:0 12px 30px #312e8120}}img{{width:100%;height:auto;border-radius:18px}}h2,h3,h4{{color:#4338ca}}.question{{background:#fff7ed;border-left:7px solid #f97316}}.equation{{direction:ltr;overflow:auto;background:#172033;color:#f8fafc;padding:14px 18px;border-radius:12px;font:18px/1.6 "Noto Sans Mono",monospace;white-space:pre-wrap}}code{{background:#ede9fe;padding:2px 5px}}button{{background:#4338ca;color:#fff;border:0;border-radius:12px;padding:12px 18px;font-weight:700;cursor:pointer}}.spark{{position:fixed;font-size:34px;animation:float 5s ease-in-out infinite alternate;pointer-events:none}}.s1{{left:2%;top:20%}}.s2{{right:2%;top:45%;animation-delay:-2s}}@keyframes float{{to{{transform:translateY(-45px) rotate(15deg)}}}}@media print{{.spark,button{{display:none}}body{{background:#fff}}section{{box-shadow:none;break-inside:avoid}}}}</style></head><body><span class="spark s1">✨</span><span class="spark s2">📚</span><header><small>EXAM SAATHI AI · {html.escape(subject)} · {html.escape(language)}</small><h1>Visual Answer Pack</h1><p>Beginner idea → mechanism → exam-ready explanation</p><button onclick="window.print()">Print / Save as PDF</button></header><main><section class="question"><h2>Question</h2><p>{html.escape(question)}</p></section><section><h2>Animated concept diagram</h2><img src="data:image/svg+xml;base64,{svg64}" alt="Animated {html.escape(subject)} concept diagram"><p><strong>Tip:</strong> Motion highlights the process; use the explanation below for exact facts.</p></section><section><h2>Verified explanation</h2>{markdown_to_safe_html(answer)}</section><section><h2>Revision method</h2><ol><li>Explain the diagram without looking at the answer.</li><li>Write the core mechanism in three steps.</li><li>Check formulas, labels and exceptions once more.</li></ol></section></main></body></html>'''


def _build_pdf(pdf_path: Path, question: str, answer: str, language: str, subject: str) -> None:
    import fitz
    static_svg=build_diagram_svg(question,subject,False)
    svg_doc=fitz.open(stream=static_svg.encode(),filetype='svg')
    pixmap=svg_doc[0].get_pixmap(matrix=fitz.Matrix(1.5,1.5),alpha=False)
    png_bytes=pixmap.tobytes('png')
    svg_doc.close()
    content=f'''<article><p class="eyebrow">EXAM SAATHI AI | {html.escape(subject)} | {html.escape(language)}</p><h1>Verified explanation</h1>{markdown_to_safe_html(answer)}<div class="note"><b>Revision:</b> Cover the answer, explain the diagram aloud, then verify every label, formula and exception.</div></article>'''
    css='''@page{size:a4;margin:42pt}body{font-family:"Noto Sans",sans-serif;color:#172033;font-size:10.5pt;line-height:1.5}h1{font-size:28pt;color:#312e81;margin:4pt 0 18pt}h2{font-size:17pt;color:#4338ca;margin-top:18pt}h3{color:#0f766e}.eyebrow{color:#0f766e;font-weight:bold}.question{background:#fff4e5;border:1pt solid #fb923c;padding:12pt;border-radius:8pt}.equation{font-family:"Noto Sans Mono",monospace;background:#eef2ff;border-left:4pt solid #4f46e5;padding:9pt;white-space:pre-wrap}img{width:100%;max-height:330pt;object-fit:contain}.note{margin-top:20pt;background:#ecfdf5;border:1pt solid #34d399;padding:12pt}li{margin-bottom:4pt}code{color:#5b21b6}'''
    answer_pdf=pdf_path.with_suffix('.answer.pdf')
    writer=fitz.DocumentWriter(str(answer_pdf))
    page_rect=fitz.paper_rect('a4'); body_rect=page_rect+(42,48,-42,-52)
    story=fitz.Story(content,user_css=css,em=11)
    story.write(writer,lambda number,filled:(page_rect,body_rect,None))
    writer.close()
    answer_doc=fitz.open(answer_pdf)
    doc=fitz.open()
    cover=doc.new_page(width=page_rect.width,height=page_rect.height)
    cover.draw_rect(cover.rect,color=None,fill=(.94,.96,1))
    cover.draw_rect(fitz.Rect(0,0,cover.rect.width,92),color=None,fill=(.19,.18,.51))
    cover.insert_text((42,38),'EXAM SAATHI AI',fontsize=12,fontname='hebo',color=(1,1,1))
    cover.insert_text((42,69),'Visual Answer Pack',fontsize=25,fontname='hebo',color=(1,1,1))
    cover.insert_text((420,53),subject+' | '+language,fontsize=9,color=(.88,.93,1))
    cover.insert_htmlbox(fitz.Rect(42,112,553,225),
        '<h2>Question</h2><p>'+html.escape(question)+'</p>',
        css='body{font-family:"Noto Sans",sans-serif;color:#172033;font-size:10.5pt}h2{color:#4338ca;margin:0 0 6pt}p{margin:0;line-height:1.45}',scale_low=.55)
    cover.insert_image(fitz.Rect(42,245,553,522),stream=png_bytes,keep_proportion=True)
    cover.insert_htmlbox(fitz.Rect(42,548,553,735),
        '<h2>How to use this pack</h2><ol><li>Study the labelled diagram.</li><li>Read the verified explanation from the next page.</li><li>Close the answer and explain the process aloud.</li><li>Recheck formulas, exceptions and source facts.</li></ol>',
        css='body{font-family:"Noto Sans",sans-serif;color:#172033;font-size:10.5pt;line-height:1.5}h2{color:#0f766e}li{margin-bottom:4pt}',scale_low=.7)
    doc.insert_pdf(answer_doc)
    answer_doc.close()
    for index,page in enumerate(doc):
        page.insert_text((42,page.rect.height-25),f'Exam Saathi AI  |  Page {index+1} of {doc.page_count}',fontsize=8,color=(.28,.31,.4))
    doc.save(pdf_path)
    doc.close(); answer_pdf.unlink(missing_ok=True)


def export_question_artifacts(question: str, answer: str, language: str, subject_override: str='Auto'):
    subject=subject_override if subject_override and subject_override!='Auto' else detect_subject(question)
    directory=Path(tempfile.gettempdir())/'exam_saathi_question_exports'
    directory.mkdir(exist_ok=True)
    token=uuid.uuid4().hex
    html_path=directory/f'visual_answer_{token}.html'
    pdf_path=directory/f'visual_answer_{token}.pdf'
    html_path.write_text(build_question_html(question,answer,language,subject),encoding='utf-8')
    _build_pdf(pdf_path,question,answer,language,subject)
    return str(pdf_path),str(html_path),subject
