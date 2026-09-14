import pandas as pd

from ._utils import _clean_optional_string


REQUIRED_COLUMNS = frozenset({"subject"})

CODE_COLUMNS = {
    "diagnosis_code_icd",
    "diagnosis_code_snomed",
}


def clean_diagnoses(
    diagnoses_df: pd.DataFrame,
    spell_admission_dates_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Clean an iCARE diagnoses table for downstream comorbidity mapping.

    This function performs the following operations:
    1. Normalises column names.
    2. Validates the input schema.
    3. Cleans available codes, descriptions and spell identifiers.
    4. Coerces invalid or absent diagnosis dates to NaT.
    5. Uses spell admission dates as an optional fallback.

    Parameters
    ----------
    diagnoses_df : pd.DataFrame
        Raw iCARE diagnoses table.

    spell_admission_dates_df : pd.DataFrame, optional
        Optional table containing spell admission dates for approximate
        diagnosis-date inference. If provided, it must contain:
        ``spell_id`` and ``admission_date``.

    Returns
    -------
    pd.DataFrame
        Cleaned diagnoses table containing the original diagnosis fields,
        plus:

    - ``comorbidity_date``: best available date for the diagnosis evidence.
    - ``comorbidity_date_source``: source used to derive ``comorbidity_date``.

    If ``spell_admission_dates_df`` is provided, ``admission_date`` is
    also included and is used as a fallback when ``diagnosis_date`` is
    unavailable.

    Notes
    -----
    At least one of ``diagnosis_code_icd`` or ``diagnosis_code_snomed``
    must be present.

    Invalid dates are converted to ``NaT``.

    If spell admission dates are supplied, ``comorbidity_date`` is populated
    using ``diagnosis_date`` where available and ``admission_date`` as a
    fallback.
    """

    # Normalise column names on a copy.
    df = diagnoses_df.copy()
    df.columns = df.columns.astype("string").str.strip().str.lower()

    # Validate the input schema.
    if df.columns.duplicated().any():
        duplicates = sorted(df.columns[df.columns.duplicated()].unique())
        raise ValueError(
            f"Duplicate diagnosis columns after normalisation: {duplicates}"
        )

    missing_columns = sorted(REQUIRED_COLUMNS - set(df.columns))
    if missing_columns:
        raise ValueError(
            f"Missing required diagnosis columns: {missing_columns}"
        )

    # Require at least one coding system.
    if not CODE_COLUMNS.intersection(df.columns):
        raise ValueError(
            "diagnoses_df must contain at least one of: "
            "'diagnosis_code_icd', 'diagnosis_code_snomed'."
        )

    # Require a usable subject identifier.
    df["subject"] = _clean_optional_string(df["subject"])
    if df["subject"].isna().any():
        raise ValueError("Diagnosis records contain missing subject identifiers.")

    # Clean available codes, descriptions and spell identifiers.
    for column in (
        "diagnosis_code_icd",
        "diagnosis_code_snomed",
        "diagnosis_desc_icd",
        "diagnosis_desc_snomed",
        "spell_id",
    ):
        if column in df.columns:
            df[column] = _clean_optional_string(df[column])

    # Keep ICD codes uppercase and remove dots.
    if "diagnosis_code_icd" in df.columns:
        df["diagnosis_code_icd"] = _clean_optional_string(
            df["diagnosis_code_icd"].str.upper().str.replace(".", "", regex=False)
        )

    # Coerce invalid or absent diagnosis dates to NaT.
    if "diagnosis_date" in df.columns:
        df["diagnosis_date"] = pd.to_datetime(
            df["diagnosis_date"],
            errors="coerce",
        )
    else:
        df["diagnosis_date"] = pd.NaT

    # Use spell admission dates as an optional fallback.
    if spell_admission_dates_df is not None:
        spell_dates = spell_admission_dates_df.copy()

        spell_dates.columns = spell_dates.columns.astype("string").str.strip().str.lower()

        if spell_dates.columns.duplicated().any():
            duplicates = sorted(
                spell_dates.columns[spell_dates.columns.duplicated()].unique()
            )
            raise ValueError(
                f"Duplicate spell admission columns after normalisation: {duplicates}"
            )

        required_spell_columns = {
            "spell_id",
            "admission_date",
        }

        missing = required_spell_columns - set(spell_dates.columns)

        if missing:
            raise ValueError(
                f"spell_admission_dates_df is missing required columns: "
                f"{sorted(missing)}"
            )

        if "spell_id" not in df.columns:
            raise ValueError(
                "diagnoses_df must contain 'spell_id' when "
                "spell_admission_dates_df is provided."
            )

        spell_dates["spell_id"] = _clean_optional_string(spell_dates["spell_id"])

        # Prevent missing spell identifiers from matching.
        spell_dates = spell_dates.dropna(subset=["spell_id"])

        # Coerce invalid admission dates to NaT.
        spell_dates["admission_date"] = pd.to_datetime(
            spell_dates["admission_date"],
            errors="coerce",
        )

        # Remove any duplicate records for the same spell IDs.

        spell_dates = spell_dates.drop_duplicates()

        if spell_dates["spell_id"].duplicated().any():
            raise ValueError(
                "spell_admission_dates_df contains multiple records "
                "for the same spell_id."
            )

        # Attach admission dates by spell.
        df = df.merge(
            spell_dates[["spell_id", "admission_date"]],
            on="spell_id",
            how="left",
        )

        # Prefer diagnosis dates and record the chosen source.
        df["comorbidity_date"] = df["diagnosis_date"].fillna(
            df["admission_date"]
        )

        df["comorbidity_date_source"] = "diagnosis_date"
        df.loc[
            df["diagnosis_date"].isna()
            & df["admission_date"].notna(),
            "comorbidity_date_source",
        ] = "spell_admission_date"

        df.loc[
            df["comorbidity_date"].isna(),
            "comorbidity_date_source",
        ] = pd.NA

    else:
        df["comorbidity_date"] = df["diagnosis_date"]

        df["comorbidity_date_source"] = (
            df["diagnosis_date"]
            .notna()
            .map({True: "diagnosis_date", False: pd.NA})
        )

    # Keep records with at least one diagnosis code.
    comorbidity_columns = [
        column
        for column in ("diagnosis_code_icd", "diagnosis_code_snomed")
        if column in df.columns
    ]
    df = df.dropna(subset=comorbidity_columns, how="all")

    # Remove duplicate records and reset the index.
    return df.drop_duplicates().reset_index(drop=True)
