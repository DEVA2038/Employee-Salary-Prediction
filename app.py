# app.py - FINAL CORRECTED VERSION
# update test - force commit
from flask import Flask, request, jsonify, send_from_directory, render_template, session, redirect, url_for, send_file
from joblib import load
import pandas as pd
import numpy as np
import json
from pathlib import Path
import os
# Add these with your other imports
from dataset_validator import DatasetValidator
from dataset_history import dataset_manager
from automation_system import AutomationSystem, AutomationMode
from database import get_db, CompanyRequest, CompanyUser, AdminUser  # Added AdminUser
from sqlalchemy.orm import Session
import secrets
import string
import config
from datetime import datetime, timedelta, timezone
import train_company
import logging
from functools import wraps
from apscheduler.schedulers.background import BackgroundScheduler
import pytz
import atexit
import smtplib
import ssl
from email.message import EmailMessage

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration ---
MODELS_DIR = Path("models")
MODEL_PATH = MODELS_DIR / "model_pipeline.pkl"
OPTIONS_PATH = MODELS_DIR / "options.json"
METADATA_PATH = MODELS_DIR / "metadata.json"

# Initialize Flask App
app = Flask(__name__,
            static_folder='static',
            static_url_path='/static',
            template_folder='templates')
# Global Automation Settings
AUTOMATION_SETTINGS = {
    "mode": "manual"
}
# Enhanced session configuration
app.secret_key = 'your-secret-key-here-change-in-production-12345'
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
app.config['UPLOAD_FOLDER'] = config.UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create necessary directories
config.UPLOAD_FOLDER.mkdir(exist_ok=True)
config.COMPANY_MODELS_FOLDER.mkdir(exist_ok=True)

# --- Admin Credentials ---
ADMIN_CREDENTIALS = {
    "username": "Deva1234",
    "password": "Deva2005@"
}

def verify_admin_password(input_password, stored_password):
    """Verify admin password"""
    return input_password == stored_password

# --- Helper Functions ---
def company_login_required(f):
    """Decorator to require company login for specific routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_company_logged_in():
            return jsonify({"error": "Please login first"}), 401
        return f(*args, **kwargs)
    return decorated_function

def admin_login_required(f):
    """Decorator to require admin login for specific routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_admin_logged_in():
            return jsonify({"error": "Admin authentication required"}), 401
        return f(*args, **kwargs)
    return decorated_function

def is_company_logged_in():
    """Check if company is logged in with session validation"""
    if not session.get('company_logged_in'):
        return False

    # Verify session data exists in database
    try:
        db: Session = next(get_db())
        user = db.query(CompanyUser).filter(
            CompanyUser.id == session.get('company_id'),
            CompanyUser.is_active == True
        ).first()

        if not user:
            session.clear()
            return False

        # Update session with fresh data
        session['company_name'] = user.company_name
        session['company_username'] = user.username

        # Get company request data
        company_request = db.query(CompanyRequest).filter(
            CompanyRequest.username == user.username
        ).first()

        if company_request:
            session['company_request_id'] = company_request.id
            session['model_accuracy'] = company_request.model_accuracy

        # Update session lifetime
        session.permanent = True
        app.permanent_session_lifetime = timedelta(hours=24)
        return True
    except Exception as e:
        logger.error(f"Session validation error: {e}")
        session.clear()
        return False

def is_admin_logged_in():
    """Check if admin is logged in and session is still valid"""
    if not session.get('admin_logged_in'):
        return False
    
    # Check if session has expired (24 hours)
    login_time_str = session.get('admin_login_time')
    if login_time_str:
        try:
            login_time = datetime.fromisoformat(login_time_str)
            current_time = datetime.now(timezone.utc)
            time_diff = current_time - login_time
            
            # If more than 24 hours have passed, logout
            if time_diff.total_seconds() > 24 * 3600:  # 24 hours in seconds
                session.clear()
                logger.info("🕒 Admin session expired after 24 hours")
                return False
        except Exception as e:
            logger.warning(f"Error checking session time: {e}")
    
    return True

def generate_password(length=12):
    characters = string.ascii_letters + string.digits + "!@#$%"
    return ''.join(secrets.choice(characters) for _ in range(length))

def validate_dataset(file_path):
    try:
        df = pd.read_csv(file_path)
        missing_columns = set(config.REQUIRED_COLUMNS) - set(df.columns)
        if missing_columns:
            return False, f"Missing columns: {', '.join(missing_columns)}"
        return True, "Dataset is valid"
    except Exception as e:
        return False, f"Error reading dataset: {str(e)}"

def load_company_model(company_id):
    try:
        db: Session = next(get_db())
        company_request = db.query(CompanyRequest).filter(CompanyRequest.id == company_id).first()

        if not company_request or not company_request.model_filename:
            return None, "Model not found"

        model_path = config.COMPANY_MODELS_FOLDER / company_request.model_filename
        if not model_path.exists():
            return None, "Model file not found"

        company_model = load(model_path)
        return company_model, "Success"
    except Exception as e:
        return None, f"Error loading model: {str(e)}"

def get_enhanced_default_options():
    """Enhanced default options with comprehensive data"""
    return {
        "categorical": {
            "gender": ["Male", "Female", "Other", "Prefer not to say"],
            "role": [
                "Software Engineer", "Data Scientist", "Product Manager", "HR Manager",
                "Sales Executive", "Marketing Manager", "Finance Analyst", "Operations Manager",
                "Project Manager", "Business Analyst", "UX Designer", "DevOps Engineer"
            ],
            "sector": [
                "IT & Technology", "Finance & Banking", "Healthcare", "Education",
                "Manufacturing", "Retail & E-commerce", "Consulting", "Real Estate",
                "Hospitality", "Transportation", "Energy", "Media & Entertainment"
            ],
            "company": [
                "Private Limited", "Public Limited", "Startup", "Multinational Corporation",
                "Government", "Non-Profit", "Partnership", "Sole Proprietorship"
            ],
            "department": [
                "Engineering", "Sales", "Marketing", "Human Resources", "Finance",
                "Operations", "Research & Development", "Customer Support",
                "IT Support", "Quality Assurance", "Product Development", "Administration"
            ],
            "education": [
                "High School", "Diploma", "Associate's Degree", "Bachelor's Degree",
                "Master's Degree", "PhD", "Professional Certification", "Vocational Training"
            ]
        },
        "numeric_meta": {
            "age": {"min": 18, "max": 65, "step": 1, "median": 32, "average": 35},
            "experience": {"min": 0, "max": 40, "step": 0.5, "median": 5.5, "average": 7.2}
        },
        "field_descriptions": {
            "age": "Employee age in years (18-65)",
            "experience": "Total years of professional experience",
            "gender": "Gender identity",
            "role": "Job title or position",
            "department": "Organizational department",
            "education": "Highest education level",
            "company": "Company type",
            "sector": "Industry sector"
        },
        "field_config": {
            "gender": {"type": "select", "required": True, "searchable": False},
            "role": {"type": "select", "required": True, "searchable": True},
            "sector": {"type": "select", "required": True, "searchable": True},
            "company": {"type": "select", "required": True, "searchable": False},
            "department": {"type": "select", "required": True, "searchable": True},
            "education": {"type": "select", "required": True, "searchable": False}
        },
        "dataset_stats": {
            "total_records": 0,
            "categorical_counts": {
                "gender": 4, "role": 12, "sector": 12,
                "company": 8, "department": 12, "education": 8
            },
            "completeness": "Using Default Options"
        }
    }

