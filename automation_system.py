"""
Automation System for Admin Portal
Handles inactive accounts and low accuracy accounts with warning/notification system
"""

import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from database import CompanyUser, CompanyRequest
import config
from pathlib import Path

logger = logging.getLogger(__name__)

class AccountStatus:
    GREEN = "green"
    YELLOW = "yellow"
    ORANGE = "orange"
    RED = "red"

class AutomationMode:
    AUTOMATED = "automated"
    MANUAL = "manual"

# automation_system.py - Fix the get_inactive_accounts method
class AutomationSystem:
    def __init__(self, db: Session, email_sender=None, mode=AutomationMode.MANUAL):
        self.db = db
        self.email_sender = email_sender
        self.mode = mode
        self.logger = logging.getLogger(__name__)
        
    def get_inactive_accounts(self):
        """Get list of inactive company accounts"""
        try:
            inactive_accounts = []
            
            # Get all active company users
            users = self.db.query(CompanyUser).filter(
                CompanyUser.is_active == True
            ).all()
            
            for user in users:
                # Get company request for additional info
                company_request = self.db.query(CompanyRequest).filter(
                    CompanyRequest.username == user.username
                ).first()
                
                if not company_request:
                    continue
                
                # Calculate inactivity
                if user.last_login_date:
                    # Ensure both datetimes are aware
                    last_login = user.last_login_date
                    if last_login.tzinfo is None:
                        last_login = last_login.replace(tzinfo=timezone.utc)
                    
                    current_time = datetime.now(timezone.utc)
                    days_inactive = (current_time - last_login).days
                else:
                    days_inactive = 999  # Never logged in
                
                # Determine status based on inactivity
                status = "active"
                if days_inactive > 90:
                    status = "critical"
                elif days_inactive > 60:
                    status = "warning_3"
                elif days_inactive > 30:
                    status = "warning_2"
                elif days_inactive > 14:
                    status = "warning_1"
                
                # Only include if inactive for more than 14 days
                if days_inactive > 14:
                    inactive_accounts.append({
                        "user_id": user.id,
                        "company_name": company_request.company_name,
                        "email": company_request.email,
                        "days_inactive": days_inactive,
                        "status": status,
                        "last_login_date": user.last_login_date.isoformat() if user.last_login_date else None,
                        "company_request_id": company_request.id
                    })
            
            return inactive_accounts
            
        except Exception as e:
            self.logger.error(f"Error in get_inactive_accounts: {e}")
            return []
    
    def get_inactivity_level(self, last_login_date):
        """Determine inactivity level based on last login"""
        if not last_login_date:
            return AccountStatus.RED, "No login history"
        
        current_time = datetime.now(timezone.utc)
        days_inactive = (current_time - last_login_date).days
        
        if days_inactive >= 180:  # 6 months
            return AccountStatus.RED, f"Inactive for {days_inactive} days (≥6 months)"
        elif days_inactive >= 90:  # 3-5 months
            return AccountStatus.ORANGE, f"Inactive for {days_inactive} days (3-5 months)"
        elif days_inactive >= 60:  # 2-3 months
            return AccountStatus.YELLOW, f"Inactive for {days_inactive} days (2-3 months)"
        else:
            return AccountStatus.GREEN, f"Active (inactive for {days_inactive} days)"
    
    def get_inactive_accounts(self):
        """Get all inactive accounts with their status levels"""
        inactive_accounts = []
        company_users = self.db.query(CompanyUser).all()
        
        for user in company_users:
            status, message = self.get_inactivity_level(user.last_login_date)
            
            if status != AccountStatus.GREEN:
                company_request = self.db.query(CompanyRequest).filter(
                    CompanyRequest.username == user.username
                ).first()
                
                if company_request:
                    inactive_accounts.append({
                        "user_id": user.id,
                        "username": user.username,
                        "company_name": user.company_name,
                        "email": user.email,
                        "last_login": user.last_login_date.isoformat() if user.last_login_date else "Never",
                        "status": status,
                        "status_message": message,
                        "company_request_id": company_request.id,
                        "warnings_sent": getattr(user, 'warnings_sent', 0) or 0,
                        "last_warning_sent": getattr(user, 'last_warning_sent', None)
                    })
        return inactive_accounts
    
    def _trigger_email(self, subject, body, to_email):
        """Internal helper to use the injected email sender"""
        if self.email_sender:
            try:
                return self.email_sender(subject, body, [to_email])
            except Exception as e:
                logger.error(f"Email callback failed: {e}")
                return False
        else:
            logger.warning(f"No email sender configured. Mocking email to {to_email}")
            return True # Assume success if no sender is configured (Mock Mode)

    def send_inactivity_warning(self, user, company_request, level, days_inactive):
        """Send inactivity warning email"""
        subject = f"Account Inactivity Warning - {user.company_name}"
        
        if level == AccountStatus.ORANGE:
            body = f"""
            Dear {user.username},
            
            Your account for {user.company_name} has been inactive for {days_inactive} days (3-5 months).
            
            WARNING: If you don't log in and use the prediction service within the next month, 
            your account will be marked for deletion.
            
            To keep your account active, please log in and make at least one prediction.
            
            Login URL: http://localhost:5000/company-login
            
            Best regards,
            Admin Team - AI Salary Predictor
            """
        elif level == AccountStatus.RED:
            body = f"""
            URGENT: Account Deletion Warning - {user.company_name}
            
            Dear {user.username},
            
            Your account has been inactive for {days_inactive} days (≥6 months).
            
            FINAL NOTICE: Your account is scheduled for deletion in 7 days.
            
            If you want to use this account in the future, please log in and use the prediction app 
            within the next 7 days to reset your account status.
            
            Login URL: http://localhost:5000/company-login
            
            After 7 days of inactivity, your account and all associated data will be 
            permanently deleted.
            
            Best regards,
            Admin Team - AI Salary Predictor
            """
        else:
            return False
        
        success = self._trigger_email(subject, body, user.email)
        if success:
            user.warnings_sent = (user.warnings_sent or 0) + 1
            user.last_warning_sent = datetime.now(timezone.utc)
            self.db.commit()
            logger.info(f"Sent {level} warning to {user.email}")
        return success
    
    def send_deletion_notification(self, user, company_request):
        """Send account deletion notification"""
        subject = f"Account Deleted Due to Inactivity - {user.company_name}"
        body = f"""
        Dear {user.username},
        
        Your account for {user.company_name} has been permanently deleted due to prolonged inactivity.
        
        All associated data including:
        - Company profile
        - Trained model
        - Dataset files
        - Prediction history
        
        ...has been removed from our system.
        
        If you wish to use our services again in the future, you'll need to submit a new company request.
        
        Thank you for using our service.
        
        Best regards,
        Admin Team - AI Salary Predictor
        """
        
        success = self._trigger_email(subject, body, user.email)
        if success:
            logger.info(f"Sent deletion notification to {user.email}")
        return success
    
    def delete_inactive_account(self, user, company_request):
        """Delete inactive account and all associated files"""
        try:
            company_name = user.company_name
            
            # 1. Delete model files
            if company_request.model_filename:
                model_path = config.COMPANY_MODELS_FOLDER / company_request.model_filename
                if model_path.exists():
                    model_path.unlink()
            
            # 2. Delete options file
            options_filename = f"{company_name.replace(' ', '_').lower()}_options.json"
            options_path = config.COMPANY_MODELS_FOLDER / options_filename
            if options_path.exists():
                options_path.unlink()
            
            # 3. Delete metadata file
            metadata_filename = f"{company_name.replace(' ', '_').lower()}_metadata.json"
            metadata_path = config.COMPANY_MODELS_FOLDER / metadata_filename
            if metadata_path.exists():
                metadata_path.unlink()
            
            # 4. Delete dataset file
            if company_request.dataset_filename:
                dataset_path = config.UPLOAD_FOLDER / company_request.dataset_filename
                if dataset_path.exists():
                    dataset_path.unlink()
            
            # 5. Delete from database
            self.db.delete(company_request)
            self.db.delete(user)
            self.db.commit()
            
            logger.warning(f"Deleted inactive account: {company_name} (User: {user.username})")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting account {user.username}: {e}")
            self.db.rollback()
            return False
    
    def process_inactive_accounts(self):
        """Process all inactive accounts based on automation mode"""
        if self.mode != AutomationMode.AUTOMATED:
            return []
        
        results = []
        inactive_accounts = self.get_inactive_accounts()
        
        for account in inactive_accounts:
            user = self.db.query(CompanyUser).filter(CompanyUser.id == account["user_id"]).first()
            company_request = self.db.query(CompanyRequest).filter(CompanyRequest.id == account["company_request_id"]).first()
            
            if not user or not company_request: continue
            
            status = account["status"]
            last_login = user.last_login_date
            current_time = datetime.now(timezone.utc)
            
            if status == AccountStatus.ORANGE:
                days_inactive = (current_time - last_login).days if last_login else 999
                self.send_inactivity_warning(user, company_request, status, days_inactive)
                results.append({"action": "warning_sent", "company": user.company_name, "level": "orange"})
                
            elif status == AccountStatus.RED:
                last_warning = user.last_warning_sent
                if not last_warning:
                    days_inactive = (current_time - last_login).days if last_login else 999
                    self.send_inactivity_warning(user, company_request, status, days_inactive)
                    results.append({"action": "final_warning_sent", "company": user.company_name})
                elif (current_time - last_warning).days >= 7:
                    self.send_deletion_notification(user, company_request)
                    success = self.delete_inactive_account(user, company_request)
                    if success:
                        results.append({"action": "account_deleted", "company": user.company_name, "reason": "inactivity"})
        
        return results
    
    def get_low_accuracy_accounts(self, threshold=0.70):
        """Get accounts with model accuracy below threshold"""
        low_accuracy_accounts = []
        company_requests = self.db.query(CompanyRequest).filter(
            CompanyRequest.status == "approved",
            CompanyRequest.model_accuracy.isnot(None),
            CompanyRequest.model_accuracy < threshold
        ).all()
        
        for request in company_requests:
            user = self.db.query(CompanyUser).filter(CompanyUser.username == request.username).first()
            if user:
                low_accuracy_accounts.append({
                    "company_request_id": request.id,
                    "company_name": request.company_name,
                    "username": request.username,
                    "email": request.email,
                    "model_accuracy": float(request.model_accuracy),
                    "user_id": user.id,
                    "data_points": request.data_points or 0,
                    "accuracy_warning_sent": getattr(request, 'accuracy_warning_sent', False) or False,
                    "last_accuracy_check": getattr(request, 'last_accuracy_check', None)
                })
        return low_accuracy_accounts
    
    def send_low_accuracy_warning(self, user, company_request, accuracy):
        """Send low accuracy warning email"""
        subject = f"Low Model Accuracy Alert - {user.company_name}"
        body = f"""
        Dear {user.username},
        
        Our system has detected that your company's salary prediction model has low accuracy ({accuracy:.1%}).
        
        RECOMMENDATION: 
        1. Upload a larger or more diverse dataset
        2. Ensure your dataset has proper formatting
        
        Login URL: http://localhost:5000/company-login
        
        Best regards,
        Admin Team - AI Salary Predictor
        """
        
        success = self._trigger_email(subject, body, user.email)
        if success:
            company_request.accuracy_warning_sent = True
            company_request.last_accuracy_check = datetime.now(timezone.utc)
            self.db.commit()
            logger.info(f"Sent low accuracy warning to {user.email}")
        return success
    
    def send_accuracy_deletion_notification(self, user, company_request, accuracy):
        subject = f"Account Suspended - Low Model Accuracy - {user.company_name}"
        body = f"""
        Dear {user.username},
        
        Your account for {user.company_name} has been suspended due to persistently low model accuracy ({accuracy:.1%}).
        
        All associated data has been removed from our system.
        
        Best regards,
        Admin Team - AI Salary Predictor
        """
        
        success = self._trigger_email(subject, body, user.email)
        return success
    
    def delete_low_accuracy_account(self, user, company_request):
        return self.delete_inactive_account(user, company_request)
    
    def process_low_accuracy_accounts(self, threshold=0.70):
        if self.mode != AutomationMode.AUTOMATED: return []
        
        results = []
        low_acc_accounts = self.get_low_accuracy_accounts(threshold)
        
        for account in low_acc_accounts:
            user = self.db.query(CompanyUser).filter(CompanyUser.username == account["username"]).first()
            company_request = self.db.query(CompanyRequest).filter(CompanyRequest.id == account["company_request_id"]).first()
            
            if not user or not company_request: continue
            
            accuracy = account["model_accuracy"]
            warning_sent = account["accuracy_warning_sent"]
            
            if not warning_sent:
                self.send_low_accuracy_warning(user, company_request, accuracy)
                results.append({"action": "accuracy_warning_sent", "company": user.company_name})
            else:
                last_check = company_request.last_accuracy_check
                if last_check and (datetime.now(timezone.utc) - last_check).days >= 30:
                    if accuracy < threshold:
                        self.send_accuracy_deletion_notification(user, company_request, accuracy)
                        success = self.delete_low_accuracy_account(user, company_request)
                        if success:
                            results.append({"action": "account_deleted", "company": user.company_name, "reason": "low_accuracy"})
        return results
    
    def run_automation(self):
        """Run all automation processes"""
        logger.info("Running automation processes...")
        results = {
            "inactive_accounts_processed": self.process_inactive_accounts(),
            "low_accuracy_accounts_processed": self.process_low_accuracy_accounts(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        logger.info(f"Automation completed. Results: {results}")
        return results