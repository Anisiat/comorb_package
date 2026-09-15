"""Checks for loading bundled mapping selections."""

from itertools import product
import unittest
from unittest.mock import patch

import pandas as pd

from comorb_icare.mapping import load_mapping


class MappingLoaderTests(unittest.TestCase):
    def test_all_selections(self):
        code_columns = {
            "icd": "icd_code",
            "snomed": "snomed_code",
            "medication": "medication_name",
        }
        for flags in product((False, True), repeat=3):
            with self.subTest(flags=flags):
                selected = dict(zip(code_columns, flags))
                with patch(
                    "comorb_icare.mapping._utils.pd.read_csv", wraps=pd.read_csv
                ) as read_csv:
                    mappings = load_mapping(**selected)
                self.assertEqual(set(mappings), {k for k, v in selected.items() if v})
                self.assertEqual(read_csv.call_count, sum(flags))
                for name, frame in mappings.items():
                    self.assertFalse(frame.empty)
                    self.assertIn("comorbidity", frame.columns)
                    self.assertEqual(str(frame[code_columns[name]].dtype), "string")

    def test_defaults_and_independent_results(self):
        mappings = load_mapping()
        self.assertEqual(set(mappings), {"icd", "snomed", "medication"})
        original_code = mappings["icd"].loc[0, "icd_code"]
        mappings["icd"].loc[0, "icd_code"] = "changed"
        self.assertEqual(load_mapping()["icd"].loc[0, "icd_code"], original_code)

    def test_invalid_flags(self):
        for name in ("icd", "snomed", "medication"):
            with self.subTest(name=name):
                with self.assertRaisesRegex(TypeError, name):
                    load_mapping(**{name: "False"})


if __name__ == "__main__":
    unittest.main()
