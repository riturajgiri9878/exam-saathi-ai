import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from question_artifacts import (build_diagram_svg,build_question_html,
                                detect_subject,diagram_kind,
                                export_question_artifacts,
                                markdown_to_safe_html)


class QuestionArtifactTests(unittest.TestCase):
    def test_subject_and_special_diagram_routing(self):
        self.assertEqual(detect_subject('Explain a volcano and plate boundary'),'Geography')
        self.assertEqual(detect_subject('ज्वालामुखी कैसे फटता है?'),'Geography')
        self.assertEqual(diagram_kind('Explain a volcano','Geography'),'volcano')
        self.assertEqual(diagram_kind('Charged ring electric field on its axis','Physics'),'charged_ring')
        self.assertEqual(diagram_kind('Draw and explain an animal cell','Biology'),'cell')

    def test_every_svg_is_valid_and_animation_is_optional(self):
        cases=[('volcano','Geography'),('Atacama climate and rainfall','Geography'),
               ('charged ring electric field','Physics'),('animal cell','Biology'),
               ('French Revolution','History')]
        for question,subject in cases:
            animated=build_diagram_svg(question,subject,True)
            static=build_diagram_svg(question,subject,False)
            ET.fromstring(animated); ET.fromstring(static)
            self.assertIn('@keyframes',animated)
            self.assertNotIn('@keyframes',static)

    def test_untrusted_answer_is_escaped_in_offline_html(self):
        document=build_question_html('Question <script>alert(1)</script>',
                                     'Answer <script>alert(2)</script>',
                                     'English','General Studies')
        self.assertNotIn('<script>alert(1)</script>',document)
        self.assertNotIn('<script>alert(2)</script>',document)
        self.assertIn('&lt;script&gt;alert(2)&lt;/script&gt;',document)
        self.assertIn('@keyframes',document)

    def test_markdown_math_and_lists_are_preserved(self):
        rendered=markdown_to_safe_html('## Result\n$$x=\\frac{a}{b}$$\n1. First\n2. Second')
        self.assertIn('class="equation"',rendered)
        self.assertIn('\\frac',rendered)
        self.assertIn('<ol>',rendered)
        cited=markdown_to_safe_html('<a href="https://example.edu/source" target="_blank">Source 1</a>')
        self.assertIn('Source 1 (https://example.edu/source)',cited)
        self.assertNotIn('<a href=',cited)

    def test_pdf_and_animated_html_are_created(self):
        pdf_file,html_file,subject=export_question_artifacts(
            'Explain the electric field and oscillation of a charged ring.',
            '## Answer\nThe force is restoring.\n\n$$F=-kz$$','English')
        self.assertEqual(subject,'Physics')
        self.assertTrue(Path(pdf_file).is_file())
        self.assertTrue(Path(html_file).is_file())
        self.assertTrue(Path(pdf_file).read_bytes().startswith(b'%PDF'))
        self.assertIn('@keyframes',Path(html_file).read_text(encoding='utf-8'))


if __name__=='__main__':
    unittest.main()
