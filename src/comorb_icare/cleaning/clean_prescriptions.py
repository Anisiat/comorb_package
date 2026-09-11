import pandas as pd

from ._utils import _clean_optional_string


REQUIRED_COLUMNS = frozenset(
    {
        "subject",
        "medication_name_short",
        "therapeutical_class",
        "order_dt_tm",
    }
)


def clean_prescriptions(prescriptions_df: pd.DataFrame) -> pd.DataFrame:
    """Clean longitudinal prescribing records for feature engineering.

    Medication records remain supporting evidence and are not converted into
    Charlson conditions here. Temporal filtering and medicine-to-condition
    mapping belong in the downstream feature-building step.
    """

    # Normalise column names on a copy.
    df = prescriptions_df.copy()
    df.columns = df.columns.astype("string").str.strip().str.lower()

    # Validate the input schema.
    if df.columns.duplicated().any():
        duplicates = sorted(df.columns[df.columns.duplicated()].unique())
        raise ValueError(
            f"Duplicate prescription columns after normalisation: {duplicates}"
        )

    missing_columns = sorted(REQUIRED_COLUMNS - set(df.columns))
    if missing_columns:
        raise ValueError(
            f"Missing required prescription columns: {missing_columns}"
        )

    # Require a usable subject identifier.
    df["subject"] = _clean_optional_string(df["subject"])
    if df["subject"].isna().any():
        raise ValueError("Prescription records contain missing subject identifiers.")

    # Lowercase medication text for consistent matching.
    for column in ("medication_name_short", "therapeutical_class"):
        df[column] = _clean_optional_string(df[column], lowercase=True)

    # Coerce invalid dates to NaT.
    df["order_dt_tm"] = pd.to_datetime(
        df["order_dt_tm"],
        errors="coerce",
    )

    # Report undated records without discarding them.
    n_missing_order_dates = df["order_dt_tm"].isna().sum()

    if n_missing_order_dates:
        print(
            f"{n_missing_order_dates} prescription records "
            "have missing order_dt_tm"
        )

    # Keep records with a medication name or class.
    df = df.dropna(
        subset=["medication_name_short", "therapeutical_class"],
        how="all",
    )

    # Remove duplicate records and reset the index.
    return df.drop_duplicates().reset_index(drop=True)
