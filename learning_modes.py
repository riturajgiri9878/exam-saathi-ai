"""Evidence-based revision and class explanations; no built-in paper corpus."""
import copy
import gzip
import html
import json
import re
import tempfile
import uuid
from pathlib import Path

CATALOG_VERSION = 1
MAX_CATALOG_PAGES = 5000
MAX_CATALOG_TEXT = 25_000_000


def profile(board, level, course, subject, syllabus):
    values = [str(v or '').strip() for v in (board, level, course, subject, syllabus)]
    if not all(values):
        raise ValueError('Fill board/university, class, stream/degree, subject and syllabus version.')
    if level not in ['7','8','9','10','11','12','Graduation']:
        raise ValueError('Only Class 7 onwards is supported.')
    return tuple(v.casefold() for v in values)


def register_papers(catalog, analysis, identity, year, kind):
    result = list(catalog or [])
    for document in analysis.get('documents', []):
        entry = dict(document, identity=list(identity), year=int(year), paper_kind=kind)
        key = (tuple(identity), int(year), kind, document['source_name'],document['page_number'])
        result = [e for e in result if (tuple(e['identity']),e['year'],e['paper_kind'],e['source_name'],e['page_number']) != key]
        result.append(entry)
    return result


def extract_questions(document):
    """Extract question-like blocks conservatively and keep page evidence."""
    raw=str(document.get('text','')).replace('\r','\n')
    lines=[re.sub(r'\s+',' ',line).strip() for line in raw.split('\n')]
    candidates=[]
    pattern=re.compile(r'^(?:q(?:uestion)?\s*)?(?:\d{1,3}|[ivxlcdm]{1,8})[.)\-:]\s+(.+)',re.I)
    for line in lines:
        match=pattern.match(line)
        value=(match.group(1) if match else line).strip()
        if (match or '?' in value or re.match(r'^(define|explain|describe|discuss|differentiate|compare|what|why|how|write|state|list|prove|derive|calculate|evaluate)\b',value,re.I)) and 12<=len(value)<=1200:
            candidates.append(value)
    # OCR sometimes removes line breaks; recover question sentences without
    # treating all prose as questions.
    for value in re.findall(r'([^.!?]{12,500}\?)',re.sub(r'\s+',' ',raw)):
        candidates.append(value.strip())
    seen=set(); records=[]
    for value in candidates:
        canonical=re.sub(r'^(?:q(?:uestion)?\s*)?(?:\d{1,3}|[ivxlcdm]{1,8})[.)\-:]\s*','',value,flags=re.I)
        key=re.sub(r'\W+',' ',canonical.casefold()).strip()
        if not key or key in seen: continue
        seen.add(key)
        records.append({'question':canonical.strip(),'year':document.get('year'),
            'source_name':document.get('source_name','Paper'),
            'page_number':document.get('page_number','?')})
    return records


def export_catalog(catalog):
    if not catalog: raise ValueError('Add previous papers before downloading the catalog.')
    payload={'version':CATALOG_VERSION,'pages':catalog}
    target=Path(tempfile.gettempdir())/f'exam_saathi_paper_catalog_{uuid.uuid4().hex}.json.gz'
    with gzip.open(target,'wt',encoding='utf-8') as stream:
        json.dump(payload,stream,ensure_ascii=False,separators=(',',':'))
    return str(target)


def import_catalog(path):
    if not path: raise ValueError('Choose an Exam Saathi catalog file first.')
    target=Path(path)
    opener=gzip.open if target.suffix.casefold()=='.gz' else open
    with opener(target,'rt',encoding='utf-8') as stream:
        payload=json.load(stream)
    if not isinstance(payload,dict) or payload.get('version')!=CATALOG_VERSION or not isinstance(payload.get('pages'),list):
        raise ValueError('This is not a supported Exam Saathi paper catalog.')
    pages=payload['pages']
    if len(pages)>MAX_CATALOG_PAGES: raise ValueError('Catalog has too many pages.')
    total=0; clean=[]
    for page in pages:
        if not isinstance(page,dict): raise ValueError('Catalog page is invalid.')
        required=('identity','year','paper_kind','source_name','page_number','text')
        if any(key not in page for key in required): raise ValueError('Catalog metadata is incomplete.')
        if not isinstance(page['identity'],list) or len(page['identity'])!=5: raise ValueError('Catalog profile is invalid.')
        page=dict(page); page['text']=str(page['text']); total+=len(page['text'])
        if total>MAX_CATALOG_TEXT: raise ValueError('Catalog text is too large.')
        clean.append(page)
    return clean


