"""Actual HTML line wrapping must not corrupt the readable quotation corpus."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from otari_sources import extract_html_text


class HTMLSourceEvidence(unittest.TestCase):
    def test_soft_wrapped_paragraph_remains_one_exact_readable_quote(self):
        html='<p>It is possible for the function to run more than once if\nanother thread calls it before the result is cached.</p>'
        text=extract_html_text(html)
        self.assertIn('more than once if another thread calls it',text)

    def test_separate_paragraphs_do_not_become_one_authored_statement(self):
        text=extract_html_text('<p>Cache data remains coherent.</p><p>Call-once behavior is not guaranteed.</p>')
        self.assertEqual(text,'Cache data remains coherent.\n\nCall-once behavior is not guaranteed.')

    def test_code_indentation_and_newlines_are_preserved(self):
        text=extract_html_text('<p>Example:</p><pre>if retry:\n    commit()\n</pre>')
        self.assertIn('if retry:\n    commit()',text)
