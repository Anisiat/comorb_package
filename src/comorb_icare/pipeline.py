import pandas as pd
from .cleaning.clean_diagnoses import clean_diagnoses
from .cleaning.clean_prescriptions import clean_prescriptions
from .cleaning.clean_problems import clean_problems
from .mapping import map_comorbidities_to_cci
from .features import build_comorbidity_features
import logging
logger = logging.getLogger(__name__)

def build_comorbidity_table(
    cohort_df: pd.DataFrame,
    diagnoses_df: pd.DataFrame | None = None,
    prescriptions_df: pd.DataFrame | None = None,
    problems_df: pd.DataFrame | None = None,
    cutoff_col: str = "discharge_date",
    spell_col: str = "spell_id",
    admission_date_col: str = "admission_date",
    cci_score: bool = False,
        
) -> pd.DataFrame:
    """Build spell-level binary comorbidity features from raw iCARE tables.
    Comorbidities are derived from diagnoses, prescriptions, and problems tables. 
    The function combines these sources, retains evidence recorded before each spell-specific cutoff date, 
    and returns one row per subject and spell with binary comorbidity indicators for 17 CCI conditions.

    Comorbidity evidence tables should be inputed with original colmn names as downloaded from snowdlake
    
    
    Parameters
    ----------
    cohort_df : pd.DataFrame
        Cohort containing ``subject``, the spell identifier, admission date, and cutoff date (e.g. discharge_date).
    diagnoses_df : pd.DataFrame
        Mapped comorbidity table containing ``subject``, ``comorbidity``, and ``comorbidity_date`` derived from diagnoses.
    prescriptions_df : pd.DataFrame
        Mapped comorbidity table containing ``subject``, ``comorbidity``, and ``comorbidity_date`` derived from prescriptions.
    problems_df : pd.DataFrame
        Mapped comorbidity table containing ``subject``, ``comorbidity``, and ``comorbidity_date`` derived from problems.
    cutoff_col : str, default="discharge_date"
        Column in ``cohort_df`` defining the start of the prediction window.
    spell_col : str, default="spell_id"
        Column identifying each spell.
    cci_score : bool, default=False
        Include CCI score in output table.

    Returns
    -------
    pd.DataFrame
        One row per subject and spell with 17 CCI binary comorbidity columns.
    """

    logger.info('Validating input dataframes and required columns...')
     # check at least one comorbidity evidence table is provided
    if all(
        df is None or df.empty
        for df in [diagnoses_df, prescriptions_df, problems_df]
    ):
        raise ValueError("At least one comorbidity evidence table is required.")

    # check that cohort_df is provided and not empty
    if cohort_df is None or cohort_df.empty:
        raise ValueError("Cohort dataframe is required and cannot be empty.")

    # check required columns in cohort_df
    required_cohort_columns = {subject_col, spell_col, cutoff_col}

    for col in required_cohort_columns:
        if col not in cohort_df.columns:
            raise ValueError(
                f"Cohort dataframe is missing required column: {col}"
            )

    logger.info('Cleaning comorbidity evidence tables...')

    spell_dates = cohort_df[
        [spell_col, admission_date_col]
    ].copy()

    spell_dates = spell_dates.rename(
        columns={
            spell_col: "spell_id",
            admission_date_col: "admission_date",
        }
    )

    clean_diagnoses_df = clean_diagnoses(
        diagnoses_df, spell_admission_dates_df = spell_dates) if diagnoses_df is not None else None
    clean_prescriptions_df = clean_prescriptions(prescriptions_df) if prescriptions_df is not None else None
    clean_problems_df = clean_problems(problems_df) if problems_df is not None else None

    logger.info('Mapping comorbidities to CCI conditions...')

    provided_evidence_tables = [
        df for df in [clean_diagnoses_df, clean_prescriptions_df, clean_problems_df] if df is not None
    ]

    mapped_evidence_tables = [
        map_comorbidities_to_cci(df) for df in provided_evidence_tables
    ]

    logger.info('Building spell-level binary comorbidity features...')

    features_df = build_comorbidity_features(
        cohort_df=cohort_df,
        evidence_tables=mapped_evidence_tables,
        cutoff_col=cutoff_col,
        spell_col=spell_col,
        cci_score=cci_score,
    )   

    logger.info('Comorbidity feature building complete.')

    return features_df
