"""
test_suite.py - Automated Unit Tests for Database and AI Extractor Parsing
"""

import os
import unittest
import tempfile
import json
import db
import extractor


class TestTransactionApp(unittest.TestCase):
    def setUp(self):
        # Create a temporary SQLite database for testing
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()
        db.init_db(self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_database_crud(self):
        # 1. Add transaction
        tx_id = db.add_transaction(
            date="2026-08-20",
            merchant="Trader Joe's",
            category="Groceries",
            total_amount=45.67,
            currency="$",
            tax_amount=3.20,
            items=[{"name": "Organic Milk", "qty": 2, "price": 8.00}, {"name": "Bananas", "qty": 1, "price": 2.50}],
            payment_method="Credit Card",
            notes="Weekly grocery shopping",
            db_path=self.db_path
        )
        self.assertIsNotNone(tx_id)

        # 2. Get transaction
        tx = db.get_transaction(tx_id, db_path=self.db_path)
        self.assertEqual(tx["merchant"], "Trader Joe's")
        self.assertEqual(tx["total_amount"], 45.67)
        self.assertEqual(len(tx["items"]), 2)

        # 3. Add second transaction
        db.add_transaction(
            date="2026-08-21",
            merchant="Starbucks",
            category="Dining & Food",
            total_amount=12.50,
            currency="$",
            db_path=self.db_path
        )

        # 4. Check stats
        stats = db.get_stats(db_path=self.db_path)
        self.assertEqual(stats["count"], 2)
        self.assertEqual(stats["total_spent"], 58.17)
        self.assertEqual(len(stats["by_category"]), 2)

        # 5. Search
        results = db.get_all_transactions(search_query="Starbucks", db_path=self.db_path)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["merchant"], "Starbucks")

        # 6. Export CSV
        csv_file = tempfile.NamedTemporaryFile(suffix=".csv", delete=False).name
        try:
            exported_count = db.export_to_csv(csv_file, db_path=self.db_path)
            self.assertEqual(exported_count, 2)
            with open(csv_file, "r") as f:
                content = f.read()
                self.assertIn("Trader Joe's", content)
                self.assertIn("Starbucks", content)
        finally:
            if os.path.exists(csv_file):
                os.remove(csv_file)

        # 7. Delete transaction
        db.delete_transaction(tx_id, db_path=self.db_path)
        stats_after = db.get_stats(db_path=self.db_path)
        self.assertEqual(stats_after["count"], 1)

    def test_json_cleaner(self):
        # Test markdown code fenced JSON
        raw_markdown = '```json\n{"merchant": "Apple Store", "total_amount": 999.00, "date": "2026-08-15", "category": "Shopping"}\n```'
        parsed = extractor._clean_and_parse_json(raw_markdown)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["merchant"], "Apple Store")
        self.assertEqual(parsed["total_amount"], 999.00)

        # Test plain text with nested json
        raw_text = 'Here is the extracted data: {"merchant": "Uber", "total_amount": 25.50, "date": "2026-08-10", "category": "Transport & Travel"}'
        parsed2 = extractor._clean_and_parse_json(raw_text)
        self.assertIsNotNone(parsed2)
        self.assertEqual(parsed2["merchant"], "Uber")
        self.assertEqual(parsed2["total_amount"], 25.50)


if __name__ == "__main__":
    unittest.main()
