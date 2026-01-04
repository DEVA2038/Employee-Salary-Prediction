# database.py - UPDATED VERSION WITH IMPROVEMENTS
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, DateTime,
    Boolean, Float, ForeignKey, JSON
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, timezone, timedelta
import sqlite3
import os
import json
import config

# ---------------------------
# Database Setup
# ---------------------------
engine = create_engine(config.DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in config.DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_current_utc_time():
    """Get current time in UTC with timezone awareness"""
    return datetime.now(timezone.utc)


# ============================================================
#  ADMIN USER TABLE
# ============================================================
class AdminUser(Base):
    __tablename__ = 'admin_users'
    
    id = Column(Integer, primary_key=True)
    full_name = Column(String(100), nullable=False)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
    created_by = Column(String(50))
    created_at = Column(DateTime, default=get_current_utc_time)
    updated_at = Column(DateTime, default=get_current_utc_time, onupdate=get_current_utc_time)
    last_login = Column(DateTime, nullable=True)
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'full_name': self.full_name,
            'username': self.username,
            'email': self.email,
            'is_active': self.is_active,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }


# ============================================================
#  COMPANY DATASET TABLE
# ============================================================
class CompanyDataset(Base):
    __tablename__ = 'company_datasets'
    
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey('company_requests.id', ondelete='CASCADE'), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)  # in bytes
    records_count = Column(Integer)
    upload_date = Column(DateTime, default=get_current_utc_time)
    is_active = Column(Boolean, default=False)
    dataset_type = Column(String(50))  # 'original', 'retrain', 'update'
    dataset_metadata = Column(Text)
    uploaded_by = Column(String(100), nullable=True)
    file_hash = Column(String(64), nullable=True)  # SHA256 hash for file integrity
    
    # Relationships
    company = relationship("CompanyRequest", backref="datasets")
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'company_id': self.company_id,
            'filename': self.filename,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'records_count': self.records_count,
            'upload_date': self.upload_date.isoformat() if self.upload_date else None,
            'is_active': self.is_active,
            'dataset_type': self.dataset_type,
            'uploaded_by': self.uploaded_by,
            'file_hash': self.file_hash
        }


# ============================================================
#  COMPANY REQUEST TABLE (admin approval + dataset + model)
# ============================================================
class CompanyRequest(Base):
    __tablename__ = 'company_requests'
    
    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String(200), nullable=False)
    contact_person = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False)
    phone = Column(String(20))
    dataset_filename = Column(String(255), nullable=False)
    status = Column(String(50), default='pending')  # pending, approved, rejected, suspended
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    approved_at = Column(DateTime(timezone=True))
    approved_by = Column(String(100), nullable=True)
    username = Column(String(100), unique=True, nullable=True)
    password = Column(String(100), nullable=True)
    model_filename = Column(String(255))
    model_accuracy = Column(Float)
    model_training_date = Column(DateTime, nullable=True)
    data_points = Column(Integer, default=0)
    predictions_count = Column(Integer, default=0)
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    column_mapping = Column(JSON, nullable=True)
    accuracy_warning_sent = Column(Boolean, default=False)
    last_accuracy_check = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    subscription_tier = Column(String(50), default='basic')  # basic, premium, enterprise
    api_key = Column(String(64), unique=True, nullable=True)
    
    def __repr__(self):
        return f"<CompanyRequest {self.company_name} ({self.status})>"
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'company_name': self.company_name,
            'contact_person': self.contact_person,
            'email': self.email,
            'phone': self.phone,
            'dataset_filename': self.dataset_filename,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'approved_by': self.approved_by,
            'username': self.username,
            'model_filename': self.model_filename,
            'model_accuracy': self.model_accuracy,
            'model_training_date': self.model_training_date.isoformat() if self.model_training_date else None,
            'data_points': self.data_points,
            'predictions_count': self.predictions_count,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'column_mapping': self.column_mapping,
            'subscription_tier': self.subscription_tier,
            'api_key': self.api_key
        }


