#  train_company.py - ENHANCED VERSION
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from joblib import dump
import json
from pathlib import Path
import config
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_dataset(df):
    """Comprehensive dataset analysis for options generation"""
    analysis = {
        'numeric_ranges': {},
        'categorical_options': {},
        'data_quality': {},
        'feature_importance': {}
    }
    
    # Analyze numeric columns
    numeric_columns = ['age', 'experience', 'salary']
    for col in numeric_columns:
        if col in df.columns:
            analysis['numeric_ranges'][col] = {
                'min': float(df[col].min()),
                'max': float(df[col].max()),
                'mean': float(df[col].mean()),
                'median': float(df[col].median()),
                'std': float(df[col].std()),
                'q25': float(df[col].quantile(0.25)),
                'q75': float(df[col].quantile(0.75))
            }
    
    # Analyze categorical columns
    categorical_columns = ['gender', 'role', 'sector', 'company', 'department', 'education']
    for col in categorical_columns:
        if col in df.columns:
            value_counts = df[col].value_counts()
            analysis['categorical_options'][col] = {
                'options': sorted(df[col].dropna().astype(str).unique().tolist()),
                'counts': value_counts.to_dict(),
                'top_5': value_counts.head(5).index.tolist(),
                'unique_count': int(df[col].nunique())
            }
    
    # Data quality analysis
    analysis['data_quality'] = {
        'total_records': len(df),
        'missing_values': df.isnull().sum().to_dict(),
        'duplicate_records': df.duplicated().sum(),
        'salary_stats': {
            'min_salary': float(df['salary'].min()),
            'max_salary': float(df['salary'].max()),
            'avg_salary': float(df['salary'].mean()),
            'median_salary': float(df['salary'].median())
        } if 'salary' in df.columns else {}
    }
    
    return analysis

def validate_company_dataset(df):
    """Enhanced dataset validation with detailed reporting"""
    required_columns = ['age', 'experience', 'gender', 'role', 'sector', 'company', 'department', 'education', 'salary']
    
    # Check required columns
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        return False, f"Missing required columns: {', '.join(missing_columns)}"
    
    validation_issues = []
    
    # Validate numeric ranges
    if 'age' in df.columns:
        age_issues = df[(df['age'] < 18) | (df['age'] > 70)]
        if len(age_issues) > 0:
            validation_issues.append(f"Found {len(age_issues)} records with age outside reasonable range (18-70)")
    
    if 'experience' in df.columns:
        exp_issues = df[(df['experience'] < 0) | (df['experience'] > 50)]
        if len(exp_issues) > 0:
            validation_issues.append(f"Found {len(exp_issues)} records with experience outside reasonable range (0-50)")
    
    if 'salary' in df.columns:
        salary_issues = df[df['salary'] < 0]
        if len(salary_issues) > 0:
            validation_issues.append(f"Found {len(salary_issues)} records with negative salary")
        
        # Check for extremely high salaries (potential outliers)
        Q1 = df['salary'].quantile(0.25)
        Q3 = df['salary'].quantile(0.75)
        IQR = Q3 - Q1
        high_outliers = df[df['salary'] > (Q3 + 3 * IQR)]
        if len(high_outliers) > 0:
            validation_issues.append(f"Found {len(high_outliers)} potential salary outliers")
    
    # Check for data diversity
    for col in ['role', 'department', 'education']:
        if col in df.columns and df[col].nunique() < 2:
            validation_issues.append(f"Column '{col}' has insufficient diversity (only 1 unique value)")
    
    if validation_issues:
        return True, f"Dataset validated with warnings: {'; '.join(validation_issues)}"
    
    return True, "Dataset is valid and ready for training"

