import pandas as pd

from ._utils import _clean_optional_string

REQUIRED_COLUMNS = frozenset(
    {
        "subject",
        "problem_code",
        "problem_dt_tm",
    }
)


def clean_problems(problems_df: pd.DataFrame) -> pd.DataFrame:
    """Clean and standardise historical problem-list records.

    ``problem_code`` is treated as a SNOMED CT concept identifier and kept as
    text so it can be matched exactly to the long-format SNOMED mapping's
    ``snomed_code`` column without risking numeric precision loss.

    Parameters
    ----------
    problems_df : pd.DataFrame
        Raw table containing ``subject``, ``problem_code``, and
        ``problem_dt_tm``. ``problem_desc`` is optional.

    Returns
    -------
    pd.DataFrame
        Copy with normalised column names, stripped string identifiers and
        codes, and parsed dates. Invalid dates become ``NaT``. Rows without
        both a code and a description are removed, as are duplicate rows.

    Raises
    ------
    ValueError
        If required columns are missing, normalised column names are
        duplicated, or subject identifiers are missing.
    """

    # Normalise column names on a copy.
    df = problems_df.copy()
    df.columns = df.columns.astype("string").str.strip().str.lower()

    # Validate the input schema.
    if df.columns.duplicated().any():
        duplicates = sorted(df.columns[df.columns.duplicated()].unique())
        raise ValueError(
            f"Duplicate problem columns after normalisation: {duplicates}"
        )

    missing_columns = sorted(REQUIRED_COLUMNS - set(df.columns))
    if missing_columns:
        raise ValueError(f"Missing required problem columns: {missing_columns}")

    # Require a usable subject identifier.
    df["subject"] = _clean_optional_string(df["subject"])
    if df["subject"].isna().any():
        raise ValueError("Problem records contain missing subject identifiers.")

    # Preserve codes as text and clean optional descriptions.
    df["problem_code"] = _clean_optional_string(df["problem_code"])

    if "problem_desc" in df.columns:
        df["problem_desc"] = _clean_optional_string(df["problem_desc"])

    # Coerce invalid dates to NaT.
    df["problem_dt_tm"] = pd.to_datetime(
        df["problem_dt_tm"],
        errors="coerce",
    )

    # Keep records with a code or description.
    comorbidity_columns = [
        column
        for column in ("problem_code", "problem_desc")
        if column in df.columns
    ]
    df = df.dropna(subset=comorbidity_columns, how="all")

    # Remove duplicate records and reset the index.
    return df.drop_duplicates().reset_index(drop=True)
