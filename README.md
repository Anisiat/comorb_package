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

## CCI mapping methodology

### ICD-10

ICD-10 comorbidity mappings are based on:

**Quan et al. (2005)**  
*Coding algorithms for defining comorbidities in ICD-9-CM and ICD-10 administrative data.*

### SNOMED CT

SNOMED CT mappings are based on:

**Fortin et al. (2022)**  
*SNOMED CT codelists for Charlson comorbidities.*

Clinically invalid or inappropriate category assignments are excluded from the package mappings where necessary.

### Medication evidence

Medication mappings are manually curated and used only for selected Charlson conditions where relatively specific chronic medications provide useful supporting evidence.

Medication evidence is:

- supportive rather than definitive
- used only for selected comorbidities
- not used to distinguish disease severity or complications

The package retains the evidence source so users can distinguish ICD, SNOMED, and medication-derived evidence.

Clinical collaboration: If you are a clinician and would like to contribute to reviewing and optimising the medication mappings used for comorbidity inference, please get in touch.

## Intended use

The package is designed for iCARE-derived clinical data and provides reusable comorbidity features for downstream clinical research and analysis.

Users may provide one, two, or all three supported source tables depending on data availability.

The package does not connect directly to Snowflake. Users are expected to extract the relevant iCARE data and pass the resulting pandas DataFrames to the package.

## iCARE source tables

### 1. Diagnoses

**Table:** `icare_episodes_diagnosis_anon`

Available fields include:

- `subject` — pseudonymised patient identifier
- `spell_identifier` — unique inpatient spell identifier
- `encntr_id` — pseudonymised inpatient encounter ID
- `episode_identifier` — unique inpatient episode identifier
- `diagnosis_code_icd` — inpatient ICD diagnosis code
- `diagnosis_code_snomed` — inpatient SNOMED diagnosis code
- `diagnosis_desc_icd` — ICD diagnosis description
- `diagnosis_desc_snomed` — SNOMED diagnosis description
- `diagnosis_date` — date of diagnosis
- `diagnosis_seq_n` — diagnosis sequence; `1 = primary`
- `order_no_of_episode` — sequential episode number within a spell
- `update_dt_tm` — date/time of data refresh

Main fields used for CCI derivation:

- `subject`
- `diagnosis_code_icd` and/or `diagnosis_code_snomed`
- `diagnosis_date`, where available

Spell id can be used to add admission date as most diagnosis dates are missing.

Diagnosis descriptions are useful for validation but are not required for code-based mapping.

### 2. Problems

**Table:** `icare_problems_anon`

Available fields include:

- `subject` — pseudonymised patient identifier
- `encntr_id` — pseudonymised encounter ID
- `problem_code` — SNOMED problem code
- `problem_desc` — problem description
- `problem_dt_tm` — date/time the problem was recorded
- `update_dt_tm` — date/time of data refresh

Main fields used for CCI derivation:

- `subject`
- `problem_code`
- `problem_dt_tm`

`problem_desc` is useful for validation but is not required for code-based mapping.

### 3. Prescribing

**Table:** `icare_pharmacy_prescribing_anon`

Available fields include:

- `subject` — pseudonymised patient identifier
- `encntr_id` — pseudonymised encounter ID
- `order_id` — prescription/order identifier
- `admission_medicine_y_n` — whether the patient was admitted on the drug
- `gp_to_continue` — whether the GP should continue the drug after discharge
- `medication_name_cleaned` — cleaned medication name
- `medication_name_short` — shortened medication name
- `ordered_dose_clean` — prescribed dose
- `ordered_drug_form` — drug formulation
- `ordered_frequency` — prescribed frequency
- `ordered_route` — prescribed route
- `ordered_unit` — prescribed unit
- `order_dt_tm` — prescription date/time
- `order_type` — order type
- `prescription_type` — prescription type
- `therapeutical_class` — drug class
- `update_dt_tm` — date/time of data refresh

Main fields used for CCI derivation:

- `subject`
- `medication_name_short` and/or `medication_name_cleaned`
- `order_dt_tm`

Medication evidence supplements diagnosis and problem-code evidence for selected conditions.

## Extraction notes

Only columns required for comorbidity derivation need to be extracted from Snowflake.

Large description fields can be omitted where necessary, since the primary mapping logic uses structured ICD, SNOMED, and medication information.

The package should tolerate partial data availability where possible. For example, diagnosis mapping can proceed using ICD-10 evidence even when SNOMED diagnosis codes are unavailable.

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

## CCI scoring

The package will support calculation of the standard weighted Charlson Comorbidity Index based on the inferred comorbidity categories.

Age-adjusted CCI scoring may be supported separately where users provide an appropriate age variable, as age is not contained within the three core iCARE source tables.

# Module information 

## Cleaning 

takes in raw tables cleans and standardises them 

diagnoses have a lot of missing dates which can be inputed by matching on spell ids and using admission dates as proxy 

keeps track of evidence data and source 

## Mapping

Maps ICD 10 and SNOMED codes from lookups + uses medication to innfer some comorbidities 
importantly - always returns same schema for all tables so they can later be merged into a long table with all the comorbidity information 
for each patient - keeping track of what the source of info was (also keeps track of snomed or icd code?) + evidence date 

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