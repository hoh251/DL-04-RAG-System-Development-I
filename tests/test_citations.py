import unittest
from src.citations import citation_status


class CitationTests(unittest.TestCase):
    def test_single_and_grouped_references(self):
        self.assertEqual(citation_status("text [1, 2] and [3]", 3)["references"], [1, 2, 3])
        self.assertTrue(citation_status("text [1, 2]", 3)["citations_valid"])

    def test_ranges(self):
        self.assertTrue(citation_status("text [1-3]", 3)["citations_valid"])

    def test_out_of_bounds(self):
        self.assertFalse(citation_status("text [1, 99]", 3)["citations_valid"])
        self.assertFalse(citation_status("text [0]", 3)["citations_valid"])

    def test_malformed_reference(self):
        self.assertFalse(citation_status("text [1, x]", 3)["citations_valid"])

    def test_reverse_or_oversized_range(self):
        self.assertFalse(citation_status("text [3-1]", 3)["citations_valid"])
        self.assertFalse(citation_status("text [1-1000000]", 3)["citations_valid"])

    def test_non_numeric_brackets_are_not_citations(self):
        self.assertFalse(citation_status("text [note]", 3)["has_citation"])
