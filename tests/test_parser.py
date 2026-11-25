"""Pengujian unit perbandingan parser sqlglot dengan parser CFG Lark."""

import unittest
from pathlib import Path
import sqlglot
from sqlglot import exp
from lark import Lark

ROOT = Path(__file__).resolve().parent.parent
GRAMMAR_FILE = ROOT / "src" / "sql_subset.lark"


class TestParserComparison(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(GRAMMAR_FILE, "r", encoding="utf-8") as f:
            cls.lark_parser = Lark(f.read(), start="start", parser="lalr")

    def test_sample_concordance(self):
        sample_queries = [
            "SELECT 1 + 2 * 3",
            "SELECT a, b FROM t WHERE a = 1",
            "SELECT (a + 1) * 2 FROM t",
            "SELECT a OR b AND c FROM t",
        ]
        for q in sample_queries:
            with self.subTest(query=q):
                ast = sqlglot.parse_one(q)
                lark_tree = self.lark_parser.parse(q)
                self.assertIsInstance(ast, exp.Select)
                self.assertIsNotNone(ast.selects)
                self.assertIsNotNone(lark_tree)


if __name__ == "__main__":
    unittest.main()
