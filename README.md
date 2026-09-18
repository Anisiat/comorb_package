# comorb-icare

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
|---|---:|---:|---|---:|

## Example data completeness

The following missingness values were observed in one cleaned development sample and are included only as an illustration of data availability.

They should not be interpreted as fixed characteristics of the full iCARE dataset.

### Diagnoses

| Column | Missing (%) |
|---|---:|
| `subject` | 0.0 |
| `spell_identifier` | 0.0 |
| `diagnosis_date` | 95.0 |
| `diagnosis_code_icd` | 3.8 |
| `diagnosis_code_snomed` | 95.6 |

### Prescribing

| Column | Missing (%) |
|---|---:|
| `subject` | 0.0 |
| `medication_name_short` | 0.0 |
| `order_dt_tm` | 0.0 |

### Problems

| Column | Missing (%) |
|---|---:|
| `subject` | 0.0 |
| `problem_code` | 2.4 |
| `problem_desc` | 0.1 |
| `problem_dt_tm` | 0.0 |

These patterns motivate a package design that does not require all coding systems or date fields to be present.

In particular:

- ICD-10 diagnosis evidence should remain usable when SNOMED diagnosis codes are missing
- diagnosis dates should be treated as optional where appropriate
- problem-list and prescribing dates can provide additional temporal information
- different evidence sources should be retained separately before reconciliation

## Development roadmap

Planned functionality includes:

- cleaning and standardisation functions for each source table
- mapping functions for ICD-10, SNOMED CT, and medication evidence
- reconciliation of overlapping and hierarchical comorbidity evidence
- standard weighted CCI scoring
- optional age-adjusted CCI scoring where age is provided
- a high-level function that performs the full pipeline automatically
- support for using one, two, or all three iCARE source tables
- retention of evidence provenance for validation and auditability
- double check ICD behaviour - 

This:

return list(dict.fromkeys(
    comorbidity
    for prefix, comorbidity in icd_prefixes
    if observed_code.startswith(prefix)
))

means all matching prefixes are retained.

For example, suppose your mapping contains:

[
    ("I10", "condition_A"),
    ("I109", "condition_B"),
]

and the observed code is:

"I109"

Both match:

"I109".startswith("I10")   # True
"I109".startswith("I109")  # True

so you'd get:

["condition_A", "condition_B"]

That may be exactly what you want, depending on your mapping. Just make sure it is intentional.

For CCI-style mappings, overlapping prefixes can matter, so I'd check your mapping table for this before deciding whether "all matches" or "most specific match" is the desired behaviour.