# -------------------------
# NEW: Real email-sending helpers
# -------------------------
def _send_email(subject: str, body: str, to_emails: list, attachments: list = None, cc: list = None) -> bool:
    """
    Send an email using settings from config.EMAIL_CONFIG.
    - to_emails: list of recipient email addresses
    - attachments: list of file paths to attach (optional)
    - cc: list of cc addresses (optional)
    Returns True on success, False on failure.
    """
    email_cfg = config.EMAIL_CONFIG
    sender = email_cfg.get('SENDER_EMAIL', '') or ''
    password = email_cfg.get('SENDER_PASSWORD', '') or ''
    smtp_server = email_cfg.get('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = email_cfg.get('SMTP_PORT', 587)

    if not sender or not password:
        logger.warning("Email sending is disabled because SENDER_EMAIL or SENDER_PASSWORD is not configured.")
        # Fallback: print to console
        logger.info("---- EMAIL (fallback to console) ----")
        logger.info(f"From: {sender}")
        logger.info(f"To: {to_emails}")
        if cc:
            logger.info(f"CC: {cc}")
        logger.info(f"Subject: {subject}")
        logger.info(body)
        if attachments:
            logger.info(f"Attachments: {attachments}")
        logger.info("---- END EMAIL ----")
        return False

    try:
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = sender
        msg['To'] = ", ".join(to_emails)
        if cc:
            msg['Cc'] = ", ".join(cc)
        msg.set_content(body)

        # Attach files if provided
        if attachments:
            for fpath in attachments:
                try:
                    fpath = Path(fpath)
                    if not fpath.exists():
                        continue
                    with open(fpath, 'rb') as f:
                        data = f.read()
                    maintype = 'application'
                    subtype = 'octet-stream'
                    msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=fpath.name)
                except Exception as e:
                    logger.warning(f"Could not attach {fpath}: {e}")

        context = ssl.create_default_context()

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(sender, password)
            server.send_message(msg)

        logger.info(f"Email sent: subject='{subject}' to={to_emails} cc={cc}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False

def send_admin_notification(company_request, db):
    """
    Notify admin that a new company request was created.
    Attaches the uploaded dataset (if present).
    """
    try:
        admin_email = config.EMAIL_CONFIG.get('ADMIN_EMAIL') or config.EMAIL_CONFIG.get('SENDER_EMAIL')
        subject = f"[New Company Request] {company_request.company_name}"
        body = (
            f"A new company request has been submitted.\n\n"
            f"Company: {company_request.company_name}\n"
            f"Contact person: {company_request.contact_person}\n"
            f"Email: {company_request.email}\n"
            f"Phone: {company_request.phone}\n"
            f"Dataset file: {company_request.dataset_filename}\n"
            f"Request ID: {company_request.id}\n"
            f"Submitted at: {company_request.created_at.isoformat() if company_request.created_at else 'N/A'}\n\n"
            f"Visit the admin panel to review and approve or reject the request."
        )

        attachments = []
        try:
            if company_request.dataset_filename:
                dataset_path = config.UPLOAD_FOLDER / company_request.dataset_filename
                if dataset_path.exists():
                    attachments.append(str(dataset_path))
        except Exception as e:
            logger.debug(f"Could not find dataset to attach: {e}")

        # If email is disabled, this will fallback to console logging and return False.
        success = _send_email(subject, body, to_emails=[admin_email], attachments=attachments)
        return success
    except Exception as e:
        logger.error(f"send_admin_notification error: {e}")
        return False

def send_company_credentials(company_request, username, password):
    """
    Send approval email with login credentials ONLY to the company's contact email.
    No CC to admin.
    """
    try:
        subject = f"Your company account has been approved - {company_request.company_name}"
        login_url = "http://localhost:5000/company-login"
        body = (
            f"Hello {company_request.contact_person},\n\n"
            f"Your company request has been approved. Here are your credentials:\n\n"
            f"Company: {company_request.company_name}\n"
            f"Username: {username}\n"
            f"Password: {password}\n\n"
            f"Login here: {login_url}\n\n"
            f"Please change your password after your first login.\n\n"
            f"Best regards,\n"
            f"Admin Team"
        )

        # --- ensure a valid recipient email ---
        company_email = (company_request.email or "").strip()
        if not company_email:
            logger.warning("⚠️ Company email missing — credentials not sent.")
            return False

        # Send email directly to company (no CC)
        success = _send_email(subject, body, to_emails=[company_email])
        if success:
            logger.info(f"📧 Credentials sent to company: {company_email}")
        else:
            logger.warning(f"⚠️ Failed to send credentials to {company_email}")

        return success

    except Exception as e:
        logger.error(f"send_company_credentials error: {e}")
        return False

# --- Load Artifacts ---
# --- Load Artifacts ---
try:
    # Attempt to load the model
    model = load(MODEL_PATH)
    
    with open(OPTIONS_PATH, "r") as f:
        options = json.load(f)
    with open(METADATA_PATH, "r") as f:
        metadata = json.load(f)
        
    print("✅ Model and metadata loaded successfully.")
    print(f"📊 Model expects {len(metadata.get('numeric_cols', []))} numeric and {len(metadata.get('categorical_cols', []))} categorical features")

except (FileNotFoundError, Exception) as e:
    # Catching generic Exception handles the KeyError: 118 (corruption)
    print(f"❌ Error loading model artifacts: {e}")
    print("⚠️  The system will start in LIMITED mode. Please run 'python train.py' to generate/fix the model.")
    
    # Create dummy data to prevent crashes so the server still runs
    options = {"categorical": {}, "numeric_meta": {}}
    metadata = {"numeric_cols": [], "categorical_cols": [], "model_name": "Demo"}
    model = None

# ---------------------------
# NEW: Helper to prepare input
# ---------------------------
def prepare_input_for_model(input_df, model_obj=None, metadata_obj=None):
    """
    Ensure input_df contains all columns the model expects.
    - If model_obj has .feature_names_in_, use that.
    - Else, try to use metadata_obj['feature_names'] (if available).
    - For missing features:
        * If derivable (experience_squared, age_experience_ratio), compute them.
        * Else fill with median from metadata if available, else 0.
    - Reorder columns to match expected order.
    Returns the prepared DataFrame.
    """
    df = input_df.copy()

    # Determine expected features
    expected = None
    if model_obj is not None:
        # sklearn estimators or pipelines often expose feature_names_in_
        expected = getattr(model_obj, "feature_names_in_", None)
        if expected is not None:
            expected = list(expected)

    if expected is None and metadata_obj is not None:
        # metadata may contain numeric_cols + categorical_cols or a combined list
        if "feature_names" in metadata_obj:
            expected = list(metadata_obj["feature_names"])
        else:
            expected = list(metadata_obj.get("numeric_cols", [])) + list(metadata_obj.get("categorical_cols", []))

    # If still not available, just use columns present in df
    if expected is None:
        expected = list(df.columns)

    expected = [str(x) for x in expected]

    # Known derivable features mapping
    # If your training pipeline created other engineered features, add them here with generator funcs
    def derive_experience_squared(row):
        try:
            return float(row.get("experience", 0)) ** 2
        except Exception:
            return 0.0

    def derive_age_experience_ratio(row):
        try:
            exp = float(row.get("experience", 0))
            age = float(row.get("age", 0))
            return age / (exp + 1.0)  # +1 to avoid divide-by-zero
        except Exception:
            return 0.0

    # Compute derivable columns if missing
    derivable_map = {
        "experience_squared": derive_experience_squared,
        "age_experience_ratio": derive_age_experience_ratio
    }

    missing = [col for col in expected if col not in df.columns]

    # If columns are missing but derivable, compute them
    for col in list(missing):
        if col in derivable_map:
            df[col] = df.apply(lambda r: derivable_map[col](r), axis=1)
            missing.remove(col)

    # For any remaining missing columns, fill with median from metadata (if present) or 0
    for col in missing:
        fill_value = 0
        # try metadata numeric medians
        if metadata_obj:
            # metadata may contain numeric_meta with medians
            numeric_meta = metadata_obj.get("numeric_meta", {})
            if col in numeric_meta and isinstance(numeric_meta[col].get("median", None), (int, float)):
                fill_value = float(numeric_meta[col]["median"])
            else:
                # also check top-level medians or defaults
                default_median = metadata_obj.get("medians", {}).get(col)
                if default_median is not None:
                    try:
                        fill_value = float(default_median)
                    except Exception:
                        fill_value = 0
        df[col] = fill_value

    # Ensure column order matches expected
    # Some models expect exactly the same ordering
    ordered_cols = [c for c in expected if c in df.columns]
    df = df[ordered_cols]

    return df

# --- Routes ---
@app.route('/')
def index():
    """Serve the main application"""
    try:
        return render_template('index.html')
    except Exception as e:
        return f"Error loading template: {e}", 500

@app.route('/company-request')
def company_request_page():
    return render_template('company_request.html')

@app.route('/company-login')
def company_login_page():
    # If already logged in, redirect to dashboard
    if is_company_logged_in():
        return redirect(url_for('company_dashboard_page'))
    return render_template('company_login.html')

@app.route('/company-dashboard')
def company_dashboard_page():
    if not is_company_logged_in():
        return redirect(url_for('company_login_page'))
    return render_template('company_dashboard.html')

@app.route('/admin-login')
def admin_login_page():
    if is_admin_logged_in():
        return redirect(url_for('admin_panel_page'))
    return render_template('admin_login.html')

@app.route('/admin-panel')
def admin_panel_page():
    if not is_admin_logged_in():
        return redirect(url_for('admin_login_page'))
    return render_template('admin_panel.html')

@app.route('/company-logout')
def company_logout():
    session.clear()
    return redirect(url_for('company_login_page'))

@app.route('/api/session/check')
def check_session():
    """API endpoint to check session status"""
    if is_company_logged_in():
        return jsonify({
            "logged_in": True,
            "company_name": session.get('company_name'),
            "username": session.get('company_username')
        })
    else:
        return jsonify({"logged_in": False})

# --- Admin Authentication Routes ---
@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({"error": "Username and password required"}), 400

        # Verify admin credentials
        if (username == ADMIN_CREDENTIALS["username"] and 
            verify_admin_password(password, ADMIN_CREDENTIALS["password"])):
            
            # Set admin session with 24-hour expiration
            session.clear()
            session.permanent = True
            app.permanent_session_lifetime = timedelta(hours=24)
            session['admin_logged_in'] = True
            session['admin_username'] = username
            session['admin_login_time'] = datetime.now(timezone.utc).isoformat()
            
            logger.info(f"✅ Admin {username} logged in successfully. Session valid for 24 hours.")
            
            return jsonify({
                "message": "Admin login successful - Session valid for 24 hours",
                "username": username,
                "session_duration": "24 hours"
            })
        else:
            return jsonify({"error": "Invalid admin credentials"}), 401

    except Exception as e:
        logger.error(f"❌ Admin login error: {e}")
        return jsonify({"error": f"Login error: {str(e)}"}), 500

@app.route('/api/admin/logout', methods=['POST'])
def admin_logout():
    session.clear()
    return jsonify({"message": "Admin logged out successfully"})

@app.route('/api/admin/session')
def check_admin_session():
    """Check if admin is logged in and return session info"""
    if is_admin_logged_in():
        login_time_str = session.get('admin_login_time')
        login_time = datetime.fromisoformat(login_time_str) if login_time_str else None
        current_time = datetime.now(timezone.utc)
        
        if login_time:
            time_diff = current_time - login_time
            hours_remaining = max(0, 24 - (time_diff.total_seconds() / 3600))
            
            return jsonify({
                "logged_in": True,
                "username": session.get('admin_username'),
                "login_time": login_time_str,
                "hours_remaining": round(hours_remaining, 2),
                "session_duration": "24 hours"
            })
        else:
            return jsonify({
                "logged_in": True,
                "username": session.get('admin_username'),
                "session_duration": "24 hours"
            })
    else:
        return jsonify({"logged_in": False})

# --- API Routes ---
@app.route('/api/company/request', methods=['POST'])
def submit_company_request():
    try:
        company_name = request.form.get('company_name')
        contact_person = request.form.get('contact_person')
        email = request.form.get('email')
        phone = request.form.get('phone')
        
        if not all([company_name, contact_person, email]):
            return jsonify({"error": "All fields are required"}), 400

        if 'dataset' not in request.files:
            return jsonify({"error": "Dataset file is required"}), 400

        file = request.files['dataset']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400

        if not file.filename.lower().endswith('.csv'):
            return jsonify({"error": "Only CSV files are allowed"}), 400

        filename = f"{company_name.replace(' ', '_')}_{secrets.token_hex(8)}.csv"
        file_path = config.UPLOAD_FOLDER / filename
        file.save(file_path)
        
        # --- VALIDATOR ADDITION START ---
        # 1. Validate Columns
        valid, msg, mapping = DatasetValidator.validate_required_columns(file_path)
        if not valid:
            file_path.unlink() # Delete invalid file
            return jsonify({"error": msg}), 400
        
        # 2. Check Data Quality
        quality_ok, quality_msg = DatasetValidator.check_data_quality(file_path, mapping)
        if not quality_ok:
            file_path.unlink()
            return jsonify({"error": f"Data Quality: {quality_msg}"}), 400
        # 3. Standardize Headers
        try:
            clean_df = DatasetValidator.prepare_mapped_dataset(file_path, mapping)
            clean_df.to_csv(file_path, index=False)
        except Exception as e:
            file_path.unlink()
            return jsonify({"error": f"Dataset processing error: {e}"}), 500
        
        is_valid, message = validate_dataset(file_path)
        if not is_valid:
            file_path.unlink(missing_ok=True)
            return jsonify({"error": message}), 400

        db: Session = next(get_db())
        company_request = CompanyRequest(
            company_name=company_name,
            contact_person=contact_person,
            email=email,
            phone=phone,
            dataset_filename=filename,
            status="pending"
        )
        db.add(company_request)
        db.commit()
        db.refresh(company_request)

        send_admin_notification(company_request, db)

        return jsonify({
            "message": "Request submitted successfully! We'll review your request and contact you soon.",
            "request_id": company_request.id
        })

    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route('/api/company/login', methods=['POST'])
def company_login():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({"error": "Username and password required"}), 400

        db: Session = next(get_db())
        user = db.query(CompanyUser).filter(
            CompanyUser.username == username,
            CompanyUser.is_active == True
        ).first()

        if user and user.password == password:
            # Clear any existing session
            session.clear()

            # Set session data
            session.permanent = True
            session['company_logged_in'] = True
            session['company_id'] = user.id
            session['company_name'] = user.company_name
            session['company_username'] = user.username

            # Get company request data
            company_request = db.query(CompanyRequest).filter(
                CompanyRequest.username == username
            ).first()

            if company_request:
                session['company_request_id'] = company_request.id
                session['model_accuracy'] = company_request.model_accuracy

            # --- NEW: Track unique login days ---
            today = datetime.now(timezone.utc).date()
            login_days = []
            try:
                if getattr(user, "login_days", None):
                    login_days = json.loads(user.login_days)
            except Exception:
                login_days = []

            if str(today) not in login_days:
                login_days.append(str(today))

            user.login_days = json.dumps(login_days)
            user.last_login_date = datetime.now(timezone.utc)
            db.commit()

            logger.info(f"✅ User {username} logged in successfully.")

            return jsonify({
                "message": "Login successful",
                "company_name": user.company_name,
                "username": user.username
            })
        else:
            return jsonify({"error": "Invalid credentials"}), 401

    except Exception as e:
        logger.error(f"❌ Login error: {e}")
        return jsonify({"error": f"Login error: {str(e)}"}), 500
    
# FIXED: Company Options Endpoint (unchanged from earlier robust version)
@app.route('/api/company/options')
@company_login_required
def get_company_options():
    """Get company-specific form options from their dataset"""
    try:
        company_name = session.get('company_name')
        if not company_name:
            return jsonify({'error': 'Company not found in session'}), 401

        # Load company-specific options
        options_filename = f"{company_name.replace(' ', '_').lower()}_options.json"
        options_path = config.COMPANY_MODELS_FOLDER / options_filename

        logger.info(f"🔍 Looking for options file: {options_path}")

        if options_path.exists():
            with open(options_path, 'r') as f:
                options_data = json.load(f)
            logger.info(f"✅ Loaded company-specific options for {company_name}")
            return jsonify(options_data)
        else:
            # Try to extract from dataset if present
            db: Session = next(get_db())
            company_request = db.query(CompanyRequest).filter(CompanyRequest.company_name == company_name).first()
            if company_request:
                dataset_path = config.UPLOAD_FOLDER / company_request.dataset_filename
                if dataset_path.exists():
                    try:
                        df = pd.read_csv(dataset_path)
                        categorical_columns = ["gender", "role", "sector", "company", "department", "education"]
                        options_data = {"categorical": {}, "numeric_meta": {}, "field_descriptions": {}}
                        for col in categorical_columns:
                            if col in df.columns:
                                options_data["categorical"][col] = sorted([str(v).strip() for v in df[col].dropna().unique() if str(v).strip() != ""])
                        # numeric meta
                        for col in ["age", "experience"]:
                            if col in df.columns:
                                options_data["numeric_meta"][col] = {
                                    "min": float(df[col].min()),
                                    "max": float(df[col].max()),
                                    "step": 1,
                                    "median": float(df[col].median()),
                                    "average": float(df[col].mean())
                                }
                        options_data["field_descriptions"] = get_enhanced_default_options().get("field_descriptions", {})
                        # cache
                        with open(options_path, 'w') as f:
                            json.dump(options_data, f, indent=4)
                        logger.info(f"✅ Auto-generated and saved company options for {company_name}")
                        return jsonify(options_data)
                    except Exception as e:
                        logger.error(f"Error extracting options from dataset: {e}")
                        return jsonify(get_enhanced_default_options())
            # fallback
            logger.warning(f"⚠️ Options file not found for {company_name}, using defaults")
            default_options = get_enhanced_default_options()
            return jsonify(default_options)

    except Exception as e:
        logger.error(f"❌ Error loading company options: {e}")
        import traceback
        traceback.print_exc()
        # Return defaults instead of error
        default_options = get_enhanced_default_options()
        return jsonify(default_options)

# --- AUTOMATION API ROUTES ---

@app.route('/api/admin/automation/settings', methods=['GET', 'POST'])
@admin_login_required
def automation_settings():
    """Get or set the current automation mode (Manual/Automated)"""
    if request.method == 'POST':
        data = request.get_json()
        mode = data.get('mode')
        if mode in ['manual', 'automated']:  # String values
            AUTOMATION_SETTINGS['mode'] = mode
            return jsonify({"message": "Settings updated", "mode": mode})
        return jsonify({"error": "Invalid mode"}), 400
    
    # Return mode as string
    return jsonify({"mode": AUTOMATION_SETTINGS['mode']})
# In app.py, update the get_inactive_accounts function
@app.route('/api/admin/inactive-accounts')
@admin_login_required
def get_inactive_accounts():
    """Get list of inactive accounts for the admin dashboard"""
    try:
        db: Session = next(get_db())
        
        # Get all active company users
        users = db.query(CompanyUser).filter(
            CompanyUser.is_active == True
        ).all()
        
        inactive_accounts = []
        current_time = datetime.now(timezone.utc)
        
        for user in users:
            try:
                # Find the corresponding company request
                company_request = db.query(CompanyRequest).filter(
                    CompanyRequest.username == user.username
                ).first()
                
                if not company_request:
                    logger.warning(f"No company request found for user: {user.username}")
                    continue
                
                # Calculate days inactive with proper timezone handling
                days_inactive = 0
                if user.last_login_date:
                    # Ensure both datetimes are timezone-aware
                    last_login = user.last_login_date
                    if last_login.tzinfo is None:
                        last_login = last_login.replace(tzinfo=timezone.utc)
                    
                    # Now both are timezone-aware
                    days_inactive = (current_time - last_login).days
                else:
                    # If never logged in, use created date
                    if user.created_at:
                        created = user.created_at
                        if created.tzinfo is None:
                            created = created.replace(tzinfo=timezone.utc)
                        days_inactive = (current_time - created).days
                    else:
                        days_inactive = 999
                
                # Only include if inactive for more than 14 days
                if days_inactive > 14:
                    # Determine status
                    if days_inactive > 90:
                        status = "critical"
                    elif days_inactive > 60:
                        status = "warning_3"
                    elif days_inactive > 30:
                        status = "warning_2"
                    elif days_inactive > 14:
                        status = "warning_1"
                    else:
                        status = "active"
                    
                    inactive_accounts.append({
                        "user_id": user.id,
                        "company_name": company_request.company_name,
                        "email": company_request.email or user.email,
                        "days_inactive": days_inactive,
                        "status": status,
                        "last_login_date": user.last_login_date.isoformat() if user.last_login_date else None,
                        "company_request_id": company_request.id
                    })
                    
            except Exception as user_error:
                logger.error(f"Error processing user {user.id}: {user_error}")
                continue
        
        logger.info(f"Found {len(inactive_accounts)} inactive accounts")
        return jsonify({"accounts": inactive_accounts})
        
    except Exception as e:
        logger.error(f"Error in get_inactive_accounts: {e}", exc_info=True)
        return jsonify({
            "error": "Failed to load inactive accounts",
            "details": str(e),
            "accounts": []
        }), 500
@app.route('/api/admin/debug/db-check')
@admin_login_required
def debug_db_check():
    """Debug endpoint to check database structure"""
    try:
        db: Session = next(get_db())
        
        # Check CompanyUser table
        users = db.query(CompanyUser).all()
        user_info = []
        for user in users:
            user_info.append({
                "id": user.id,
                "username": user.username,
                "company_name": user.company_name,
                "last_login_date": str(user.last_login_date) if user.last_login_date else None,
                "created_at": str(user.created_at) if user.created_at else None,
                "is_active": user.is_active
            })
        
        # Check CompanyRequest table
        requests = db.query(CompanyRequest).all()
        request_info = []
        for req in requests:
            request_info.append({
                "id": req.id,
                "company_name": req.company_name,
                "username": req.username,
                "status": req.status,
                "approved_at": str(req.approved_at) if req.approved_at else None
            })
        
        return jsonify({
            "company_users_count": len(users),
            "company_users": user_info[:5],  # First 5 only
            "company_requests_count": len(requests),
            "company_requests": request_info[:5]
        })
        
    except Exception as e:
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500
@app.route('/api/admin/debug/inactive')
@admin_login_required
def debug_inactive_accounts():
    """Debug endpoint to check inactive accounts data"""
    try:
        db: Session = next(get_db())
        
        # Get all company users
        users = db.query(CompanyUser).all()
        user_data = []
        
        for user in users:
            company_request = db.query(CompanyRequest).filter(
                CompanyRequest.username == user.username
            ).first()
            
            days_inactive = 0
            if user.last_login_date:
                last_login = user.last_login_date
                if last_login.tzinfo is None:
                    last_login = last_login.replace(tzinfo=timezone.utc)
                current_time = datetime.now(timezone.utc)
                days_inactive = (current_time - last_login).days
            
            user_data.append({
                "id": user.id,
                "username": user.username,
                "company_name": user.company_name,
                "last_login_date": user.last_login_date.isoformat() if user.last_login_date else None,
                "days_inactive": days_inactive,
                "company_request_exists": company_request is not None,
                "company_request_company": company_request.company_name if company_request else None
            })
        
        return jsonify({
            "total_users": len(users),
            "users": user_data
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route('/api/admin/low-accuracy-accounts')
@admin_login_required
def get_low_accuracy_accounts():
    """Get list of accounts with low model accuracy"""
    try:
        db: Session = next(get_db())
        system = AutomationSystem(db, email_sender=_send_email, mode=AutomationMode.MANUAL)
        accounts = system.get_low_accuracy_accounts()
        return jsonify({"accounts": accounts})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/automation/run', methods=['POST'])
@admin_login_required
def run_automation():
    """Manually trigger the automation logic (check all accounts now)"""
    try:
        db: Session = next(get_db())
        mode = AUTOMATION_SETTINGS.get('mode', 'manual')  # Get as string
        
        # Initialize System with Email Sender
        system = AutomationSystem(db, email_sender=_send_email, mode=mode)
        results = system.run_automation()
        
        response = {
            "results": {
                "inactive_accounts_found": len(system.get_inactive_accounts()),
                "low_accuracy_accounts_found": len(system.get_low_accuracy_accounts()),
                "processed_actions": results,
                "mode": results.get('mode', mode)  # Use mode from results
            }
        }
        
        # Check if mode is manual
        if mode == 'manual':
            response["note"] = "MANUAL mode active. No automatic actions were taken."
            
        return jsonify(response)
    except Exception as e:
        logger.error(f"Automation run error: {e}")
        return jsonify({"error": str(e)}), 500

# Example for one endpoint - update all three similarly
@app.route('/api/admin/manual/warn-inactive/<int:user_id>', methods=['POST'])
@admin_login_required
def manual_warn_inactive(user_id):
    """Manually send an inactivity warning email"""
    try:
        db: Session = next(get_db())
        # Pass string mode instead of enum
        system = AutomationSystem(db, email_sender=_send_email, mode='manual')
        
        user = db.query(CompanyUser).filter(CompanyUser.id == user_id).first()
        if not user: return jsonify({"error": "User not found"}), 404
        
        company_request = db.query(CompanyRequest).filter(CompanyRequest.username == user.username).first()
        
        # Calculate days inactive
        days = 0
        if user.last_login_date:
            current_time = datetime.now(timezone.utc)
            last_login = user.last_login_date
            if last_login.tzinfo is None:
                last_login = last_login.replace(tzinfo=timezone.utc)
            days = (current_time - last_login).days
        
        # Get status
        status = "warning_1"
        if days > 90:
            status = "critical"
        elif days > 60:
            status = "warning_3"
        elif days > 30:
            status = "warning_2"
        elif days > 14:
            status = "warning_1"
        
        success = system.send_inactivity_warning(user, company_request, status, days)
        if success:
            return jsonify({"message": "Warning email sent successfully"})
        return jsonify({"error": "Failed to send email"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/manual/warn-low-accuracy/<int:request_id>', methods=['POST'])
@admin_login_required
def manual_warn_accuracy(request_id):
    """Manually send a low accuracy warning email"""
    try:
        db: Session = next(get_db())
        system = AutomationSystem(db, email_sender=_send_email, mode=AutomationMode.MANUAL)
        
        req = db.query(CompanyRequest).filter(CompanyRequest.id == request_id).first()
        if not req: return jsonify({"error": "Request not found"}), 404
        
        user = db.query(CompanyUser).filter(CompanyUser.username == req.username).first()
        if not user: return jsonify({"error": "Linked user not found"}), 404

        success = system.send_low_accuracy_warning(user, req, float(req.model_accuracy))
        if success:
            return jsonify({"message": "Low accuracy warning sent"})
        return jsonify({"error": "Failed to send email"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/manual/delete-account/<int:user_id>', methods=['POST'])
@admin_login_required
def manual_delete_account(user_id):
    """Manually delete an account (via Automation logic)"""
    try:
        db: Session = next(get_db())
        system = AutomationSystem(db, email_sender=_send_email, mode=AutomationMode.MANUAL)
        
        user = db.query(CompanyUser).filter(CompanyUser.id == user_id).first()
        if not user: return jsonify({"error": "User not found"}), 404
        
        company_request = db.query(CompanyRequest).filter(CompanyRequest.username == user.username).first()
        company_name = user.company_name
        
        success = system.delete_inactive_account(user, company_request)
        if success:
            return jsonify({"message": f"Account {company_name} deleted successfully"})
        return jsonify({"error": "Deletion failed"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- DATASET HISTORY ROUTES ---

@app.route('/api/company/datasets')
@company_login_required
def get_company_datasets_history_route():
    """Get the history of all uploaded datasets for the logged-in company"""
    try:
        # Uses DatasetHistoryManager imported from dataset_history.py
        datasets = dataset_manager.get_company_datasets(session.get('company_name'))
        
        # Serialize datetime objects for JSON
        for d in datasets:
            if isinstance(d['upload_date'], datetime):
                d['upload_date'] = d['upload_date'].isoformat()
        return jsonify(datasets)
    except Exception as e:
        logger.error(f"Error fetching dataset history: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/company/datasets/download/<dataset_id>')
@company_login_required
def download_company_dataset_route(dataset_id):
    """Download a specific historical dataset"""
    try:
        path = dataset_manager.download_dataset(session.get('company_name'), dataset_id)
        if path and path.exists():
            return send_file(path, as_attachment=True, download_name=path.name, mimetype='text/csv')
        return jsonify({"error": "File not found"}), 404
    except Exception as e:
        logger.error(f"Error downloading dataset: {e}")
        return jsonify({"error": "Download error"}), 500

@app.route('/api/company/predict', methods=['POST'])
@company_login_required
def company_predict():
    try:
        data = request.get_json()
        company_request_id = session.get('company_request_id')
        company_model, message = load_company_model(company_request_id)
        if not company_model:
            return jsonify({"error": message}), 400

        # Build input dataframe from provided json data
        input_df = pd.DataFrame([data])

        # Prepare the input to match the model's expected features
        prepared = prepare_input_for_model(input_df, model_obj=company_model, metadata_obj=metadata)

        # If prepared has zero columns, return error
        if prepared.shape[1] == 0:
            return jsonify({"error": "Prepared input is empty; cannot predict."}), 400

        # Make prediction
        prediction = company_model.predict(prepared)

        # Update predictions count in database
        db: Session = next(get_db())
        company_request = db.query(CompanyRequest).filter(CompanyRequest.id == company_request_id).first()
        if company_request:
            company_request.predictions_count = (company_request.predictions_count or 0) + 1
            company_request.updated_at = datetime.now(timezone.utc)
            db.commit()

        return jsonify({
            "predicted_salary": float(prediction[0]),
            "model_accuracy": session.get('model_accuracy', 0.85),
            "company_name": session.get('company_name', 'Your Company')
        })

    except Exception as e:
        logger.error(f"❌ Prediction error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Prediction error: {str(e)}"}), 500

# --- NEW: Settings and Analytics Routes ---
@app.route('/api/company/change-password', methods=['POST'])
@company_login_required
def change_company_password():
    """Change company user password"""
    try:
        data = request.get_json()
        current_password = data.get('current_password')
        new_password = data.get('new_password')

        if not current_password or not new_password:
            return jsonify({"error": "Current password and new password are required"}), 400

        if len(new_password) < 6:
            return jsonify({"error": "New password must be at least 6 characters long"}), 400

        db: Session = next(get_db())
        user = db.query(CompanyUser).filter(
            CompanyUser.id == session.get('company_id')
        ).first()

        if not user:
            return jsonify({"error": "User not found"}), 404

        # Verify current password
        if user.password != current_password:
            return jsonify({"error": "Current password is incorrect"}), 401

        # Update password
        user.password = new_password
        db.commit()

        logger.info(f"✅ Password changed for user: {user.username}")

        return jsonify({
            "message": "Password changed successfully",
            "username": user.username
        })

    except Exception as e:
        logger.error(f"❌ Password change error: {e}")
        return jsonify({"error": f"Password change failed: {str(e)}"}), 500

# FIXED: Removed duplicate route definition
@app.route('/api/company/retrain', methods=['POST'])
@company_login_required
def retrain_company_model():
    # Initialize variables to None
    filename = None
    file_path = None
    
    try:
        if 'dataset' not in request.files:
            return jsonify({"error": "File required"}), 400
            
        file = request.files.get('dataset')
        if not file or not file.filename.endswith('.csv'):
            return jsonify({"error": "Valid CSV file required"}), 400
        
        company_name = session.get('company_name')
        filename = f"{company_name.replace(' ', '_')}_retrain_{secrets.token_hex(4)}.csv"
        file_path = config.UPLOAD_FOLDER / filename
        file.save(file_path)
        
        # Validate Dataset
        valid, msg, mapping = DatasetValidator.validate_required_columns(file_path)
        if not valid: 
            if file_path.exists(): file_path.unlink()
            return jsonify({"error": msg}), 400
            
        DatasetValidator.prepare_mapped_dataset(file_path, mapping).to_csv(file_path, index=False)
        
        # Train Model
        model_filename, accuracy = train_company.train_company_model(file_path, company_name)
        
        # Update DB
        db: Session = next(get_db())
        req = db.query(CompanyRequest).filter(CompanyRequest.company_name == company_name).first()
        req.model_filename = model_filename
        req.model_accuracy = accuracy
        req.updated_at = datetime.now(timezone.utc)
        db.commit()
        
        return jsonify({"message": "Retraining successful", "new_accuracy": accuracy})

    except Exception as e:
        logger.error(f"Retrain Error: {e}")
        # Cleanup on error
        if file_path and file_path.exists():
            file_path.unlink()
        return jsonify({"error": str(e)}), 500

@app.route('/api/company/delete-account', methods=['POST'])
@company_login_required
def delete_company_account():
    """Request company account deletion"""
    try:
        db: Session = next(get_db())
        company_id = session.get('company_id')
        company_name = session.get('company_name')

        user = db.query(CompanyUser).filter(CompanyUser.id == company_id).first()
        company_request = db.query(CompanyRequest).filter(
            CompanyRequest.company_name == company_name
        ).first()

        if not user or not company_request:
            return jsonify({"error": "Company account not found"}), 404

        # Send notification to admin
        admin_email = config.EMAIL_CONFIG.get('ADMIN_EMAIL') or config.EMAIL_CONFIG.get('SENDER_EMAIL')
        if admin_email:
            subject = f"[Account Deletion Request] {company_name}"
            body = (
                f"Company {company_name} has requested account deletion.\n\n"
                f"Contact: {company_request.contact_person}\n"
                f"Email: {company_request.email}\n"
                f"Username: {user.username}\n\n"
                f"Please review and process this deletion request in the admin panel."
            )
            _send_email(subject, body, to_emails=[admin_email])

        logger.info(f"✅ Account deletion requested for: {company_name}")

        return jsonify({
            "message": "Account deletion request submitted. Admin will process your request shortly.",
            "company_name": company_name
        })

    except Exception as e:
        logger.error(f"❌ Account deletion request error: {e}")
        return jsonify({"error": f"Account deletion request failed: {str(e)}"}), 500

@app.route('/api/company/analytics')
@company_login_required
def get_company_analytics():
    """Return full analytics data for the company dashboard"""
    try:
        db: Session = next(get_db())

        company_name = session.get('company_name')
        company_request_id = session.get('company_request_id')

        if not company_name:
            return jsonify({"error": "Company name missing from session"}), 400

        # Try to get company request using ID or fallback by name
        company_request = None
        if company_request_id:
            company_request = db.query(CompanyRequest).filter(
                CompanyRequest.id == company_request_id
            ).first()

        if not company_request:
            company_request = db.query(CompanyRequest).filter(
                CompanyRequest.company_name == company_name
            ).first()

        if not company_request:
            return jsonify({"error": "Company record not found"}), 404

        # --- NEW: Calculate active days based on login history ---
        days_active = 0
        user = db.query(CompanyUser).filter(CompanyUser.username == company_request.username).first()
        if user and getattr(user, "login_days", None):
            try:
                login_days = json.loads(user.login_days)
                days_active = len(set(login_days))
            except Exception:
                days_active = 0

        # Try to load metadata file for advanced analytics
        model_details = {
            "type": "Random Forest Regressor",
            "algorithm": "Ensemble Learning",
            "features_count": 8,
            "training_method": "Supervised Learning",
            "cross_validation": "5-fold",
            "hyperparameters": "Optimized"
        }

        metadata_path = config.COMPANY_MODELS_FOLDER / f"{company_name.replace(' ', '_').lower()}_metadata.json"
        if metadata_path.exists():
            try:
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)
                numeric = len(metadata.get("features_used", {}).get("numeric", []))
                categorical = len(metadata.get("features_used", {}).get("categorical", []))
                model_details["features_count"] = numeric + categorical
            except Exception as e:
                logger.warning(f"Metadata parsing failed for {company_name}: {e}")

        analytics = {
            "company_name": company_request.company_name,
            "data_points": company_request.data_points or 0,
            "predictions_count": company_request.predictions_count or 0,
            "days_active": days_active,
            "model_accuracy": (
                round(float(company_request.model_accuracy) * 100, 2)
                if company_request.model_accuracy is not None else 0.0
            ),
            "last_training": (
                company_request.updated_at.isoformat()
                if company_request.updated_at else None
            ),
            "model_details": model_details
        }

        return jsonify(analytics), 200

    except Exception as e:
        logger.error(f"❌ Error loading analytics for company: {e}", exc_info=True)
        return jsonify({"error": f"Failed to load analytics: {str(e)}"}), 500

@app.route('/api/company/profile')
@company_login_required
def get_company_profile():
    """Return detailed company profile data for the dashboard"""
    try:
        db: Session = next(get_db())
        company_id = session.get('company_id')
        company_request_id = session.get('company_request_id')

        user = db.query(CompanyUser).filter(CompanyUser.id == company_id).first()
        company_request = db.query(CompanyRequest).filter(CompanyRequest.id == company_request_id).first()

        if not user or not company_request:
            return jsonify({"error": "Company not found"}), 404

        profile = {
            "username": user.username,
            "company_name": user.company_name,
            "contact_person": company_request.contact_person,
            "email": company_request.email,
            "phone": company_request.phone,
            "status": company_request.status or "active",
            "approved_at": company_request.approved_at.isoformat() if company_request.approved_at else None,
            "last_training": company_request.updated_at.isoformat() if company_request.updated_at else None,
            "data_points": company_request.data_points or 0,
            "predictions_count": company_request.predictions_count or 0,
            "model_accuracy": (
                f"{round(float(company_request.model_accuracy) * 100, 2)}%"
                if company_request.model_accuracy else "0%"
            )
        }

        return jsonify(profile)

    except Exception as e:
        logger.error(f"❌ Error loading company profile: {e}")
        return jsonify({"error": f"Failed to load company profile: {str(e)}"}), 500

# --- Admin Management Routes ---
@app.route('/api/admin/list')
@admin_login_required
def get_admin_list():
    """Get list of all admin users"""
    try:
        db: Session = next(get_db())
        admins = db.query(AdminUser).order_by(AdminUser.created_at.desc()).all()
        
        admins_data = []
        for admin in admins:
            admins_data.append({
                "id": admin.id,
                "full_name": admin.full_name,
                "username": admin.username,
                "email": admin.email,
                "is_active": admin.is_active,
                "created_at": admin.created_at.isoformat() if admin.created_at else None,
                "created_by": admin.created_by
            })
        
        return jsonify(admins_data)
    except Exception as e:
        logger.error(f"❌ Error loading admin list: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/create', methods=['POST'])
@admin_login_required
def create_admin():
    """Create new admin user"""
    try:
        data = request.get_json()
        full_name = data.get('full_name')
        email = data.get('email')
        
        if not full_name or not email:
            return jsonify({"error": "Full name and email are required"}), 400
        
        # Validate email format
        import re
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, email):
            return jsonify({"error": "Invalid email format"}), 400
        
        db: Session = next(get_db())
        
        # Check if email already exists
        existing_admin = db.query(AdminUser).filter(AdminUser.email == email).first()
        if existing_admin:
            return jsonify({"error": "Admin with this email already exists"}), 400
        
        # Generate username and password
        username_base = full_name.lower().replace(' ', '.')
        username = f"{username_base}.{secrets.token_hex(3)}"
        password = generate_password(10)
        
        # Get current admin username from session
        current_admin = session.get('admin_username', 'System')
        
        # Create new admin
        new_admin = AdminUser(
            full_name=full_name,
            username=username,
            password=password,  # Store plain password (for demo only)
            email=email,
            created_by=current_admin
        )
        
        db.add(new_admin)
        db.commit()
        
        # Send credentials email
        subject = "Your Admin Account Credentials - AI Salary Predictor"
        body = f"""
        Hello {full_name},

        Your admin account has been created successfully.

        Login Credentials:
        -------------------
        Username: {username}
        Password: {password}
        Admin Panel URL: http://localhost:5000/admin-login

        Please login and change your password immediately.

        Best regards,
        System Administrator
        """
        
        # Send email (if configured)
        try:
            _send_email(subject, body, [email])
            email_sent = True
        except Exception as e:
            logger.warning(f"Could not send admin creation email: {e}")
            email_sent = False
        
        logger.info(f"✅ Created new admin: {full_name} ({username})")
        
        return jsonify({
            "message": "Admin created successfully",
            "username": username,
            "password": password,
            "email": email,
            "email_sent": email_sent
        })
        
    except Exception as e:
        logger.error(f"❌ Error creating admin: {e}")
        return jsonify({"error": f"Failed to create admin: {str(e)}"}), 500

@app.route('/api/admin/delete/<int:admin_id>', methods=['DELETE'])
@admin_login_required
def delete_admin(admin_id):
    """Delete admin user"""
    try:
        db: Session = next(get_db())
        
        # Prevent deleting yourself
        current_admin_username = session.get('admin_username')
        admin = db.query(AdminUser).filter(AdminUser.id == admin_id).first()
        
        if not admin:
            return jsonify({"error": "Admin not found"}), 404
        
        if admin.username == current_admin_username:
            return jsonify({"error": "Cannot delete your own account"}), 400
        
        # Delete admin
        db.delete(admin)
        db.commit()
        
        logger.info(f"✅ Deleted admin: {admin.full_name} ({admin.username})")
        
        return jsonify({"message": "Admin deleted successfully"})
        
    except Exception as e:
        logger.error(f"❌ Error deleting admin: {e}")
        return jsonify({"error": f"Failed to delete admin: {str(e)}"}), 500

# --- Admin Routes (PROTECTED) ---
@app.route('/api/admin/requests')
@admin_login_required
def get_company_requests():
    try:
        db: Session = next(get_db())
        requests = db.query(CompanyRequest).order_by(CompanyRequest.created_at.desc()).all()

        requests_data = []
        for req in requests:
            requests_data.append({
                "id": req.id,
                "company_name": req.company_name,
                "contact_person": req.contact_person,
                "email": req.email,
                "phone": req.phone,
                "status": req.status,
                "created_at": req.created_at.isoformat() if req.created_at else None,
                "approved_at": req.approved_at.isoformat() if req.approved_at else None,
                "model_accuracy": req.model_accuracy,
                "username": req.username,
                "password": req.password,
                "data_points": req.data_points,
                "predictions_count": req.predictions_count,
                "updated_at": req.updated_at.isoformat() if req.updated_at else None
            })

        return jsonify(requests_data)
    except Exception as e:
        logger.error(f"❌ Error loading requests: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/approve/<int:request_id>', methods=['POST'])
@admin_login_required
def approve_company_request(request_id):
    try:
        db: Session = next(get_db())
        company_request = db.query(CompanyRequest).filter(CompanyRequest.id == request_id).first()

        if not company_request:
            return jsonify({"error": "Request not found"}), 404

        if company_request.status == "approved":
            return jsonify({"error": "Request already approved"}), 400

        # Generate credentials
        username = f"{company_request.company_name.replace(' ', '').lower()}_{secrets.token_hex(4)}"
        password = generate_password()

        # Train model with company's dataset
        dataset_path = config.UPLOAD_FOLDER / company_request.dataset_filename
        
        # Count data points from the dataset
        try:
            df = pd.read_csv(dataset_path)
            data_points = len(df)
            logger.info(f"📊 Dataset has {data_points} records")
        except Exception as e:
            logger.warning(f"Could not count data points: {e}")
            data_points = 0
        
        # Train the model
        model_filename, accuracy = train_company.train_company_model(dataset_path, company_request.company_name)

        # Update company request with REAL data
        company_request.status = "approved"
        company_request.approved_at = datetime.now(timezone.utc)
        company_request.username = username
        company_request.password = password
        company_request.model_filename = model_filename
        company_request.model_accuracy = accuracy
        company_request.data_points = data_points  # REAL data points count
        company_request.predictions_count = 0  # Start with 0 predictions
        company_request.updated_at = datetime.now(timezone.utc)

        # Create company user
        company_user = CompanyUser(
            company_name=company_request.company_name,
            username=username,
            password=password,
            email=company_request.email,
            # Add company_id which is the foreign key to CompanyRequest
            company_id=company_request.id  # ADD THIS LINE
        )
        db.add(company_user)
        db.commit()

        # Send credentials to company
        send_company_credentials(company_request, username, password)

        logger.info(f"✅ Approved company {company_request.company_name} with accuracy {accuracy} and {data_points} data points")

        return jsonify({
            "message": "Company approved successfully",
            "username": username,
            "password": password,
            "model_accuracy": accuracy,
            "data_points": data_points
        })

    except Exception as e:
        logger.error(f"❌ Approval error: {e}")
        return jsonify({"error": f"Approval error: {str(e)}"}), 500

@app.route('/api/admin/reject/<int:request_id>', methods=['POST'])
@admin_login_required
def reject_company_request(request_id):
    try:
        db: Session = next(get_db())
        company_request = db.query(CompanyRequest).filter(CompanyRequest.id == request_id).first()

        if not company_request:
            return jsonify({"error": "Request not found"}), 404

        company_request.status = "rejected"
        db.commit()

        logger.info(f"✅ Rejected company request: {company_request.company_name}")

        return jsonify({"message": "Company request rejected successfully"})

    except Exception as e:
        logger.error(f"❌ Rejection error: {e}")
        return jsonify({"error": f"Rejection error: {str(e)}"}), 500

@app.route('/api/admin/delete/<int:request_id>', methods=['DELETE'])
@admin_login_required
def delete_company_request(request_id):
    try:
        db: Session = next(get_db())
        company_request = db.query(CompanyRequest).filter(CompanyRequest.id == request_id).first()

        if not company_request:
            return jsonify({"error": "Request not found"}), 404

        # Get related data before deletion for cleanup
        company_name = company_request.company_name
        username = company_request.username
        model_filename = company_request.model_filename
        dataset_filename = company_request.dataset_filename

        # Delete company user if exists
        if username:
            company_user = db.query(CompanyUser).filter(CompanyUser.username == username).first()
            if company_user:
                db.delete(company_user)

        # Delete company request
        db.delete(company_request)
        db.commit()

        # Clean up files
        try:
            # Delete model file
            if model_filename:
                model_path = config.COMPANY_MODELS_FOLDER / model_filename
                if model_path.exists():
                    model_path.unlink()
            
            # Delete options file
            options_filename = f"{company_name.replace(' ', '_').lower()}_options.json"
            options_path = config.COMPANY_MODELS_FOLDER / options_filename
            if options_path.exists():
                options_path.unlink()
            
            # Delete dataset file
            if dataset_filename:
                dataset_path = config.UPLOAD_FOLDER / dataset_filename
                if dataset_path.exists():
                    dataset_path.unlink()
                    
        except Exception as e:
            logger.warning(f"File cleanup warning for company {company_name}: {e}")

        logger.info(f"✅ Deleted company request: {company_name} (ID: {request_id})")

        return jsonify({
            "message": "Company request and all associated data deleted successfully",
            "deleted_company": company_name
        })

    except Exception as e:
        logger.error(f"❌ Deletion error: {e}")
        return jsonify({"error": f"Deletion error: {str(e)}"}), 500

# --- Force Deletion Routes ---
@app.route('/api/admin/companies')
@admin_login_required
def get_all_companies():
    """Get all approved companies for force deletion"""
    try:
        db: Session = next(get_db())
        companies = db.query(CompanyRequest).filter(
            CompanyRequest.status == "approved"
        ).order_by(CompanyRequest.company_name).all()
        
        companies_data = []
        for company in companies:
            companies_data.append({
                "id": company.id,
                "company_name": company.company_name,
                "username": company.username,
                "contact_person": company.contact_person,
                "email": company.email,
                "data_points": company.data_points,
                "predictions_count": company.predictions_count,
                "approved_at": company.approved_at.isoformat() if company.approved_at else None
            })
        
        return jsonify(companies_data)
    except Exception as e:
        logger.error(f"❌ Error loading companies: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/force-delete/<int:company_id>', methods=['DELETE'])
@admin_login_required
def force_delete_company(company_id):
    """Force delete company and all associated data"""
    try:
        db: Session = next(get_db())
        company_request = db.query(CompanyRequest).filter(CompanyRequest.id == company_id).first()
        
        if not company_request:
            return jsonify({"error": "Company not found"}), 404
        
        if company_request.status != "approved":
            return jsonify({"error": "Only approved companies can be force deleted"}), 400
        
        # Get related data before deletion for cleanup
        company_name = company_request.company_name
        username = company_request.username
        model_filename = company_request.model_filename
        dataset_filename = company_request.dataset_filename
        
        # Delete company user if exists
        if username:
            company_user = db.query(CompanyUser).filter(CompanyUser.username == username).first()
            if company_user:
                db.delete(company_user)
        
        # Delete company request
        db.delete(company_request)
        db.commit()
        
        # Clean up files
        files_deleted = []
        try:
            # Delete model file
            if model_filename:
                model_path = config.COMPANY_MODELS_FOLDER / model_filename
                if model_path.exists():
                    model_path.unlink()
                    files_deleted.append("Model file")
            
            # Delete options file
            options_filename = f"{company_name.replace(' ', '_').lower()}_options.json"
            options_path = config.COMPANY_MODELS_FOLDER / options_filename
            if options_path.exists():
                options_path.unlink()
                files_deleted.append("Options file")
            
            # Delete metadata file
            metadata_filename = f"{company_name.replace(' ', '_').lower()}_metadata.json"
            metadata_path = config.COMPANY_MODELS_FOLDER / metadata_filename
            if metadata_path.exists():
                metadata_path.unlink()
                files_deleted.append("Metadata file")
            
            # Delete dataset file
            if dataset_filename:
                dataset_path = config.UPLOAD_FOLDER / dataset_filename
                if dataset_path.exists():
                    dataset_path.unlink()
                    files_deleted.append("Dataset file")
                    
        except Exception as e:
            logger.warning(f"File cleanup warning for company {company_name}: {e}")
        
        # Log the force deletion
        logger.warning(f"⚠️ FORCE DELETED company: {company_name} (ID: {company_id})")
        logger.warning(f"   Files deleted: {', '.join(files_deleted)}")
        
        return jsonify({
            "message": "Company force deleted successfully",
            "deleted_company": company_name,
            "files_deleted": files_deleted
        })
        
    except Exception as e:
        logger.error(f"❌ Force deletion error: {e}")
        return jsonify({"error": f"Force deletion failed: {str(e)}"}), 500

# --- Static file serving ---
@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

# --- API endpoints for main app ---
@app.route('/options')
def get_options():
    """Return options for form fields with proper structure"""
    try:
        return jsonify({
            "categorical": options.get("categorical", {}),
            "numeric_meta": options.get("numeric_meta", {}),
            "numeric_cols": metadata.get("numeric_cols", []),
            "categorical_cols": metadata.get("categorical_cols", []),
        })
    except Exception as e:
        logger.error(f"❌ Error in /options endpoint: {e}")
        return jsonify({
            "categorical": {
                "gender": ["Male", "Female", "Other"],
                "role": ["Software Engineer", "Data Scientist", "Manager", "Analyst"],
                "sector": ["IT", "Finance", "Healthcare", "Education"],
                "company": ["Company A", "Company B", "Company C"],
                "department": ["Engineering", "Sales", "HR", "Marketing"],
                "education": ["Bachelor's", "Master's", "PhD", "High School"]
            },
            "numeric_meta": {
                "age": {"min": 18, "max": 65, "median": 30, "mean": 35},
                "experience": {"min": 0, "max": 40, "median": 5, "mean": 7}
            },
            "numeric_cols": ["age", "experience"],
            "categorical_cols": ["gender", "role", "sector", "company", "department", "education"]
        })

@app.route('/api/company/forgot-password', methods=['POST'])
def forgot_password():
    try:
        data = request.get_json()
        username_or_email = data.get("username_or_email")

        if not username_or_email:
            return jsonify({"error": "Username or Email required"}), 400

        db: Session = next(get_db())
        user = db.query(CompanyUser).filter(
            (CompanyUser.username == username_or_email) |
            (CompanyUser.email == username_or_email)
        ).first()

        if not user:
            return jsonify({"error": "User not found"}), 404

        # Generate OTP
        otp = str(secrets.randbelow(900000) + 100000)  # 6-digit
        expiry = datetime.now() + timedelta(minutes=5)

        user.otp_code = otp
        user.otp_expiry = expiry
        db.commit()

        # Send OTP via email
        subject = "Your OTP for Password Recovery"
        body = (
            f"Dear {user.username},\n\n"
            f"Your OTP for password recovery is: {otp}\n"
            f"This OTP will expire in 5 minutes.\n\n"
            f"Regards,\nAdmin Team"
        )

        _send_email(subject, body, [user.email])

        return jsonify({"message": "OTP sent successfully to your registered email."})

    except Exception as e:
        return jsonify({"error": f"OTP sending failed: {str(e)}"}), 500

@app.route('/api/company/verify-otp', methods=['POST'])
def verify_otp():
    try:
        data = request.get_json()
        username_or_email = data.get("username_or_email")
        otp = data.get("otp")

        db: Session = next(get_db())
        user = db.query(CompanyUser).filter(
            (CompanyUser.username == username_or_email) |
            (CompanyUser.email == username_or_email)
        ).first()

        if not user:
            return jsonify({"error": "User not found"}), 404

        # Validate OTP
        if not user.otp_code or otp != user.otp_code:
            return jsonify({"error": "Invalid OTP"}), 400

        if datetime.now() > user.otp_expiry:
            return jsonify({"error": "OTP expired"}), 400

        # OTP verified → send credentials
        subject = "Your Login Credentials Recovery"
        body = (
            f"Hello {user.username},\n\n"
            f"Your account credentials are:\n"
            f"Username: {user.username}\n"
            f"Password: {user.password}\n\n"
            f"Please login and change your password immediately.\n\n"
            f"Regards,\nAdmin Team"
        )

        _send_email(subject, body, [user.email])

        # Clear OTP after verification
        user.otp_code = None
        user.otp_expiry = None
        db.commit()

        return jsonify({"message": "OTP verified! Credentials sent to your email."})

    except Exception as e:
        return jsonify({"error": f"OTP verification failed: {str(e)}"}), 500

@app.route('/model-comparison')
def get_model_comparison():
    return jsonify({
        "model_comparison": metadata.get("model_comparison", {}),
        "best_model": metadata.get("model_name", "N/A"),
        "cv_score": metadata.get("cv_score", 0),
        "all_models": metadata.get("all_models", [])
    })

@app.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid input"}), 400

        logger.info(f"📥 Received prediction request: {data}")

        # Check for required fields
        required_fields = ['age', 'experience', 'gender', 'role', 'sector', 'company', 'department', 'education']
        missing_fields = [field for field in required_fields if field not in data or data[field] is None or data[field] == '']

        if missing_fields:
            return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

        # Create input DataFrame with only the required fields in correct order
        input_data = {}
        for field in required_fields:
            if field in ['age', 'experience']:
                # Convert numeric fields
                try:
                    input_data[field] = float(data[field])
                except (ValueError, TypeError):
                    return jsonify({"error": f"Invalid value for {field}. Must be a number."}), 400
            else:
                input_data[field] = str(data[field])

        input_df = pd.DataFrame([input_data])

        logger.info(f"🔧 Processed input data: {input_data}")
        logger.info(f"📊 Input DataFrame shape: {input_df.shape}")

        # Prepare input for model (handles missing engineered features)
        prepared_df = prepare_input_for_model(input_df, model_obj=model, metadata_obj=metadata)

        logger.info(f"Prepared DataFrame columns: {prepared_df.columns.tolist()}")

        # Make prediction
        prediction = model.predict(prepared_df)

        logger.info(f"🎯 Prediction result: {prediction[0]}")

        return jsonify({
            "predicted_salary": float(prediction[0]),
            "model_used": metadata.get("model_name", "N/A")
        })
    except Exception as e:
        logger.error(f"❌ Prediction Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Failed to make prediction.", "details": str(e)}), 500

@app.before_request
def before_request():
    """Set session as permanent before each request and check expiry"""
    session.permanent = True
    app.permanent_session_lifetime = timedelta(hours=24)
    
    # Check admin session expiry on each request
    if session.get('admin_logged_in'):
        is_admin_logged_in()  # This will automatically clear expired sessions

# --- Error handlers ---
@app.errorhandler(404)
def not_found(error):
    return "Page not found. Please check the URL.", 404

@app.errorhandler(500)
def internal_error(error):
    return "Internal server error.", 500
def scheduled_automation_task():
    """
    This runs automatically every 1 hour.
    It checks if the admin has enabled 'Automated Mode'.
    """
    with app.app_context():
        # 1. Check the current mode set by the admin toggle
        current_mode = AUTOMATION_SETTINGS.get('mode', 'manual')
        
        # 2. IF Manual: Do nothing (just log it)
        if current_mode != 'automated':
            logger.info("ℹ️ Scheduler ran, but system is in MANUAL mode. Skipping tasks.")
            return

        # 3. IF Automated: Run the logic
        try:
            logger.info("🤖 System is in AUTOMATED mode. Running scheduled checks...")
            db: Session = next(get_db())
            
            # Initialize system in automated mode
            system = AutomationSystem(db, email_sender=_send_email, mode='automated')
            
            # Execute warning emails and deletions
            results = system.run_automation()
            
            logger.info(f"✅ Automated Task Completed: {results}")
            
        except Exception as e:
            logger.error(f"❌ Automated Task Failed: {e}")

# Initialize Scheduler
# We use Asia/Kolkata timezone to ensure logs match your local time
scheduler = BackgroundScheduler(timezone=pytz.timezone('Asia/Kolkata'))

# Add the job to run every 60 minutes
scheduler.add_job(func=scheduled_automation_task, trigger="interval", minutes=60)

# Start the scheduler
scheduler.start()

# Ensure scheduler shuts down when app exits
atexit.register(lambda: scheduler.shutdown())
if __name__ == '__main__':
    print("🚀 Starting AI Salary Predictor...")
    print("=" * 60)
    
    # Check if emails are configured
    email_cfg = config.EMAIL_CONFIG
    if email_cfg.get('SENDER_EMAIL') and email_cfg.get('SENDER_PASSWORD'):
        print("📧 Email functionality: ENABLED (using configured SMTP settings)")
    else:
        print("📧 Email functionality: DISABLED (using console output)")
    
    print("\n🌐 Application URLs:")
    print("=" * 60)
    print("📍 Main Application:     http://localhost:5000")
    print("📍 Admin Login:         http://localhost:5000/admin-login")
    print("📍 Company Login:       http://localhost:5000/company-login")
    print("📍 Company Registration: http://localhost:5000/company-request")
    print("\n🔐 Session lifetime: 24 hours")
    print("📁 Template files required in templates/ folder:")
    print("   - index.html, company_request.html, company_login.html")
    print("   - company_dashboard.html, admin_panel.html, admin_login.html")
    print("=" * 60)
    print("🚀 Starting AI Salary Predictor with Automation Scheduler...")
    app.run(host='0.0.0.0', port=5000, debug=True)