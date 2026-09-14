import pandas as pd

from ._loaders import load_mapping



def _get_icd_prefixes(mapping_df):
    """Prepare ICD prefixes and their target comorbidity.
    
    Returns a list of tuples (icd_prefix, comorbidity) for subsequent prefix matching."""

    return [
        (str(code).strip().upper().replace(".", ""), comorbidity)
        for code, comorbidity in mapping_df[
            ["icd_code", "comorbidity"]
        ].itertuples(index=False, name=None)

        if pd.notna(code) and pd.notna(comorbidity)
    ]

def _match_icd_code(value, icd_prefixes):
    """Match one ICD-10 code."""

    if pd.isna(value):
        return pd.NA

    # Match the mapping-table format by removing surrounding whitespace,
    # normalising case, and removing decimal points from the observed code.
    observed_code = str(value).strip().upper().replace(".", "")

    # Keep distinct matches in mapping-table order.
    return list(dict.fromkeys(
        comorbidity
        for prefix, comorbidity in icd_prefixes
        if observed_code.startswith(prefix)
    ))


def _get_exact_lookup(mapping, code_column, *, lowercase=False):
    """Build an exact-match lookup."""

    lookup = {}

    for code, comorbidity in mapping[
        [code_column, "comorbidity"]
    ].itertuples(index=False, name=None):

        if pd.isna(code) or pd.isna(comorbidity):
            continue

        key = str(code).strip()

        if lowercase:
            key = key.lower()

        # Deduplicate mapping rows while preserving condition order.
        lookup.setdefault(key, {})[comorbidity] = None

    return {
        key: list(categories)
        for key, categories in lookup.items()
    }


def _match_exact(value, lookup, *, lowercase=False):
    """Match one exact source value."""

    if pd.isna(value):
        return pd.NA

    key = str(value).strip()
    if lowercase:
        key = key.lower()
    return lookup.get(key, pd.NA)


def map_codes_to_comorbidities(
    df: pd.DataFrame,
    code_col: str,
    code_type: str,
    date_col: str,
    source: str | None = None,
    mapping_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Map codes to comorbidities using a mapping DataFrame.
    Specify the code type to use the correct mapping.
    Can either use a provided mapping DataFrame or load the default mapping for the specified code type.

    ICD codes are matched as prefixes, while SNOMED and medication names are matched exactly.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing ``subject`` and the codes to map.
    code_col : str
        Name of the column in df containing the codes to map.
    code_type : str
        Type of code to map. Must be one of 'icd', 'snomed', or 'medication'.
    date_col : str
        Name of the column in df containing the comorbidity dates.
    source : str, optional
        Optional label for source table of comorbidity evidence e.g. diagnoses, problems, prescribing.
    mapping_df : pd.DataFrame, optional
        DataFrame containing the mapping of codes to comorbidities. If not provided, the default mapping for the specified code type will be loaded.
    
    Returns
    -------
    pd.DataFrame
        DataFrame containing ``subject``, ``comorbidity_code_value``,
        ``comorbidity_code_source``, ``comorbidity``, and ``comorbidity_date``.
        Multiple comorbidity matches are expanded into separate rows.
        Unmatched codes retain a row with a missing comorbidity.
    """

    df = df.copy()

    if code_type not in {"icd", "snomed", "medication"}:
        raise ValueError("code_type must be one of 'icd', 'snomed', or 'medication'.")

    if code_col not in df.columns:
        raise ValueError(
            f"df does not contain code column '{code_col}'."
        )
    
    if "subject" not in df.columns:
        raise ValueError("df must contain 'subject'.")

    if date_col not in df.columns:
        raise ValueError(
            f"df does not contain date column '{date_col}'."
        )

    # Preserve the mapped code and choose the source-specific evidence date.
    df["comorbidity_code_value"] = df[code_col].astype("string")

    if source:
        df["comorbidity_code_source"] = source
    else:
        df["comorbidity_code_source"] = code_type

    # Rename and standardize the date column.
    df["comorbidity_date"] = pd.to_datetime(
        df[date_col],
        errors="coerce",
    )

    # Load the default mapping if no mapping DataFrame is provided
    if mapping_df is None:
        mapping_df = load_mapping(code_type)
    
    # Validate the provided mapping DataFrame
    required_columns = {"comorbidity"}

    if code_type == "icd":
        required_columns.add("icd_code")
    elif code_type == "snomed":
        required_columns.add("snomed_code")
    else:
        required_columns.add("medication_name")

    missing_columns = required_columns - set(mapping_df.columns)

    if missing_columns:
        raise ValueError(
            f"Provided mapping DataFrame is missing required columns: {missing_columns}"
        )


    # Prepare ICD prefixes and their target conditions.
    if code_type == "icd":
        icd_prefixes = _get_icd_prefixes(mapping_df)

        df["comorbidity"] = df[code_col].map(
            lambda value: _match_icd_code(value, icd_prefixes)
        )

    elif code_type == "snomed":
        snomed_lookup = _get_exact_lookup(mapping_df, "snomed_code")
        df["comorbidity"] = df[code_col].map(
            lambda x: _match_exact(x, snomed_lookup)
        )

    elif code_type == "medication":
        medication_lookup = _get_exact_lookup(mapping_df, "medication_name", lowercase=True)
        df["comorbidity"] = df[code_col].map(
            lambda x: _match_exact(x, medication_lookup, lowercase=True)
        )

    # Expand matches into rows; unmatched records retain a missing value.
    df = df.explode("comorbidity")
    df["comorbidity"] = df["comorbidity"].astype("string")

    output_columns = [
        "subject",
        "comorbidity_code_value",
        "comorbidity_code_source",
        "comorbidity",
        "comorbidity_date",
    ]

    return df[output_columns].reset_index(drop=True)