def train_company_model(dataset_path, company_name):
    """Enhanced company model training with better feature engineering"""
    try:
        logger.info(f"🏢 Training enhanced model for company: {company_name}")
        
        # Load and validate dataset
        df = pd.read_csv(dataset_path)
        logger.info(f"📊 Dataset loaded with {len(df)} records and {len(df.columns)} columns")
        
        # Validate dataset
        is_valid, validation_message = validate_company_dataset(df)
        if not is_valid:
            raise ValueError(validation_message)
        
        logger.info(f"✅ Dataset validation: {validation_message}")
        
        # Analyze dataset for options generation
        dataset_analysis = analyze_dataset(df)
        logger.info("📈 Dataset analysis completed")
        
        # Enhanced preprocessing
        df_clean = df.copy()
        
        # Handle missing values strategically
        for col in df_clean.columns:
            if df_clean[col].dtype == 'object':
                df_clean[col] = df_clean[col].fillna('Unknown')
            else:
                df_clean[col] = df_clean[col].fillna(df_clean[col].median())
        
        # Remove duplicates
        initial_count = len(df_clean)
        df_clean = df_clean.drop_duplicates()
        duplicates_removed = initial_count - len(df_clean)
        if duplicates_removed > 0:
            logger.info(f"🧹 Removed {duplicates_removed} duplicate records")
        
        # Feature engineering
        df_clean = create_features(df_clean)
        
        # Prepare features and target
        X = df_clean.drop('salary', axis=1)
        y = df_clean['salary']
        
        # Split data with stratification if possible
        stratification_col = None
        if 'department' in X.columns and X['department'].nunique() > 1:
            stratification_col = X['department']
        elif 'role' in X.columns and X['role'].nunique() > 1:
            stratification_col = X['role']
        
        if stratification_col is not None:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=stratification_col
            )
            logger.info("📊 Using stratified train-test split")
        else:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
            logger.info("📊 Using random train-test split")
        
        logger.info(f"📈 Training set: {len(X_train)} records")
        logger.info(f"📊 Test set: {len(X_test)} records")
        
        # Define preprocessing
        numeric_features = [f for f in ['age', 'experience', 'experience_squared', 'age_experience_ratio'] if f in X.columns]
        categorical_features = [f for f in ['gender', 'role', 'sector', 'company', 'department', 'education'] if f in X.columns]
        
        logger.info(f"🔢 Using numeric features: {numeric_features}")
        logger.info(f"🔠 Using categorical features: {categorical_features}")
        
        # Enhanced preprocessing pipeline
        numeric_transformer = Pipeline(steps=[
            ('imputer', SimpleImputer(strategy='median')),
            ('scaler', StandardScaler())
        ])
        
        categorical_transformer = Pipeline(steps=[
            ('imputer', SimpleImputer(strategy='constant', fill_value='Unknown')),
            ('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=False))
        ])
        
        preprocessor = ColumnTransformer(
            transformers=[
                ('num', numeric_transformer, numeric_features),
                ('cat', categorical_transformer, categorical_features)
            ]
        )
        
        # Enhanced Random Forest with optimized parameters
        model = RandomForestRegressor(
            n_estimators=200,
            max_depth=25,
            min_samples_split=5,
            min_samples_leaf=2,
            max_features='sqrt',
            bootstrap=True,
            random_state=42,
            n_jobs=-1,
            verbose=0
        )
        
        pipeline = Pipeline(steps=[
            ('preprocessor', preprocessor),
            ('regressor', model)
        ])
        
        logger.info("🚀 Training enhanced model...")
        pipeline.fit(X_train, y_train)
        
        # Comprehensive evaluation
        y_pred = pipeline.predict(X_test)
        
        accuracy = r2_score(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        mae = mean_absolute_error(y_test, y_pred)
        
        # Calculate MAPE safely
        y_test_nonzero = y_test[y_test != 0]
        if len(y_test_nonzero) > 0:
            y_pred_nonzero = y_pred[y_test != 0]
            mape = np.mean(np.abs((y_test_nonzero - y_pred_nonzero) / y_test_nonzero)) * 100
        else:
            mape = 0.0
        
        # Cross-validation
        cv_scores = cross_val_score(pipeline, X, y, cv=5, scoring='r2')
        cv_mean = cv_scores.mean()
        cv_std = cv_scores.std()
        
        logger.info(f"✅ Model trained successfully!")
        logger.info(f"📊 R² Score: {accuracy:.4f}")
        logger.info(f"📏 RMSE: {rmse:,.2f}")
        logger.info(f"📏 MAE: {mae:,.2f}")
        logger.info(f"📏 MAPE: {mape:.2f}%")
        logger.info(f"🎯 Cross-validation R²: {cv_mean:.4f} (±{cv_std:.4f})")
        
        # Save model and metadata
        model_filename = f"{company_name.replace(' ', '_').lower()}_model.pkl"
        model_path = config.COMPANY_MODELS_FOLDER / model_filename
        dump(pipeline, model_path)
        
        # Enhanced metadata with options
        metadata = {
            'company_name': company_name,
            'model_accuracy': accuracy,
            'cv_accuracy': cv_mean,
            'rmse': rmse,
            'mae': mae,
            'mape': mape,
            'features_used': {
                'numeric': numeric_features,
                'categorical': categorical_features
            },
            'dataset_analysis': dataset_analysis,
            'dataset_size': len(df_clean),
            'training_records': len(X_train),
            'test_records': len(X_test),
            'model_parameters': model.get_params(),
            'training_date': pd.Timestamp.now().isoformat()
        }
        
        metadata_path = config.COMPANY_MODELS_FOLDER / f"{company_name.replace(' ', '_').lower()}_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)
        
        # Save options for frontend
        options = generate_frontend_options(dataset_analysis)
        options_path = config.COMPANY_MODELS_FOLDER / f"{company_name.replace(' ', '_').lower()}_options.json"
        with open(options_path, 'w') as f:
            json.dump(options, f, indent=2)
        
        logger.info(f"💾 Model saved to: {model_path}")
        logger.info(f"📄 Metadata saved to: {metadata_path}")
        logger.info(f"🎛️  Frontend options saved to: {options_path}")
        
        return model_filename, accuracy
        
    except Exception as e:
        logger.error(f"❌ Company model training error: {e}")
        raise e

def create_features(df):
    """Create enhanced features for better model performance"""
    df = df.copy()
    
    # Basic feature engineering
    if 'experience' in df.columns and 'age' in df.columns:
        df['experience_squared'] = df['experience'] ** 2
        df['age_experience_ratio'] = df['age'] / (df['experience'] + 1)  # +1 to avoid division by zero
    
    # Salary percentiles for potential benchmarking
    if 'salary' in df.columns:
        df['salary_percentile'] = df['salary'].rank(pct=True)
    
    return df

def generate_frontend_options(dataset_analysis):
    """Generate optimized options for frontend form fields"""
    options = {
        "categorical": {},
        "numeric_meta": {},
        "validation_rules": {},
        "field_config": {}
    }
    
    # Generate categorical options
    for col, data in dataset_analysis['categorical_options'].items():
        options["categorical"][col] = data['options']
        
        # Add field configuration
        options["field_config"][col] = {
            "type": "select",
            "required": True,
            "multiple": False,
            "searchable": len(data['options']) > 10,
            "top_suggestions": data.get('top_5', [])[:5]
        }
    
    # Generate numeric metadata with enhanced ranges
    for col, data in dataset_analysis['numeric_ranges'].items():
        if col in ['age', 'experience']:
            options["numeric_meta"][col] = {
                "min": max(0, int(data['min'])),
                "max": min(100, int(data['max'])),
                "step": 1 if col == 'age' else 0.5,
                "suggested_min": int(data['q25']),
                "suggested_max": int(data['q75']),
                "average": int(data['mean']),
                "median": int(data['median'])
            }
            
            # Add validation rules
            options["validation_rules"][col] = {
                "min": max(0, int(data['min'])),
                "max": min(100, int(data['max'])),
                "required": True,
                "type": "number"
            }
    
    # Add field ordering and grouping
    options["field_groups"] = {
        "personal": ["age", "gender", "experience"],
        "professional": ["role", "department", "education"],
        "organizational": ["company", "sector"]
    }
    
    # Add help texts and tooltips
    options["field_descriptions"] = {
        "age": "Employee age in years (18-70)",
        "experience": "Total years of professional experience",
        "gender": "Gender identity",
        "role": "Job title or position",
        "department": "Organizational department",
        "education": "Highest education level",
        "company": "Company type or organization",
        "sector": "Industry sector"
    }
    
    return options

def get_company_options(company_name):
    """Retrieve options for a specific company"""
    try:
        options_path = config.COMPANY_MODELS_FOLDER / f"{company_name.replace(' ', '_').lower()}_options.json"
        if options_path.exists():
            with open(options_path, 'r') as f:
                return json.load(f)
        return None
    except Exception as e:
        logger.error(f"Error loading options for {company_name}: {e}")
        return None