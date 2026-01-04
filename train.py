# train.py - UPDATED VERSION
import os
import json
import numpy as np
import pandas as pd
from pathlib import Path
from joblib import dump
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder, PowerTransformer
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor, StackingRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from packaging import version
import sklearn
import platform

# Check if running on Windows
IS_WINDOWS = platform.system() == 'Windows'

# --- Installation Checks ---
try:
    import xgboost as xgb
    XGB_INSTALLED = True
except ImportError:
    XGB_INSTALLED = False
    print("⚠️  XGBoost not installed. For better performance, run: pip install xgboost")

try:
    import lightgbm as lgb
    LGBM_INSTALLED = True
except ImportError:
    LGBM_INSTALLED = False
    print("⚠️  LightGBM not installed. For better performance, run: pip install lightgbm")

# --- Configuration ---
RANDOM_STATE = 42
DATA_DIR = Path("data")
DATA_PATH = DATA_DIR / "Employee_Salary.csv"
MODELS_DIR = Path("models")

# Required columns for the model - UPDATED to match exactly what we need
REQUIRED_COLUMNS = ['age', 'experience', 'gender', 'role', 'sector', 'company', 'department', 'education', 'salary']

# --- Setup Directories ---
DATA_DIR.mkdir(exist_ok=True)
MODELS_DIR.mkdir(exist_ok=True)

print("--- Starting Enhanced Model Training ---")
print(f"🖥️  Platform: {platform.system()}")

# --- Load Data ---
if not DATA_PATH.exists():
    print(f"❌ Error: Dataset not found at {DATA_PATH}")
    print("Please place your 'Employee_Salary.csv' file in the 'data' directory.")
    exit()

df = pd.read_csv(DATA_PATH)
print("✅ Dataset loaded successfully.")

# --- Check Required Columns ---
missing_columns = set(REQUIRED_COLUMNS) - set(df.columns)
if missing_columns:
    print(f"❌ Missing required columns: {missing_columns}")
    print(f"✅ Available columns: {list(df.columns)}")
    exit()

# --- Enhanced Preprocessing ---
# Keep only required columns
df = df[REQUIRED_COLUMNS].copy()
df = df.drop_duplicates().reset_index(drop=True)

print(f"📊 Dataset shape after cleaning: {df.shape}")

# --- Feature Splitting ---
# Define the core required features
numeric_cols = ['age', 'experience']
categorical_cols = ['gender', 'role', 'sector', 'company', 'department', 'education']

print(f"🔢 Numeric columns: {numeric_cols}")
print(f"🔠 Categorical columns: {categorical_cols}")

# --- Save Options for Frontend ---
# Get actual unique values from the dataset
options = {
    "categorical": {col: sorted(df[col].dropna().astype(str).unique().tolist()) for col in categorical_cols},
    "numeric_meta": {
        col: {
            "min": float(df[col].min()), 
            "max": float(df[col].max()),
            "median": float(df[col].median()), 
            "mean": float(df[col].mean())
        } for col in numeric_cols
    }
}

# Save options to file
with open(MODELS_DIR / "options.json", "w") as f:
    json.dump(options, f, indent=2)

print("✅ Options saved successfully:")
for col in categorical_cols:
    print(f"   {col}: {len(options['categorical'][col])} unique values")

# --- Train-Test Split ---
TARGET = 'salary'
X = df[numeric_cols + categorical_cols]
y = df[TARGET]
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.15, random_state=RANDOM_STATE)

print(f"📈 Training set: {X_train.shape[0]} samples")
print(f"📊 Test set: {X_test.shape[0]} samples")

# --- Enhanced Preprocessing Pipelines ---
ohe_params = {'handle_unknown': "ignore"}
if version.parse(sklearn.__version__) >= version.parse("1.2"):
    ohe_params['sparse_output'] = False
else:
    ohe_params['sparse'] = False

# Numeric transformer
numeric_transformer = Pipeline([
    ("imputer", SimpleImputer(strategy="median")), 
    ("scaler", StandardScaler())
])

categorical_transformer = Pipeline([
    ("imputer", SimpleImputer(strategy="most_frequent")), 
    ("onehot", OneHotEncoder(**ohe_params))
])

preprocessor = ColumnTransformer([
    ("num", numeric_transformer, numeric_cols), 
    ("cat", categorical_transformer, categorical_cols)
], remainder='drop')

# --- Enhanced Model Definitions with Hyperparameter Tuning ---
# For Windows, use n_jobs=1 to avoid multiprocessing issues
n_jobs_value = 1 if IS_WINDOWS else -1

