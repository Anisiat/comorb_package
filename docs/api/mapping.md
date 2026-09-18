# Mapping

Use `load_mapping` to inspect a bundled lookup or pass your own lookup to
`map_codes_to_comorbidities`. ICD codes use prefix matching; SNOMED codes use
exact matching; medication names use case-insensitive exact matching.

| Cleaned source | `code_col` | `code_type` | `date_col` |
| --- | --- | --- | --- |
| Diagnoses, ICD | `diagnosis_code_icd` | `icd` | `comorbidity_date` |
| Diagnoses, SNOMED | `diagnosis_code_snomed` | `snomed` | `comorbidity_date` |
| Problems | `problem_code` | `snomed` | `problem_dt_tm` |
| Prescriptions | `medication_name_short` | `medication` | `order_dt_tm` |

Only map code columns that exist in your cleaned table. Map ICD and SNOMED
separately if you want evidence from both diagnosis code systems.

```python
from comorb_icare.mapping import load_mapping
from comorb_icare.mapping.map_code_to_comorbidity import map_codes_to_comorbidities

icd_mapping = load_mapping("icd")
```

::: comorb_icare.mapping.load_mapping
    options:
      heading_level: 2

::: comorb_icare.mapping.map_code_to_comorbidity.map_codes_to_comorbidities
    options:
      heading_level: 2
