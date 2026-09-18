`comorb-icare` is a Python package for deriving Charlson Comorbidity Index (CCI) features from routinely collected iCARE clinical data.

## Overview

The package uses information from up to three iCARE tables:

- diagnoses
- problems
- prescribing

It identifies the 17 Charlson comorbidities using:

- ICD-10 diagnosis codes
- SNOMED CT codes
- medication evidence for selected conditions

Evidence from these sources is standardised to a common set of CCI comorbidity labels, reconciled across sources, and can then be used to calculate the Charlson Comorbidity Index.

The package is intended to support both:

- lower-level use, where users clean, map, reconcile, or score data step-by-step
- higher-level use, where users provide one or more iCARE tables and receive derived comorbidities and CCI scores directly

IMPORTANT: works using exact iCARE column names.


## Intended use

The package is designed for iCARE-derived clinical data and provides reusable comorbidity features for downstream clinical research and analysis.

Users may provide one, two, or all three supported source tables depending on data availability.

The package does not connect directly to Snowflake. Users are expected to extract the relevant iCARE data and pass the resulting pandas DataFrames to the package.


## Outputs

The package is intended to return two main outputs.

### Evidence table

A long-format table containing the comorbidity evidence identified for each subject:

| subject | comorbidity | evidence_source | code | date |
|---|---|---|---|---|

This preserves the provenance of each inferred comorbidity.

### CCI feature table

A wide-format subject-level table containing:

- binary indicators for the 17 Charlson comorbidities
- the calculated CCI score
- optionally, only the overall score if individual comorbidity flags are not required

Example structure:

| subject | diabetes | heart_failure | ... | cci_score |