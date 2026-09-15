"""Regression checks for scalar comorbidity mapping."""

import unittest

import pandas as pd

from comorb_icare.mapping.map_code_to_comorbidity import map_codes_to_comorbidities
from comorb_icare.pipeline import (
    map_comorbidities_to_cci,
    reconcile_cci_mapping,
    aggregate_comorbidities_by_infection_episode,
)


class ScalarMappingTests(unittest.TestCase):
    def test_shared_output_for_all_three_tables(self):
        cases = [
            ("diagnoses", "diagnosis_code_icd", "icd", "I21", "diagnosis_date"),
            ("problems", "problem_code", "snomed", "95443002", "problem_dt_tm"),
            ("prescriptions", "medication_name_short", "medication", "aclidinium", "order_dt_tm"),
        ]
        outputs = []
        for source, column, code_type, code, date_column in cases:
            with self.subTest(source=source):
                raw = pd.DataFrame({"subject": ["P"], column: [code],
                                    date_column: ["2020-01-01"]})
                result = map_codes_to_comorbidities(raw, column, code_type, source=source)
                self.assertEqual(result.columns.tolist(), ["subject", "comorbidity",
                                 "evidence_source", "evidence_value", "evidence_date"])
                self.assertEqual(result.loc[0, "evidence_source"], source)
                self.assertEqual(result.loc[0, "evidence_value"], code)
                self.assertEqual(result.loc[0, "evidence_date"], pd.Timestamp("2020-01-01"))
                outputs.append(result)
        self.assertEqual(pd.concat(outputs, ignore_index=True).shape, (3, 5))

    def test_date_precedence_and_missing_dates(self):
        raw = pd.DataFrame({"subject": ["P"], "code": ["I21"],
                            "evidence_date": ["2021-01-01"],
                            "diagnosis_date": ["2020-01-01"]})
        result = map_codes_to_comorbidities(raw, "code", "icd")
        self.assertEqual(result.loc[0, "evidence_date"], pd.Timestamp("2021-01-01"))
        result = map_codes_to_comorbidities(raw[["subject", "code"]], "code", "icd")
        self.assertTrue(pd.isna(result.loc[0, "evidence_date"]))
        self.assertEqual(result.loc[0, "evidence_source"], "icd")
        with self.assertRaisesRegex(ValueError, "subject"):
            map_codes_to_comorbidities(raw[["code"]], "code", "icd")

    def test_default_icd_and_medication(self):
        result = map_codes_to_comorbidities(
            pd.DataFrame({"subject": ["P"] * 3, "code": [" i21.9 ", None, "unknown"]}), "code", "icd"
        )
        self.assertEqual(result.loc[0, "comorbidity"], "myocardial_infarction")
        self.assertTrue(result.comorbidity.iloc[1:].isna().all())
        self.assertEqual(str(result.comorbidity.dtype), "string")
        result = map_codes_to_comorbidities(
            pd.DataFrame({"subject": ["P"], "code": [" ACLIDINIUM "]}), "code", "medication"
        )
        self.assertEqual(result.loc[0, "comorbidity"], "chronic_pulmonary_disease")

    def test_exact_lookup_retains_all_codes_and_repeated_rows(self):
        mapping = pd.DataFrame({"snomed_code": ["1", "2", "1"],
                                "comorbidity": ["renal_disease", "dementia", "renal_disease"]})
        raw = pd.DataFrame({"subject": ["P"] * 4, "code": ["1", " 2 ", None, "3"]})
        result = map_codes_to_comorbidities(raw, "code", "snomed", mapping_df=mapping)
        self.assertEqual(result.comorbidity.iloc[:2].tolist(), ["renal_disease", "dementia"])
        self.assertTrue(result.comorbidity.iloc[2:].isna().all())
        self.assertNotIn("comorbidity", raw)

    def test_multiple_matches_expand_rows(self):
        result = map_codes_to_comorbidities(
            pd.DataFrame({"code": ["194781004"], "subject": ["P"]}), "code", "snomed"
        )
        self.assertEqual(result.comorbidity.tolist(), ["congestive_heart_failure", "renal_disease"])
        self.assertEqual(result.subject.tolist(), ["P", "P"])
        mapping = pd.DataFrame({"icd_code": ["A", "A1", "A1"],
                                "comorbidity": ["dementia", "renal_disease", "renal_disease"]})
        result = map_codes_to_comorbidities(
            pd.DataFrame({"subject": ["P"], "code": ["A12"]}), "code", "icd", mapping_df=mapping
        )
        self.assertEqual(result.comorbidity.tolist(), ["dementia", "renal_disease"])
        self.assertEqual(str(result.comorbidity.dtype), "string")

    def test_expansion_preserves_pipeline_subjects(self):
        from comorb_icare.mapping import load_mapping

        mappings = {name: load_mapping(name) for name in ("icd", "snomed", "medication")}
        raw = pd.DataFrame({"subject": ["P", "Q"], "icd_code": [None, None],
                            "snomed_code": ["194781004", "95443002"],
                            "medication_name": [None, None],
                            "comorbidity_date": ["2020-01-01"] * 2}, index=[7, 7])
        result = reconcile_cci_mapping(map_comorbidities_to_cci(raw, mappings))
        self.assertEqual(result.subject.tolist(), ["P", "P", "Q"])
        self.assertEqual(result.cci_condition.tolist(),
                         ["congestive_heart_failure", "renal_disease", "peripheral_vascular_disease"])
        episodes = pd.DataFrame({"subject": ["P"], "infection_id": [1],
                                 "admission_date": ["2021-01-01"]})
        flags = aggregate_comorbidities_by_infection_episode(result, episodes)
        self.assertEqual(flags.loc[("P", 1), "congestive_heart_failure"], 1)
        self.assertEqual(flags.loc[("P", 1), "renal_disease"], 1)
        self.assertEqual(len(raw), 2)

    def test_pipeline_reconciliation_and_aggregation(self):
        mappings = {
            "icd": pd.DataFrame({"icd_code": ["A"], "comorbidity": ["dementia"]}),
            "snomed": pd.DataFrame({"snomed_code": ["1"], "comorbidity": ["renal_disease"]}),
            "medication": pd.DataFrame({"medication_name": ["drug"], "comorbidity": ["dementia"]}),
        }
        raw = pd.DataFrame({"subject": ["P"] * 3, "icd_code": ["A", None, None],
                            "snomed_code": ["1", None, None],
                            "medication_name": [None, "drug", None],
                            "comorbidity_date": ["2020-01-01"] * 3})
        result = reconcile_cci_mapping(map_comorbidities_to_cci(raw, mappings))
        self.assertEqual(result.cci_condition.iloc[:2].tolist(), ["renal_disease", "dementia"])
        self.assertTrue(pd.isna(result.cci_condition.iloc[2]))
        self.assertEqual(result.coding_conflict.tolist(), [1, 0, 0])
        episodes = pd.DataFrame({"subject": ["P"], "infection_id": [1], "admission_date": ["2021-01-01"]})
        flags = aggregate_comorbidities_by_infection_episode(result, episodes)
        self.assertEqual(flags.loc[("P", 1), "renal_disease"], 1)
        self.assertEqual(flags.loc[("P", 1), "dementia"], 1)


if __name__ == "__main__":
    unittest.main()