# ============================================================
#  COMPANY USER TABLE (login + OTP + tracking)
# ============================================================
class CompanyUser(Base):
    __tablename__ = "company_users"
    
    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String(200), nullable=False)
    company_id = Column(Integer, ForeignKey('company_requests.id'), nullable=False, unique=True)
    username = Column(String(100), unique=True, nullable=False)
    password = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=True)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=get_current_utc_time)
    last_password_change = Column(DateTime, default=get_current_utc_time)

    # --- Login Tracking ---
    login_days = Column(Text, default=json.dumps([]))     # list of login dates
    last_login_date = Column(DateTime, nullable=True)
    last_login_ip = Column(String(45), nullable=True)     # IPv4 or IPv6
    total_logins = Column(Integer, default=0)

    # --- OTP for Forgot Password ---
    otp_code = Column(String(10), nullable=True)
    otp_expiry = Column(DateTime, nullable=True)
    otp_attempts = Column(Integer, default=0)
    warnings_sent = Column(Integer, default=0)
    last_warning_sent = Column(DateTime, nullable=True)
    
    # --- Security ---
    failed_login_attempts = Column(Integer, default=0)
    account_locked_until = Column(DateTime, nullable=True)
    mfa_enabled = Column(Boolean, default=False)
    
    # Relationship
    company = relationship("CompanyRequest", backref="user_account", uselist=False)
    
    def is_account_locked(self):
        """Check if account is currently locked"""
        if not self.account_locked_until:
            return False
        return datetime.now(timezone.utc) < self.account_locked_until
    
    def to_dict(self, include_sensitive=False):
        """Convert to dictionary for JSON serialization"""
        data = {
            'id': self.id,
            'company_name': self.company_name,
            'company_id': self.company_id,
            'username': self.username,
            'email': self.email,
            'phone': self.phone,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login_date': self.last_login_date.isoformat() if self.last_login_date else None,
            'total_logins': self.total_logins,
            'mfa_enabled': self.mfa_enabled
        }
        
        if include_sensitive:
            data.update({
                'last_password_change': self.last_password_change.isoformat() if self.last_password_change else None,
                'warnings_sent': self.warnings_sent,
                'failed_login_attempts': self.failed_login_attempts,
                'account_locked': self.is_account_locked()
            })
        
        return data


# ============================================================
#  AUDIT LOG TABLE
# ============================================================
class AuditLog(Base):
    __tablename__ = 'audit_logs'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=get_current_utc_time)
    user_type = Column(String(20))  # 'admin', 'company', 'system'
    user_id = Column(Integer, nullable=True)
    username = Column(String(100), nullable=True)
    action = Column(String(100), nullable=False)  # 'login', 'logout', 'create', 'update', 'delete', 'approve', 'reject'
    entity_type = Column(String(50))  # 'company_request', 'dataset', 'user', 'model'
    entity_id = Column(Integer, nullable=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'user_type': self.user_type,
            'user_id': self.user_id,
            'username': self.username,
            'action': self.action,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'details': self.details,
            'ip_address': self.ip_address
        }


# ============================================================
#  PREDICTION LOG TABLE
# ============================================================
class PredictionLog(Base):
    __tablename__ = 'prediction_logs'
    
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey('company_requests.id'), nullable=False)
    timestamp = Column(DateTime, default=get_current_utc_time)
    input_data = Column(JSON, nullable=True)
    prediction_result = Column(JSON, nullable=True)
    model_version = Column(String(50), nullable=True)
    processing_time = Column(Float, nullable=True)  # in seconds
    api_key_used = Column(String(64), nullable=True)
    ip_address = Column(String(45), nullable=True)
    
    # Relationship
    company = relationship("CompanyRequest", backref="prediction_logs")


