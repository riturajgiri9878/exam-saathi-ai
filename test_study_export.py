import tempfile
import unittest
from pathlib import Path
from PIL import Image
from study_export import build_study_html, export_study_guide


class StudyExportTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        image = Path(self.directory.name) / 'source.png'
        Image.new('RGB', (300,200), 'white').save(image)
        self.result = {
            'notes':[{'note_number':1,'text':'Force = mass × acceleration. <script>alert(1)</script>', 'source_name':'Physics.pdf','page_number':2}],
            'topics':[{'topic':'Force'}],
            'formulas':[{'formula':'F = ma','source_name':'Physics.pdf','page_number':2}],
            'diagrams':[{'image_path':str(image),'description':'Source diagram','source_name':'Physics.pdf','page_number':2}],
            'question_bank':{'mcq_questions':[{'question':'Unit of force?', 'options':['Newton','Joule'],'answer':'Newton','source_name':'Physics.pdf','page_number':2}]},
        }

    def test_offline_embedded_images_and_safe_text(self):
        output = build_study_html(self.result, '<img onerror=alert(1)>')
        self.assertIn('data:image/jpeg;base64,', output)
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', output)
        self.assertNotIn('<script>alert(1)</script>', output)
        self.assertNotIn('https://', output)
        self.assertIn('Physics.pdf · Page 2', output)
        for key in ('sprint','notes','formulas','diagrams','cards','quiz','review'):
            self.assertIn(f'id="{key}"', output)

    def test_text_only(self):
        self.assertNotIn('data:image', build_study_html(self.result, include_diagrams=False))

    def test_missing_image_keeps_notes(self):
        self.result['diagrams'][0]['image_path'] = '/does-not-exist.png'
        output = build_study_html(self.result)
        self.assertIn('1 image(s) unavailable', output)
        self.assertIn('Force = mass', output)

    def test_no_analysis(self):
        with self.assertRaises(ValueError):
            build_study_html({})

    def test_export_unique(self):
        first = Path(export_study_guide(self.result))
        second = Path(export_study_guide(self.result))
        self.addCleanup(first.unlink)
        self.addCleanup(second.unlink)
        self.assertNotEqual(first,second)
        self.assertIn('data:image',first.read_text())


if __name__ == '__main__':
    unittest.main()