base_models = {
    "RandomForest": RandomForestRegressor(random_state=RANDOM_STATE, n_jobs=n_jobs_value),
    "GradientBoosting": GradientBoostingRegressor(random_state=RANDOM_STATE)
}

if XGB_INSTALLED:
    base_models["XGBoost"] = xgb.XGBRegressor(random_state=RANDOM_STATE, n_jobs=n_jobs_value, eval_metric='rmse')
if LGBM_INSTALLED:
    base_models["LightGBM"] = lgb.LGBMRegressor(random_state=RANDOM_STATE, n_jobs=n_jobs_value)

# Hyperparameter grids for tuning - simplified for Windows compatibility
param_grids = {
    "RandomForest": {
        'regressor__n_estimators': [100, 150],
        'regressor__max_depth': [10, 15]
    },
    "GradientBoosting": {
        'regressor__n_estimators': [100, 150],
        'regressor__learning_rate': [0.05, 0.1]
    }
}

if XGB_INSTALLED:
    param_grids["XGBoost"] = {
        'regressor__n_estimators': [100, 150],
        'regressor__learning_rate': [0.05, 0.1]
    }

if LGBM_INSTALLED:
    param_grids["LightGBM"] = {
        'regressor__n_estimators': [100, 150],
        'regressor__learning_rate': [0.05, 0.1]
    }

# --- Training and Evaluation Loop with Hyperparameter Tuning ---
best_pipelines = {}
scores = {}

print(f"🚀 Training and tuning {len(base_models)} models...")
print("💡 Using single-threaded mode for Windows compatibility")

for name, model in base_models.items():
    print(f"\n--- Training {name} ---")
    pipeline = Pipeline([("preprocessor", preprocessor), ("regressor", model)])
    
    try:
        # Use GridSearchCV for hyperparameter tuning with Windows compatibility
        if name in param_grids:
            grid_search = GridSearchCV(
                pipeline, 
                param_grids[name], 
                cv=2,  # Reduced CV for Windows
                scoring='r2', 
                n_jobs=1,  # Single job for Windows
                verbose=1
            )
            grid_search.fit(X_train, y_train)
            pipeline = grid_search.best_estimator_
            print(f"   Best params: {grid_search.best_params_}")
        else:
            pipeline.fit(X_train, y_train)
        
        y_pred = pipeline.predict(X_test)
        
        r2 = r2_score(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        mae = mean_absolute_error(y_test, y_pred)
        
        # Calculate MAPE safely (avoid division by zero)
        y_test_nonzero = y_test[y_test != 0]
        if len(y_test_nonzero) > 0:
            y_pred_nonzero = y_pred[y_test != 0]
            mape = np.mean(np.abs((y_test_nonzero - y_pred_nonzero) / y_test_nonzero)) * 100
        else:
            mape = 0.0

        best_pipelines[name] = pipeline
        scores[name] = {"r2": r2, "rmse": rmse, "mae": mae, "mape": mape}
        
        print(f"✅ {name} trained successfully! R²: {r2:.4f}")
        print(f"   RMSE: {rmse:,.2f}, MAE: {mae:,.2f}, MAPE: {mape:.2f}%")
        
    except Exception as e:
        print(f"❌ Error training {name}: {e}")
        import traceback
        traceback.print_exc()

if not scores:
    print("⚠️  No models were trained successfully. Trying simple approach...")
    # Fallback: train a simple model without hyperparameter tuning
    try:
        simple_model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            random_state=RANDOM_STATE,
            n_jobs=1
        )
        pipeline = Pipeline([("preprocessor", preprocessor), ("regressor", simple_model)])
        pipeline.fit(X_train, y_train)
        
        y_pred = pipeline.predict(X_test)
        r2 = r2_score(y_test, y_pred)
        
        best_pipelines["RandomForest"] = pipeline
        scores["RandomForest"] = {"r2": r2, "rmse": 0, "mae": 0, "mape": 0}
        print(f"✅ Fallback model trained! R²: {r2:.4f}")
    except Exception as e:
        raise RuntimeError("❌ No models were trained successfully!") from e

