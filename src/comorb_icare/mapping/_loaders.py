"""Shared helpers for loading mapping tables."""

from importlib.resources import files

import pandas as pd


MAPPING_OPTIONS = {
    "icd": ("charlson_icd10_mapping.csv", "icd_code"),
    "snomed": ("charlson_snomed_mapping.csv", "snomed_code"),
    "medication": ("charlson_medication_mapping.csv", "medication_name"),
}


def load_mapping(mapping_type: str) -> pd.DataFrame:
    """Load one bundled CCI mapping table.

    Parameters
    ----------
    mapping_type : str
        Mapping to load. Must be one of:
        ``"icd"``, ``"snomed"`` or ``"medication"``.

    Returns
    -------
    pd.DataFrame
        Selected CCI mapping table. Mapping values are loaded as nullable
        strings for reliable matching.
    """

    if mapping_type not in MAPPING_OPTIONS:
        raise ValueError(
            f"mapping_type must be one of {list(MAPPING_OPTIONS)}"
        )

    filename, code_column = MAPPING_OPTIONS[mapping_type]

    data_directory = files("comorb_icare").joinpath("data")

    with data_directory.joinpath(filename).open("rb") as source:
        mapping = pd.read_csv(
            source,
            dtype={code_column: "string"},
        )

    return mapping