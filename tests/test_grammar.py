"""Pengujian unit untuk tata bahasa Context-Free Grammar (CFG) sql_subset.lark."""

import unittest
from pathlib import Path
from lark import Lark, LarkError

ROOT = Path(__file__).resolve().parent.parent
GRAMMAR_FILE = ROOT / "src" / "sql_subset.lark"


class TestSQLGrammar(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(GRAMMAR_FILE, "r", encoding="utf-8") as f:
            tata_bahasa = f.read()
        cls.parser = Lark(tata_bahasa, start="start", parser="lalr")

    def test_valid_queries(self):
        valid_queries = [
            "SELECT 1",
            "SELECT a",
            "SELECT * FROM t",
            "SELECT a, b FROM t",
            "SELECT a + 1 AS x FROM t WHERE b = 2",
            "SELECT a FROM t WHERE a > 1 AND b < 2",
            "SELECT a OR b AND c FROM t",
            "SELECT NOT a FROM t",
            "SELECT (a + 1) * 2 FROM t",
            "SELECT COUNT(a) FROM t",
            "SELECT SUM(a), AVG(b) FROM t",
            "SELECT 'teks' FROM t",
            "SELECT a FROM t AS x WHERE a <> 1",
            "SELECT a, b, c FROM t WHERE a <= 1 OR b >= 2",
            "SELECT -a + 1 FROM t",
            "SELECT a % 2 FROM t",
            "SELECT a * (b + c) FROM t",
            "SELECT a FROM t x",
            "SELECT t.a FROM t",
            "SELECT a + b - c FROM t",
            "SELECT (a) FROM t",
            "SELECT abs(a) + 1 FROM t WHERE NOT a = 1",
            "SELECT a FROM t WHERE (a = 1) AND (b = 2)",
            "SELECT 2 * 3 + 4 * 5 FROM t WHERE a = 'x' AND b = 'y'",
        ]
        for query in valid_queries:
            with self.subTest(query=query):
                tree = self.parser.parse(query)
                self.assertIsNotNone(tree)
                self.assertEqual(tree.data, "start")

    def test_invalid_queries(self):
        invalid_queries = [
            "SELECT",
            "SELECT FROM t",
            "SELECT a + FROM t",
            "SELECT (a + 1 FROM t",
            "SELECT a WHERE",
            "FROM t",
            "SELECT a = = 1",
            "SELECT 1 +",
            "SELECT ,a FROM t",
            "SELECT a FROM",
            "SELECT a AND FROM t",
            "WHERE a = 1",
        ]
        for query in invalid_queries:
            with self.subTest(query=query):
                with self.assertRaises(LarkError):
                    self.parser.parse(query)

    def test_operator_precedence(self):
        tree = self.parser.parse("SELECT 1 + 2 * 3")
        found_additive = False
        for sub in tree.find_data("additive"):
            found_additive = True
            child_rules = [c.data for c in sub.children if hasattr(c, "data")]
            self.assertIn("multiplicative", child_rules)
        self.assertTrue(found_additive)


if __name__ == "__main__":
    unittest.main()
