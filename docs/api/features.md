# Features

Combine mapped evidence into one row per subject and spell. Evidence must be
strictly earlier than the cutoff: records dated exactly at the cutoff are
excluded. Spells without qualifying evidence receive zero-valued indicators.

## Example

This example uses synthetic data and a custom mapping to demonstrate the
cleaning, mapping, and feature-building steps.

```python
import pandas as pd

from comorb_icare.cleaning.clean_diagnoses import clean_diagnoses
from comorb_icare.mapping.map_code_to_comorbidity import map_codes_to_comorbidities
from comorb_icare.features import build_comorbidity_features

cohort = pd.DataFrame({
    "subject": ["example-1"],
    "spell_id": ["spell-1"],
    "admission_date": ["2025-02-01"],
})
diagnoses = pd.DataFrame({
    "subject": ["example-1"],
    "diagnosis_code_icd": ["I21.0"],
    "diagnosis_date": ["2025-01-01"],
})
mapping = pd.DataFrame({
    "icd_code": ["I21"],
    "comorbidity": ["myocardial_infarction"],
})

cleaned = clean_diagnoses(diagnoses)
evidence = map_codes_to_comorbidities(
    cleaned,
    code_col="diagnosis_code_icd",
    code_type="icd",
    date_col="comorbidity_date",
    source="diagnoses",
    mapping_df=mapping,
)
features = build_comorbidity_features(
    cohort,
    evidence_tables=[evidence],
    cutoff_col="admission_date",
    cci_score=True,
)
# myocardial_infarction = 1; cci_score = 1
```

::: comorb_icare.features.build_comorbidity_features
    options:
      heading_level: 2
