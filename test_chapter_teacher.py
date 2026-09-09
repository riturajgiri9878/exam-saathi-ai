"""Offline contract/failure tests. These do not simulate Gemini answer quality."""
import copy
import ast
from pathlib import Path
import unittest
from chapter_teacher import lesson_steps, source_units, validate_batch, render_lesson
from study_export import build_study_html


def batch_fixture(units):
    ids=[u['id'] for u in units]
    return {'covered_source_ids':ids,'topics':[{
        'title':'Test and measurement','definition':'A test collects responses; measurement assigns numbers.',
        'story':'A teacher gives her class ten questions about fractions. She then counts the correct answers and records a score. These are related actions, but they perform different jobs.',
        'analogy_limit':'A score does not explain every reason for a learning difficulty.',
        'steps':['Choose tasks that match the lesson.','Collect student responses.','Use a scoring rule to assign numbers.'],
        'example':'Riya answers eight of ten fraction questions correctly. The questions are the test; assigning eight out of ten is measurement.',
        'memory_tip':'Test asks; measurement numbers.','takeaways':['Tests collect evidence.','Scores describe one aspect of performance.'],
        'check_question':'Which action is measurement: asking a question or assigning a score?',
        'source_ids':ids,'diagram':{'kind':'comparison','caption':'Two related roles',
            'nodes':[{'label':'Test','detail':'Questions/tasks'},{'label':'Measurement','detail':'Numerical description'}]},
        'comparison':[]}],
        'short_questions':[{'question':'What is measurement?','answer':'Assigning numerical values according to a rule.','why':'Distinguishes a tool from its score.','source_ids':ids}],
        'long_questions':[{'question':'Compare testing and measurement with a classroom example.',
            'answer':'A test presents tasks; measurement assigns numbers to the responses using a scoring rule.',
            'outline':['Define each term.','Describe the fraction test.','Explain how the score was assigned.'],
            'why':'Combines definitions with application.','source_ids':ids}],
        'revision_points':['A test uses tasks.','Measurement describes performance numerically.']}


class ChapterTests(unittest.TestCase):
    def setUp(self):
        self.analysis={'documents':[{'text':('first concept '*2500)+' LAST TOPIC CCE',
            'source_name':'Notes.txt','page_number':1,'extraction_method':'Pasted Text'}]}

    def test_partition_keeps_every_character_and_last_topic(self):
        units=source_units(self.analysis)
        self.assertEqual(''.join(u['text'] for u in units),self.analysis['documents'][0]['text'])
        self.assertIn('LAST TOPIC CCE',units[-1]['text'])
        self.assertGreater(len(units),4)

    def test_all_batches_and_cached_resume(self):
        calls=[]
        def provider(prompt,units,language):
            calls.extend(u['id'] for u in units)
            return batch_fixture(units)
        lesson=list(lesson_steps(self.analysis,'English',provider=provider))[-1]
        self.assertEqual(lesson['status'],'complete')
        self.assertEqual(calls,[u['id'] for u in source_units(self.analysis)])
        old=len(calls)
        list(lesson_steps(self.analysis,'English',existing=lesson,provider=provider))
        self.assertEqual(len(calls),old)
        list(lesson_steps(self.analysis,'Hindi',existing=lesson,provider=provider))
        self.assertGreater(len(calls),old)

    def test_partial_resume_does_not_repeat_completed_batch(self):
        calls=[]
        def fails(prompt,units,language):
            calls.append(units[0]['id'])
            if len(calls)==2: raise TimeoutError()
            return batch_fixture(units)
        partial=list(lesson_steps(self.analysis,'English',provider=fails))[-1]
        self.assertEqual(partial['status'],'partial')
        self.assertEqual(len(partial['batches']),1)
        resumed=[]
        def succeeds(prompt,units,language):
            resumed.append(units[0]['id']); return batch_fixture(units)
        complete=list(lesson_steps(self.analysis,'English',existing=partial,provider=succeeds))[-1]
        self.assertEqual(complete['status'],'complete')
        self.assertNotIn('S1',resumed)
        self.assertEqual(complete['errors'],{})

    def test_reject_incomplete_or_invented_references(self):
        units=source_units(self.analysis)[:3]
        for mutate in (lambda d:d.update(covered_source_ids=['S1']),
                       lambda d:d['topics'][0].update(source_ids=['invented']),
                       lambda d:d.update(long_questions=[])):
            data=batch_fixture(units);mutate(data)
            with self.assertRaises(ValueError):validate_batch(data,units)

    def test_export_same_lesson_and_safe_rendering(self):
        lesson=list(lesson_steps(self.analysis,'English',provider=lambda p,u,l:batch_fixture(u)))[-1]
        lesson['batches']['0']['topics'][0]['title']='<script>alert(1)</script>'
        rendered=render_lesson(lesson)
        self.assertNotIn('<script>',rendered)
        self.assertIn('&lt;script&gt;',rendered)
        output=build_study_html(dict(self.analysis,detailed_lesson=lesson))
        self.assertIn('Two related roles',output)
        self.assertIn('Compare testing and measurement',output)
        self.assertIn('Explain how the score was assigned.',output)
        changed=copy.deepcopy(self.analysis);changed['documents'][0]['text']='different upload'
        with self.assertRaises(ValueError):build_study_html(dict(changed,detailed_lesson=lesson))

    def test_empty_source_does_not_fabricate_lesson(self):
        with self.assertRaises(ValueError):list(lesson_steps({'documents':[]},'English'))

    def test_ui_export_failure_preserves_generated_lesson(self):
        # Execute the real callback with controlled dependencies, without importing Gradio.
        tree=ast.parse(Path(__file__).with_name('app.py').read_text())
        fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='build_chapter_ui')
        lesson=list(lesson_steps(self.analysis,'English',provider=lambda p,u,l:batch_fixture(u)))[-1]
        class FakeGr:
            @staticmethod
            def skip(): return 'SKIP'
        def fail_export(*a): raise OSError('disk full')
        namespace={'gr':FakeGr,'lesson_steps':lambda *a:iter([lesson]),
                   'render_lesson':render_lesson,'lesson_plain':lambda l:'context',
                   'export_study_guide':fail_export,'diagram_gallery_items':lambda a:[]}
        exec(compile(ast.Module(body=[fn],type_ignores=[]),'app.py','exec'),namespace)
        result=list(namespace['build_chapter_ui'](self.analysis,'','English',{}))[-1]
        self.assertEqual(len(result),6)
        self.assertEqual(result[2],lesson)
        self.assertIn('HTML creation failed',result[3])


if __name__=='__main__': unittest.main()
