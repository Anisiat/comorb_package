"""Regression checks for shared source-table cleaning."""

import unittest

import pandas as pd

from comorb_icare.cleaning._utils import _clean_optional_string
from comorb_icare.cleaning.clean_diagnoses import clean_diagnoses
from comorb_icare.cleaning.clean_prescriptions import clean_prescriptions
from comorb_icare.cleaning.clean_problems import clean_problems


class CleaningTests(unittest.TestCase):
    def test_optional_strings(self):
        values = pd.Series([None, pd.NA, float("nan"), "", " \t", " NONE ",
                            "Null", "NaN", "N/A", "na", " A\t B\n", 123])
        cleaned = _clean_optional_string(values)
        self.assertTrue(cleaned.iloc[:10].isna().all())
        self.assertEqual(cleaned.iloc[10:].tolist(), ["A B", "123"])
        self.assertEqual(_clean_optional_string(values, lowercase=True).iloc[10], "a b")
        self.assertEqual(str(cleaned.dtype), "string")

    def test_cleaners_share_validation_and_do_not_mutate_input(self):
        cases = [
            (clean_diagnoses, {"subject": [" P1 "], "diagnosis_code_icd": [" e11.9 "]}),
            (clean_problems, {"subject": [" P1 "], "problem_code": ["123"],
                              "problem_dt_tm": ["2024-01-01"]}),
            (clean_prescriptions, {"subject": [" P1 "], "medication_name_short": [" Drug "],
                                   "therapeutical_class": ["N/A"], "order_dt_tm": ["2024-01-01"]}),
        ]
        for cleaner, data in cases:
            with self.subTest(cleaner=cleaner.__name__):
                raw = pd.DataFrame(data, index=[8])
                raw.columns = [f" {column.upper()} " for column in raw.columns]
                original = raw.copy(deep=True)
                result = cleaner(raw)
                self.assertEqual(result["subject"].tolist(), ["P1"])
                self.assertEqual(result.index.tolist(), [0])
                pd.testing.assert_frame_equal(raw, original)
                with self.assertRaisesRegex(ValueError, "Missing required"):
                    cleaner(pd.DataFrame())
                with self.assertRaisesRegex(ValueError, "Duplicate"):
                    cleaner(pd.DataFrame([[1, 2]], columns=["subject", " SUBJECT "]))
                missing_subject = pd.DataFrame(data).assign(subject=" N/A ")
                with self.assertRaisesRegex(ValueError, "missing subject"):
                    cleaner(missing_subject)

    def test_diagnoses_clean_codes_and_spell_fallback(self):
        raw = pd.DataFrame({
            "subject": ["P1"] * 3,
            "diagnosis_code_icd": [" e11.9 ", "NULL", "N/A"],
            "diagnosis_code_snomed": ["na", " 123456789012345678 ", "none"],
            "diagnosis_desc_icd": [" Type\t 2 ", "NaN", ""],
            "spell_id": [" 12 ", "none", "12"],
        })
        spells = pd.DataFrame({" SPELL_ID ": ["12", None],
                               " ADMISSION_DATE ": ["2024-01-01", "2024-02-01"]})
        result = clean_diagnoses(raw, spells)
        self.assertEqual(len(result), 2)
        self.assertEqual(result.loc[0, "diagnosis_code_icd"], "E119")
        self.assertEqual(result.loc[0, "diagnosis_desc_icd"], "Type 2")
        self.assertEqual(result.loc[0, "comorbidity_date_source"], "spell_admission_date")
        self.assertEqual(result.loc[1, "diagnosis_code_snomed"], "123456789012345678")
        self.assertTrue(pd.isna(result.loc[1, "comorbidity_date"]))
        with self.assertRaisesRegex(ValueError, "at least one"):
            clean_diagnoses(raw[["subject"]])

    def test_diagnosis_dates_use_comorbidity_names(self):
        from comorb_icare.mapping.map_code_to_comorbidity import map_codes_to_comorbidities

        raw = pd.DataFrame({
            "subject": ["P1", "P2", "P3"],
            "diagnosis_code_icd": ["I21"] * 3,
            "diagnosis_date": ["2024-01-01", None, None],
            "spell_id": ["1", "2", "3"],
        })
        spells = pd.DataFrame({"spell_id": ["1", "2"],
                               "admission_date": ["2023-12-01", "2024-02-01"]})
        for fallback in (None, spells):
            with self.subTest(fallback=fallback is not None):
                cleaned = clean_diagnoses(raw, fallback)
                self.assertNotIn("evidence_date", cleaned)
                self.assertNotIn("evidence_date_source", cleaned)
                self.assertEqual(cleaned.loc[0, "comorbidity_date"], pd.Timestamp("2024-01-01"))
                self.assertEqual(cleaned.loc[0, "comorbidity_date_source"], "diagnosis_date")
                self.assertTrue(pd.isna(cleaned.loc[2, "comorbidity_date"]))
                self.assertTrue(pd.isna(cleaned.loc[2, "comorbidity_date_source"]))
                if fallback is not None:
                    self.assertEqual(cleaned.loc[1, "comorbidity_date"], pd.Timestamp("2024-02-01"))
                    self.assertEqual(cleaned.loc[1, "comorbidity_date_source"], "spell_admission_date")
                mapped = map_codes_to_comorbidities(
                    cleaned, "diagnosis_code_icd", "icd", date_col="comorbidity_date"
                )
                pd.testing.assert_series_equal(mapped.comorbidity_date, cleaned.comorbidity_date)
                self.assertEqual(mapped.comorbidity.tolist(), ["myocardial_infarction"] * 3)

    def test_problem_and_prescription_evidence_filtering(self):
        problems = pd.DataFrame({"subject": ["P1"] * 3, "problem_code": ["na", "123", "null"],
                                 "problem_desc": [" Some\n problem ", "none", "n/a"],
                                 "problem_dt_tm": ["invalid"] * 3})
        result = clean_problems(problems)
        self.assertEqual(len(result), 2)
        self.assertEqual(result.loc[0, "problem_desc"], "Some problem")
        self.assertTrue(result["problem_dt_tm"].isna().all())
        self.assertEqual(len(clean_problems(problems.drop(columns="problem_desc"))), 1)
        prescriptions = pd.DataFrame({"subject": ["P1"] * 3,
                                      "medication_name_short": [" Drug\t A ", "NONE", "drug a"],
                                      "therapeutical_class": ["N/A", "null", None],
                                      "order_dt_tm": ["2024-01-01"] * 3})
        result = clean_prescriptions(prescriptions)
        self.assertEqual(result["medication_name_short"].tolist(), ["drug a"])


if __name__ == "__main__":
    unittest.main()
