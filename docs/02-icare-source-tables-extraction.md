
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