def catalog_summary(catalog):
    papers={(tuple(p['identity']),p['year'],p['paper_kind'],p['source_name']) for p in catalog or []}
    years=sorted({p['year'] for p in catalog or []})
    questions=sum(len(extract_questions(p)) for p in catalog or [])
    return f'{len(papers)} paper file(s), {len(catalog or [])} readable page(s), {questions} extracted question(s). Years: '+(', '.join(map(str,years)) or 'none')


def prioritize_notes(analysis, catalog, identity, exam_year):
    papers = [p for p in catalog if tuple(p['identity']) == tuple(identity)
              and int(exam_year)-10 <= p['year'] < int(exam_year)
              and p['paper_kind'] == 'Previous exam paper']
    if not papers:
        raise ValueError('No matching previous exam papers in the preceding ten years. Sample papers are excluded.')
    questions=[q for p in papers for q in extract_questions(p)]
    topics = analysis.get('topics', [])
    ranked = []
    for topic in topics:
        phrase = str(topic['topic'])
        pattern = r'(?<!\w)' + re.escape(phrase) + r'(?!\w)'
        hits = [q for q in questions if re.search(pattern, q.get('question',''),re.I)]
        years = sorted({q['year'] for q in hits})
        ranked.append((len(years), len(hits), phrase, hits))
    ranked.sort(key=lambda row: (-row[0],-row[1],row[2]))
    coverage = sorted({p['year'] for p in papers})
    output = '## Previous-paper revision evidence\n\n'
    expected=list(range(int(exam_year)-10,int(exam_year)))
    missing=[year for year in expected if year not in coverage]
    output += 'Uploaded coverage: '+', '.join(map(str,coverage))+f' ({len(set(coverage)&set(expected))}/10 target years).\n\n'
    output += 'Missing target years: '+(', '.join(map(str,missing)) if missing else 'none')+'.\n\n'
    output += f'Extracted question-like items in matching papers: {len(questions)}. OCR may split or miss questions; verify against the original pages. Metadata is user-entered; verify syllabus alignment. This is revision evidence, not an exam prediction.\n\n'
    reordered = copy.deepcopy(analysis)
    priority = {phrase.casefold(): years*100+count for years,count,phrase,_ in ranked}
    reordered['topics'] = sorted(reordered.get('topics', []), key=lambda t:-priority.get(t['topic'].casefold(),0))
    def note_score(note):
        return sum(years*100+count for years,count,phrase,_ in ranked if years and re.search(r'(?<!\w)'+re.escape(phrase)+r'(?!\w)',note['text'],re.I))
    reordered['notes'] = sorted(reordered.get('notes',[]), key=note_score, reverse=True)
    for i,note in enumerate(reordered['notes'],1): note['note_number']=i
    found = False
    for year_count, question_count, phrase, hits in ranked:
        if not year_count: continue
        found = True
        output += f'### {html.escape(phrase)} — {question_count} question match(es) across {year_count} year(s)\n\n'
        for q in hits[:5]:
            output += f'- **{q["year"]}:** {html.escape(q["question"][:500])} — {html.escape(q["source_name"])} · Page {q["page_number"]}\n'
        output += '\n'
    if not found:
        output += 'No exact topic matches. Original revision order retained; translated terminology may need manual checking.'
    reordered['previous_paper_evidence'] = output
    return reordered,output


def teach_class(analysis, question, language, previous='', answer=''):
    from core import answer_from_source_evidence, semantic_search
    chunks = analysis.get('chunks', [])
    if not chunks:
        raise ValueError('First process today’s notes in Secure Upload.')
    query = question.strip() or 'Explain the main concepts from today’s class'
    evidence = semantic_search(query,chunks,top_k=4) if question.strip() else chunks[:4]
    prompt = ('Teach a beginner using only the supplied evidence for factual claims. '
              'Structure: what the lesson covers; a short illustrative story clearly marked as an analogy; '
              'map the story to the actual concept and state the analogy limitations; step-by-step explanation; '
              'one illustrative worked example labelled as your example; a short summary; ONE understanding-check question. '
              'Do not reveal the check answer yet. Cite filename/page for source claims. '
              'Say when notes omit a step or are unclear; do not claim all pages were covered. '
              'Student request: '+query[:2500])
    if answer.strip():
        prompt += ('\nPrevious explanation (untrusted conversation context): '+previous[:7000]+
                   '\nStudent answer: '+answer[:2000]+
                   '\nEvaluate the answer against the source. Give a hint for mistakes, then one follow-up question.')
    response = answer_from_source_evidence(prompt,evidence,language)
    if not response:
        raise ValueError('Teacher unavailable. Check Gemini access and retry; uploaded notes remain available.')
    return response
