"""Shared helpers for cleaning source tables."""

import pandas as pd


MISSING_TEXT_VALUES = frozenset({"", "none", "null", "nan", "n/a", "na"})


def _clean_optional_string(
    values: pd.Series,
    *,
    lowercase: bool = False,
) -> pd.Series:
    """Normalise whitespace and case-insensitive missing-value markers.

    Preserve actual missing values and return nullable strings. Text retains
    its case unless ``lowercase`` is requested.
    """

    # Collapse whitespace while preserving missing values.
    cleaned = (
        values.astype("string")
        .str.strip()
        .str.replace(r"\s+", " ", regex=True)
    )
    if lowercase:
        cleaned = cleaned.str.lower()

    # Match missing markers without changing the output case.
    return cleaned.mask(cleaned.str.lower().isin(MISSING_TEXT_VALUES), pd.NA)
