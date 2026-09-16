import pytest 
import pandas as pd 

from comorb_icare.cleaning.clean_diagnoses import clean_diagnoses


@pytest.fixture
def diagnoses_df():
    """ 
    Fixture to create a sample diagnoses dataframe for testing.
    """
    data = {
        'subject': [1, 2, 3],
        'spell_identifier': ['A01', 'B02', 'C03'],
        'diagnosis_date': ['2021-01-01', '2021-02-01', '2021-03-01'], 
        'diagnosis_code_icd': ['D001', 'D002', 'D003'],
        'diagnosis_code_snomed': ['S001', 'S002', 'S003'],
    }
    return pd.DataFrame(data)

def test_columns_are_normalised(diagnoses_df):
    """
    Test that the column names are normalised correctly.
    """
    df = diagnoses_df.rename(columns={'spell_identifier': 'SPELL_ID', 'diagnosis_date': 'DIAGNOSIS_DATE '})
    cleaned_df = clean_diagnoses(df)

    assert 'spell_id' in cleaned_df.columns
    assert 'diagnosis_date' in cleaned_df.columns
    
def test_columns_are_validated():
    """ 
    Test correct columns are validated in the input dataframe.
    """

    data = {
        'spell_identifier': ['A01', 'B02', 'C03'],
        'diagnosis_date': ['2021-01-01', '2021-02-01', '2021-03-01'], 
        'diagnosis_code_icd': ['D001', 'D002', 'D003'],
        'diagnosis_code_snomed': ['S001', 'S002', 'S003'],
    }

    df = pd.DataFrame(data)

    with pytest.raises(ValueError):
        clean_diagnoses(df)


def test_require_min_one_code_col(diagnoses_df):
    """
    Test that at least one of the code columns is required.
    """
    df = diagnoses_df.drop(columns=['diagnosis_code_icd', 'diagnosis_code_snomed'])
    
    with pytest.raises(ValueError):
        clean_diagnoses(df)


def test_missing_subject_values_are_reported():
    """
    Test that missing subject values are reported as an error.
    """
    df = pd.DataFrame({
        'subject': [1, None, 3],
        'spell_identifier': ['A01', 'B02', 'C03'],
        'diagnosis_date': ['2021-01-01', '2021-02-01', '2021-03-01'], 
        'diagnosis_code_icd': ['D001', 'D002', 'D003'],
        'diagnosis_code_snomed': ['S001', 'S002', 'S003'],
    })

    with pytest.raises(ValueError):
        clean_diagnoses(df)


def test_codes_are_cleaned(diagnoses_df):
    """
    Test that the diagnosis codes are cleaned correctly.
    """
    df = diagnoses_df.copy()
    df['diagnosis_code_icd'] = [' d001 ', 'D002', ' d0.03 ']
    df['diagnosis_code_snomed'] = [' s001 ', 'S002', ' 7667 ']

    cleaned_df = clean_diagnoses(df)

    assert cleaned_df['diagnosis_code_icd'].tolist() == ['D001', 'D002', 'D003']
    assert cleaned_df['diagnosis_code_snomed'].tolist() == ['S001', 'S002', '7667']