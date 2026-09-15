"""Quick validation checks for the CCI/comorbidity feature pipeline.

Run inside the SDE after importing this file/project. It does not modify source data.
It rebuilds the CCI evidence table from the configured cleaned inputs and prints
a compact set of diagnostics for mapping, reconciliation, aggregation and scoring.
"""

from pathlib import Path
import pandas as pd

from steps.build_comorbidity_features import (
    CONFIG_PATH,
    COMORBIDITY_COLUMN_MAP,
    CCI_WEIGHTS,
    load_config_paths,
    load_datasets,
    load_mapping,
    filter_prescriptions_to_cci_mapping,
    standardise_comorbidity_df,
    fill_missing_diagnosis_dates,
    combine_comorbidity_datasets,
    map_comorbidities_to_cci,
    reconcile_cci_mapping,
    aggregate_comorbidities_by_infection_episode,
    calculate_cci_score,
)


def run_checks(config_path=CONFIG_PATH):
    print("\n=== CCI PIPELINE VALIDATION ===")

    cfg = load_config_paths(config_path)
    datasets = load_datasets(cfg)
    mappings = load_mapping(cfg)

    # Match production behaviour: remove prescriptions with no CCI mapping.
    n_rx_before = len(datasets["prescriptions"])
    datasets["prescriptions"] = filter_prescriptions_to_cci_mapping(
        datasets["prescriptions"], mappings["medication"]
    )
    print(f"\nPrescriptions retained for CCI: {len(datasets['prescriptions']):,} / {n_rx_before:,}")

    # Build longitudinal evidence table.
    standardised = []
    for source, column_map in COMORBIDITY_COLUMN_MAP.items():
        df = standardise_comorbidity_df(
            datasets[source],
            source=source,
            column_map=column_map,
        )
        if source == "diagnoses":
            df = fill_missing_diagnosis_dates(df, datasets["infection_eps"])
        standardised.append(df)

    combined = combine_comorbidity_datasets(standardised)
    mapped = map_comorbidities_to_cci(combined, mappings)

    # ------------------------------------------------------------------
    # 1. Mapping sanity checks
    # ------------------------------------------------------------------
    print("\n--- Mapping checks ---")

    icd_prefixes = tuple(
        str(x).strip().upper().replace(".", "")
        for x in mappings["icd"]["icd_code"].dropna().unique()
    )

    icd_codes = mapped["icd_code"].dropna().astype(str).str.strip().str.upper().str.replace(".", "", regex=False)
    icd_should_map = mapped.loc[mapped["icd_code"].notna()].copy()
    icd_should_map["_code"] = icd_codes
    icd_should_map = icd_should_map.loc[
        icd_should_map["_code"].str.startswith(icd_prefixes, na=False)
        & icd_should_map["icd_comorbidity"].isna()
    ]

    snomed_mapping_codes = set(
        mappings["snomed"]["snomed_code"].dropna().astype(str).str.strip()
    )
    snomed_failed = mapped.loc[
        mapped["snomed_code"].notna()
        & mapped["snomed_code"].astype(str).str.strip().isin(snomed_mapping_codes)
        & mapped["snomed_comorbidity"].isna()
    ]

    med_mapping_names = set(
        mappings["medication"]["medication_name"].dropna().astype(str).str.strip().str.lower()
    )
    med_failed = mapped.loc[
        mapped["medication_name"].notna()
        & mapped["medication_name"].astype(str).str.strip().str.lower().isin(med_mapping_names)
        & mapped["medication_comorbidity"].isna()
    ]

    print(f"ICD rows matching a configured prefix but not mapped: {len(icd_should_map):,}")
    if len(icd_should_map):
        print(icd_should_map["icd_code"].value_counts().head(20))

    print(f"SNOMED rows present in mapping but not mapped: {len(snomed_failed):,}")
    if len(snomed_failed):
        print(snomed_failed["snomed_code"].value_counts().head(20))

    print(f"Medication rows present in mapping but not mapped: {len(med_failed):,}")
    if len(med_failed):
        print(med_failed["medication_name"].value_counts().head(20))

    # ------------------------------------------------------------------
    # 2. Reconciliation checks
    # ------------------------------------------------------------------
    reconciled = reconcile_cci_mapping(mapped)

    print("\n--- Reconciliation checks ---")
    print(f"Coding conflicts: {int(reconciled['coding_conflict'].sum()):,}")

    conflicts = reconciled.loc[
        reconciled["coding_conflict"].eq(1),
        ["icd_code", "snomed_code", "icd_comorbidity", "snomed_comorbidity", "cci_condition"],
    ]
    if not conflicts.empty:
        print(conflicts.drop_duplicates().head(20).to_string(index=False))

    n_unmapped = reconciled["cci_condition"].isna().sum()
    print(f"Evidence rows with no final CCI condition: {n_unmapped:,} / {len(reconciled):,}")

    # ------------------------------------------------------------------
    # 3. Episode aggregation + score checks
    # ------------------------------------------------------------------
    flags = aggregate_comorbidities_by_infection_episode(
        reconciled,
        datasets["infection_eps"],
    )
    scored = calculate_cci_score(flags)

    print("\n--- Episode-level checks ---")
    print(f"Infection episodes expected: {len(datasets['infection_eps']):,}")
    print(f"Infection episodes returned: {len(scored):,}")
    print(f"Duplicate episode index: {scored.index.duplicated().any()}")

    flag_cols = list(CCI_WEIGHTS)
    non_binary = {
        col: sorted(scored[col].dropna().unique().tolist())
        for col in flag_cols
        if not set(scored[col].dropna().unique()).issubset({0, 1})
    }
    print(f"Non-binary CCI flag columns: {non_binary or 'None'}")

    print(
        "CCI score range:",
        int(scored["cci_score"].min()),
        "to",
        int(scored["cci_score"].max()),
    )

    # Nested conditions should not double-count in the score.
    scoring_copy = scored[flag_cols].copy()
    scoring_copy.loc[
        scoring_copy["diabetes_with_complication"].eq(1),
        "diabetes_without_complication",
    ] = 0
    scoring_copy.loc[
        scoring_copy["moderate_or_severe_liver_disease"].eq(1),
        "mild_liver_disease",
    ] = 0
    scoring_copy.loc[
        scoring_copy["metastatic_solid_tumor"].eq(1),
        "malignancy",
    ] = 0

    expected_score = sum(
        scoring_copy[c] * w for c, w in CCI_WEIGHTS.items()
    )
    print(f"CCI score mismatches: {(expected_score != scored['cci_score']).sum():,}")

    # ------------------------------------------------------------------
    # 4. Quick temporal summary
    # ------------------------------------------------------------------
    dated = reconciled.loc[
        reconciled["subject"].notna()
        & pd.to_datetime(reconciled["comorbidity_date"], errors="coerce").notna()
        & reconciled["cci_condition"].notna()
    ].copy()
    dated["comorbidity_date"] = pd.to_datetime(dated["comorbidity_date"], errors="coerce")

    episodes = datasets["infection_eps"][["subject", "infection_id", "admission_date"]].copy()
    episodes["admission_date"] = pd.to_datetime(episodes["admission_date"], errors="coerce")

    # Count evidence occurring after admission; this is allowed in the longitudinal
    # source table, but it must not contribute to the admission-cutoff CCI flags.
    future_pairs = episodes.merge(
        dated[["subject", "comorbidity_date"]],
        on="subject",
        how="inner",
    )
    future_n = (future_pairs["comorbidity_date"] > future_pairs["admission_date"]).sum()
    print(f"Post-admission CCI evidence rows seen before filtering: {future_n:,}")
    print("(These are expected to be excluded by the episode aggregation cutoff.)")

    # Hard assertions for things that should never fail.
    assert len(scored) == len(datasets["infection_eps"])
    assert not scored.index.duplicated().any()
    assert not non_binary
    assert (expected_score == scored["cci_score"]).all()

    print("\n✅ Core CCI checks passed.")
    return scored


if __name__ == "__main__":
    run_checks()
