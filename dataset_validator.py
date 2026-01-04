# dataset_validator.py
import pandas as pd
import re
from typing import Dict, List, Tuple, Optional
import logging
from database import CompanyRequest, CompanyUser

logger = logging.getLogger(__name__)

class DatasetValidator:
    """Validator for company registration datasets"""
    
    # Standard column names (lowercase)
    REQUIRED_COLUMNS = {
        'age', 'experience', 'gender', 'role', 'sector', 
        'company', 'department', 'education', 'salary'
    }
    
    # Common alternative column names mapping
    COLUMN_MAPPINGS = {
        'age': ['age', 'employee_age', 'staff_age', 'age_years', 'dob'],
        'experience': ['experience', 'exp', 'years_experience', 'work_experience', 'yoe', 'years_of_exp'],
        'gender': ['gender', 'sex', 'gender_identity'],
        'role': ['role', 'job_title', 'position', 'title', 'designation', 'job_role'],
        'sector': ['sector', 'industry', 'industry_sector', 'business_sector', 'domain'],
        'company': ['company', 'company_name', 'employer', 'organization', 'company_type'],
        'department': ['department', 'dept', 'division', 'team', 'functional_area'],
        'education': ['education', 'qualification', 'education_level', 'degree', 'highest_degree'],
        'salary': ['salary', 'income', 'compensation', 'pay', 'annual_salary', 'ctc', 'monthly_salary']
    }
    
    @staticmethod
    def validate_required_columns(file_path: str) -> Tuple[bool, str, Dict[str, str]]:
        """
        Validate if dataset has all required columns.
        Returns: (is_valid, message, column_mapping)
        """
        try:
            # Read only first row to get headers
            df = pd.read_csv(file_path, nrows=0)
            actual_columns = [str(col).strip().lower() for col in df.columns]
            
            # Create mapping from actual to standard column names
            column_mapping = {}
            missing_columns = []
            
            for required_col in DatasetValidator.REQUIRED_COLUMNS:
                found = False
                
                # Check for exact match
                if required_col in actual_columns:
                    column_mapping[required_col] = required_col
                    found = True
                else:
                    # Check for alternative names
                    for actual_col in actual_columns:
                        if actual_col in DatasetValidator.COLUMN_MAPPINGS.get(required_col, []):
                            column_mapping[required_col] = actual_col
                            found = True
                            break
                
                if not found:
                    missing_columns.append(required_col)
            
            if missing_columns:
                return False, f"Missing required columns: {', '.join(missing_columns)}", {}
            
            return True, "All required columns found", column_mapping
        
        except Exception as e:
            logger.error(f"Error validating columns: {e}")
            return False, f"Error reading dataset: {str(e)}", {}
    
    @staticmethod
    def check_data_quality(file_path: str, column_mapping: Dict[str, str]) -> Tuple[bool, str]:
        """
        Check basic data quality of the dataset.
        """
        try:
            # Read the entire dataset
            df = pd.read_csv(file_path)
            
            # Map columns if needed (temporary rename for validation)
            temp_mapping = {v: k for k, v in column_mapping.items()}
            # Only rename columns that exist in the mapping
            df = df.rename(columns=temp_mapping)
            
            issues = []
            
            # Check for empty dataset
            if len(df) == 0:
                issues.append("Dataset is empty")
            
            # Check required columns exist
            for col in DatasetValidator.REQUIRED_COLUMNS:
                if col not in df.columns:
                    issues.append(f"Column '{col}' not found after mapping")
            
            # Check for null values in critical columns
            critical_cols = ['age', 'experience', 'salary']
            for col in critical_cols:
                if col in df.columns:
                    null_count = df[col].isnull().sum()
                    if null_count > 0:
                        issues.append(f"Column '{col}' has {null_count} null values")
            
            # Check numeric ranges
            if 'age' in df.columns:
                # Convert to numeric, forcing errors to NaN
                df['age'] = pd.to_numeric(df['age'], errors='coerce')
                invalid_ages = df[(df['age'] < 18) | (df['age'] > 75)]
                if len(invalid_ages) > 0:
                    issues.append(f"Found {len(invalid_ages)} records with age outside reasonable range (18-75)")
            
            if 'experience' in df.columns:
                df['experience'] = pd.to_numeric(df['experience'], errors='coerce')
                invalid_exp = df[df['experience'] < 0]
                if len(invalid_exp) > 0:
                    issues.append(f"Found {len(invalid_exp)} records with negative experience")
            
            if 'salary' in df.columns:
                df['salary'] = pd.to_numeric(df['salary'], errors='coerce')
                invalid_salary = df[df['salary'] <= 0]
                if len(invalid_salary) > 0:
                    issues.append(f"Found {len(invalid_salary)} records with non-positive salary")
            
            if issues:
                return False, "; ".join(issues[:5]) + ("..." if len(issues) > 5 else "")
            
            return True, "Data quality check passed"
        
        except Exception as e:
            logger.error(f"Error checking data quality: {e}")
            return False, f"Error checking data quality: {str(e)}"
    
    @staticmethod
    def check_email_duplicate(email: str, db) -> Tuple[bool, str]:
        """
        Check if email is already used for registration.
        Returns: (is_duplicate, message)
        """
        try:
            # Check in CompanyRequest table
            existing_request = db.query(CompanyRequest).filter(
                CompanyRequest.email == email,
                CompanyRequest.status.in_(["pending", "approved"])
            ).first()
            
            if existing_request:
                if existing_request.status == "pending":
                    return True, f"This email is already used in a pending registration request."
                else:
                    return True, f"This email is already registered. Please use company login."
            
            # Also check in CompanyUser table
            existing_user = db.query(CompanyUser).filter(
                CompanyUser.email == email
            ).first()
            
            if existing_user:
                return True, f"This email is already associated with a company account."
            
            return False, "Email is available"
        
        except Exception as e:
            logger.error(f"Error checking email duplicate: {e}")
            return False, f"Error checking email: {str(e)}"
    
    @staticmethod
    def prepare_mapped_dataset(file_path: str, column_mapping: Dict[str, str]) -> pd.DataFrame:
        """
        Prepare dataset with mapped columns to standard names.
        """
        try:
            df = pd.read_csv(file_path)
            
            # Apply column mapping if provided (Standard Name -> Actual Name)
            # We need to rename Actual Name -> Standard Name
            if column_mapping:
                reverse_mapping = {v: k for k, v in column_mapping.items()}
                df = df.rename(columns=reverse_mapping)
            
            # Ensure all required columns exist (fill with NA if missing)
            for col in DatasetValidator.REQUIRED_COLUMNS:
                if col not in df.columns:
                    df[col] = pd.NA
            
            # Select only required columns (discard extra columns to keep file clean)
            df = df[list(DatasetValidator.REQUIRED_COLUMNS)]
            
            # Clean numeric columns
            numeric_cols = ['age', 'experience', 'salary']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Drop rows where critical target 'salary' is NaN
            df = df.dropna(subset=['salary'])
            
            return df
        
        except Exception as e:
            logger.error(f"Error preparing mapped dataset: {e}")
            raise