# ============================================================
#  SCHEMA VERIFICATION (Auto-fix missing columns)
# ============================================================
def verify_database_schema():
    db_path = config.DATABASE_URL.replace("sqlite:///", "")
    
    # Handle in-memory database
    if db_path == ":memory:":
        Base.metadata.create_all(bind=engine)
        print("✅ Created new in-memory database with full schema")
        return

    if not os.path.exists(db_path):
        Base.metadata.create_all(bind=engine)
        print("✅ Created new database with full schema")
        print("✅ Created tables: admin_users, company_requests, company_users, company_datasets, audit_logs, prediction_logs")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get all existing tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = {row[0] for row in cursor.fetchall()}
        
        # Check if all required tables exist
        required_tables = {
            'admin_users', 'company_requests', 'company_users', 
            'company_datasets', 'audit_logs', 'prediction_logs'
        }
        missing_tables = required_tables - existing_tables
        
        if missing_tables:
            print(f"⚠️ Missing tables: {missing_tables}")
        
        # Define required columns for each table
        table_requirements = {
            'admin_users': [
                "id", "full_name", "username", "password", "email", 
                "is_active", "created_by", "created_at", "updated_at", "last_login"
            ],
            'company_requests': [
                "id", "company_name", "contact_person", "email", "phone",
                "dataset_filename", "status", "created_at", "approved_at",
                "approved_by", "username", "password", "model_filename",
                "model_accuracy", "data_points", "predictions_count",
                "updated_at", "column_mapping", "accuracy_warning_sent",
                "last_accuracy_check", "rejection_reason", "subscription_tier",
                "api_key", "model_training_date"
            ],
            'company_users': [
                "id", "company_name", "company_id", "username", "password",
                "email", "phone", "is_active", "created_at", "last_password_change",
                "login_days", "last_login_date", "last_login_ip", "total_logins",
                "otp_code", "otp_expiry", "otp_attempts", "warnings_sent",
                "last_warning_sent", "failed_login_attempts", "account_locked_until",
                "mfa_enabled"
            ],
            'company_datasets': [
                "id", "company_id", "filename", "file_path", "file_size",
                "records_count", "upload_date", "is_active", "dataset_type",
                "dataset_metadata", "uploaded_by", "file_hash"
            ],
            'audit_logs': [
                "id", "timestamp", "user_type", "user_id", "username",
                "action", "entity_type", "entity_id", "details", "ip_address",
                "user_agent"
            ],
            'prediction_logs': [
                "id", "company_id", "timestamp", "input_data", "prediction_result",
                "model_version", "processing_time", "api_key_used", "ip_address"
            ]
        }
        
        # Check missing columns for each existing table
        missing_columns = {}
        for table, required_columns in table_requirements.items():
            if table in existing_tables:
                cursor.execute(f"PRAGMA table_info({table})")
                existing_columns = [col[1] for col in cursor.fetchall()]
                missing = [col for col in required_columns if col not in existing_columns]
                if missing:
                    missing_columns[table] = missing

        needs_update = bool(missing_tables or missing_columns)

        if needs_update:
            print("⚠️ Database schema outdated. Updating schema...")
            print(f"Missing tables: {missing_tables}")
            for table, columns in missing_columns.items():
                print(f"Missing columns in {table}: {columns}")

            # Backup existing data
            existing_data = {}
            for table in required_tables.union(existing_tables):
                try:
                    cursor.execute(f"SELECT * FROM {table}")
                    existing_data[table] = {
                        'rows': cursor.fetchall(),
                        'columns': [desc[0] for desc in cursor.description] if cursor.description else []
                    }
                except:
                    existing_data[table] = {'rows': [], 'columns': []}
            
            conn.close()

            # Backup old DB
            backup = db_path + ".backup"
            if os.path.exists(backup):
                os.remove(backup)
            os.rename(db_path, backup)
            print(f"📦 Backup created: {backup}")

            # Recreate DB with updated schema
            Base.metadata.drop_all(bind=engine)
            Base.metadata.create_all(bind=engine)
            
            # Restore data if possible
            try:
                new_conn = sqlite3.connect(db_path)
                new_cursor = new_conn.cursor()
                
                for table in existing_data:
                    if table not in required_tables:
                        continue  # Skip old tables that are no longer needed
                        
                    data = existing_data[table]
                    if data['rows'] and data['columns']:
                        # Get column info for this table in new schema
                        new_cursor.execute(f"PRAGMA table_info({table})")
                        new_columns = [col[1] for col in new_cursor.fetchall()]
                        
                        # Create mapping between old and new columns
                        column_mapping = []
                        for old_col in data['columns']:
                            if old_col in new_columns:
                                column_mapping.append(old_col)
                            else:
                                column_mapping.append(None)  # Column doesn't exist in new schema
                        
                        # Insert data
                        for row in data['rows']:
                            # Map row values to new columns
                            new_values = []
                            for i, old_col in enumerate(data['columns']):
                                if i < len(row) and column_mapping[i] is not None:
                                    new_values.append(row[i])
                            
                            if new_values:
                                placeholders = ','.join(['?'] * len(new_values))
                                column_names = ','.join([col for col, mapped in zip(data['columns'], column_mapping) if mapped is not None])
                                try:
                                    new_cursor.execute(f"INSERT INTO {table} ({column_names}) VALUES ({placeholders})", new_values)
                                except Exception as e:
                                    print(f"Warning: Could not insert row into {table}: {e}")
                
                new_conn.commit()
                new_conn.close()
                print("✅ Data restored from backup")
                
            except Exception as restore_error:
                print(f"⚠️ Could not restore data: {restore_error}")
                print("✓ Database created with empty tables")

            print("✅ Database schema updated successfully")

        else:
            print("✓ Database schema is already up to date.")
            conn.close()

    except Exception as e:
        print(f"❌ Schema verification error: {e}")
        # If schema verification fails, ensure tables exist
        Base.metadata.create_all(bind=engine)
        print("✅ Created tables as fallback")


# Run schema verification when file loads
verify_database_schema()


# ============================================================
#  DATABASE UTILITIES
# ============================================================
def init_database():
    """Initialize database with default admin user if empty"""
    from werkzeug.security import generate_password_hash
    
    db = SessionLocal()
    try:
        # Check if any admin users exist
        admin_count = db.query(AdminUser).count()
        
        if admin_count == 0:
            # Create default admin user
            default_admin = AdminUser(
                full_name="System Administrator",
                username="admin",
                password=generate_password_hash("admin123"),  # Should be changed on first login
                email="admin@system.local",
                created_by="system",
                is_active=True
            )
            db.add(default_admin)
            db.commit()
            print("✅ Created default admin user: admin / admin123")
            
        # Check if company_users table has company_id column
        try:
            db.execute("SELECT company_id FROM company_users LIMIT 1")
        except:
            print("⚠️ Company users table needs migration. Run schema update.")
            
    except Exception as e:
        print(f"❌ Database initialization error: {e}")
        db.rollback()
    finally:
        db.close()


# ============================================================
#  SESSION PROVIDER
# ============================================================
def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Initialize database on import
if __name__ != "__main__":
    init_database()