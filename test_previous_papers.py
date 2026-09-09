import tempfile
import unittest
from pathlib import Path

from learning_modes import (catalog_summary, export_catalog, extract_questions,
                            import_catalog, prioritize_notes, profile,
                            register_papers)


class PreviousPaperTests(unittest.TestCase):
    def setUp(self):
        self.identity=profile('CBSE','10','General','Science','2025 syllabus')
        self.notes={'topics':[{'topic':'Photosynthesis'},{'topic':'Force'}],
                    'notes':[{'text':'Force changes motion.','note_number':1},
                             {'text':'Photosynthesis makes food.','note_number':2}],
                    'documents':[{'text':'class notes'}]}

    def add(self,catalog,year,text,kind='Previous exam paper',name=None):
        analysis={'documents':[{'text':text,'source_name':name or f'{year}.pdf','page_number':2}]}
        return register_papers(catalog,analysis,self.identity,year,kind)

    def test_extract_and_rank_real_question_matches(self):
        catalog=[]
        catalog=self.add(catalog,2024,'1. Explain photosynthesis with a labelled diagram?\n2. Define force.')
        catalog=self.add(catalog,2023,'Q1: What is photosynthesis?\nQ2: Calculate speed from the data.')
        updated,report=prioritize_notes(self.notes,catalog,self.identity,2026)
        self.assertIn('2 question match(es) across 2 year(s)',report)
        self.assertIn('2024.pdf · Page 2',report)
        self.assertEqual(updated['topics'][0]['topic'],'Photosynthesis')
        self.assertEqual(updated['notes'][0]['text'],'Photosynthesis makes food.')

    def test_target_window_and_sample_papers_are_excluded(self):
        catalog=self.add([],2015,'1. Explain photosynthesis?')
        catalog=self.add(catalog,2025,'1. Explain photosynthesis?',kind='Sample / practice paper')
        with self.assertRaisesRegex(ValueError,'preceding ten years'):
            prioritize_notes(self.notes,catalog,self.identity,2026)

    def test_portable_catalog_round_trip_and_rejects_bad_file(self):
        catalog=self.add([],2024,'1. Explain photosynthesis?')
        path=Path(export_catalog(catalog));self.addCleanup(path.unlink)
        self.assertEqual(import_catalog(path),catalog)
        self.assertIn('1 extracted question',catalog_summary(catalog))
        with tempfile.NamedTemporaryFile('w',suffix='.json',delete=False) as stream:
            stream.write('{"version":999,"pages":[]}');bad=Path(stream.name)
        self.addCleanup(bad.unlink)
        with self.assertRaisesRegex(ValueError,'not a supported'):
            import_catalog(bad)

    def test_questions_keep_year_file_and_page(self):
        records=extract_questions({'text':'Q1. Define assessment?','year':2022,
            'source_name':'exam.pdf','page_number':7})
        self.assertEqual(records[0]['year'],2022)
        self.assertEqual(records[0]['source_name'],'exam.pdf')
        self.assertEqual(records[0]['page_number'],7)


if __name__=='__main__': unittest.main()
