"""Evidence-based revision and class explanations; no built-in paper corpus."""
import copy
import html
import re


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


def prioritize_notes(analysis, catalog, identity, exam_year):
    papers = [p for p in catalog if tuple(p['identity']) == tuple(identity)
              and int(exam_year)-10 <= p['year'] < int(exam_year)
              and p['paper_kind'] == 'Previous exam paper']
    if not papers:
        raise ValueError('No matching previous exam papers in the preceding ten years. Sample papers are excluded.')
    topics = analysis.get('topics', [])
    ranked = []
    for topic in topics:
        phrase = str(topic['topic'])
        pattern = r'(?<!\w)' + re.escape(phrase) + r'(?!\w)'
        hits = [p for p in papers if re.search(pattern, p.get('text',''),re.I)]
        years = sorted({p['year'] for p in hits})
        ranked.append((len(years), phrase, hits))
    ranked.sort(key=lambda row: (-row[0], row[1]))
    coverage = sorted({p['year'] for p in papers})
    output = '## Previous-paper revision evidence\n\n'
    output += 'Uploaded coverage: '+', '.join(map(str,coverage))+f' ({len(coverage)}/10 years).\n\n'
    output += 'Topic mentions across distinct years, not extracted question counts or marks. Metadata is user-entered; verify syllabus alignment. This is not an exam prediction.\n\n'
    reordered = copy.deepcopy(analysis)
    priority = {phrase.casefold(): count for count,phrase,_ in ranked}
    reordered['topics'] = sorted(reordered.get('topics', []), key=lambda t:-priority.get(t['topic'].casefold(),0))
    def note_score(note):
        return sum(count for count, phrase, _ in ranked if count and re.search(r'(?<!\w)'+re.escape(phrase)+r'(?!\w)',note['text'],re.I))
    reordered['notes'] = sorted(reordered.get('notes',[]), key=note_score, reverse=True)
    for i,note in enumerate(reordered['notes'],1): note['note_number']=i
    found = False
    for count, phrase, hits in ranked:
        if not count: continue
        found = True
        output += f'### {html.escape(phrase)} — mentioned in {count} year(s)\n\n'
        for p in hits[:3]:
            output += f'- {html.escape(p["source_name"])} · Page {p["page_number"]} · {p["year"]}\n'
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