# --- Ensemble Model ---
print("\n--- Creating Ensemble Model ---")
try:
    # Use top 2 models for stacking
    if len(scores) >= 2:
        top_models = sorted(scores.items(), key=lambda x: x[1]['r2'], reverse=True)[:2]
        estimators = [(name, best_pipelines[name]) for name, _ in top_models]
        
        ensemble = StackingRegressor(
            estimators=estimators,
            final_estimator=Ridge(alpha=0.1),
            cv=2,  # Reduced CV for Windows
            n_jobs=1  # Single job for Windows
        )
        
        ensemble.fit(X_train, y_train)
        y_pred_ensemble = ensemble.predict(X_test)
        
        r2_ensemble = r2_score(y_test, y_pred_ensemble)
        rmse_ensemble = np.sqrt(mean_squared_error(y_test, y_pred_ensemble))
        mae_ensemble = mean_absolute_error(y_test, y_pred_ensemble)
        
        best_pipelines["Ensemble"] = ensemble
        scores["Ensemble"] = {
            "r2": r2_ensemble, 
            "rmse": rmse_ensemble, 
            "mae": mae_ensemble, 
            "mape": 0.0
        }
        
        print(f"✅ Ensemble model created! R²: {r2_ensemble:.4f}")
    else:
        print("⚠️ Not enough models for ensemble creation")
        
except Exception as e:
    print(f"⚠️ Ensemble creation failed: {e}")
def generate_frontend_options(dataset_analysis):
    """Generate optimized options for frontend form fields based on actual dataset"""
    options = {
        "categorical": {},
        "numeric_meta": {},
        "validation_rules": {},
        "field_descriptions": {}
    }
    
    # Generate categorical options from actual dataset values
    for col, data in dataset_analysis['categorical_options'].items():
        # Use the actual unique values from the dataset
        options["categorical"][col] = data['options']
    
    # Generate numeric metadata with enhanced ranges from actual data
    for col, data in dataset_analysis['numeric_ranges'].items():
        if col in ['age', 'experience']:
            options["numeric_meta"][col] = {
                "min": max(0, int(data['min'])),
                "max": min(100, int(data['max'])),
                "step": 1 if col == 'age' else 0.5,
                "median": int(data['median']),
                "mean": int(data['mean'])
            }
    
    # Enhanced field descriptions based on actual data
    options["field_descriptions"] = {
        "age": f"Age range: {int(dataset_analysis['numeric_ranges']['age']['min'])}-{int(dataset_analysis['numeric_ranges']['age']['max'])} years",
        "experience": f"Experience range: {dataset_analysis['numeric_ranges']['experience']['min']:.1f}-{dataset_analysis['numeric_ranges']['experience']['max']:.1f} years",
        "gender": f"Available options: {', '.join(dataset_analysis['categorical_options']['gender']['options'])}",
        "role": f"Available roles: {len(dataset_analysis['categorical_options']['role']['options'])} options",
        "department": f"Departments: {len(dataset_analysis['categorical_options']['department']['options'])} options",
        "education": f"Education levels: {len(dataset_analysis['categorical_options']['education']['options'])} options",
        "company": f"Company types: {len(dataset_analysis['categorical_options']['company']['options'])} options",
        "sector": f"Industry sectors: {len(dataset_analysis['categorical_options']['sector']['options'])} options"
    }
    
    return options

# --- Best Model Selection ---
best_name = max(scores, key=lambda k: scores[k]["r2"])
best_pipeline = best_pipelines[best_name]
best_score = scores[best_name]['r2']

print(f"\n🏆 Best model: {best_name} (R²: {best_score:.4f})")

# --- Final Cross-Validation ---
print("🔍 Performing final cross-validation on the best model...")
try:
    cv_scores = cross_val_score(best_pipeline, X, y, cv=3, scoring='r2', n_jobs=1)  # Reduced CV and single job
    cv_mean, cv_std = float(cv_scores.mean()), float(cv_scores.std())
    print(f"   Cross-validation R²: {cv_mean:.4f} (± {cv_std:.4f})")
except Exception as e:
    print(f"⚠️ Cross-validation failed: {e}")
    cv_mean, cv_std = best_score, 0.0

# --- Save Artifacts ---
dump(best_pipeline, MODELS_DIR / "model_pipeline.pkl")
metadata = {
    "numeric_cols": numeric_cols,
    "categorical_cols": categorical_cols,
    "model_name": best_name,
    "cv_score": cv_mean,
    "model_comparison": scores,
    "all_models": list(scores.keys()),
    "required_columns": REQUIRED_COLUMNS[:-1]  # Exclude salary
}
with open(MODELS_DIR / "metadata.json", "w") as f:
    json.dump(metadata, f, indent=2)

print("\n✅ Saved best model pipeline to: models/model_pipeline.pkl")
print("✅ Saved options and metadata.")
print(f"✅ Required prediction fields: {REQUIRED_COLUMNS[:-1]}")
print("\n🎉 Enhanced training complete!")