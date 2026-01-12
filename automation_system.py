# automation_system.py - FINAL UPDATED VERSION
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from database import CompanyUser, CompanyRequest
from enum import Enum
import traceback

logger = logging.getLogger(__name__)

class AutomationMode(Enum):
    MANUAL = "manual"
    AUTOMATED = "automated"

class AutomationSystem:
    def __init__(self, db_session: Session, email_sender=None, mode=None):
        self.db = db_session
        self.email_sender = email_sender
        
        # Robust handling of mode input (String or Enum)
        if isinstance(mode, AutomationMode):
            self.mode = mode
        elif isinstance(mode, str):
            try:
                self.mode = AutomationMode(mode.lower())
            except ValueError:
                logger.warning(f"Invalid mode string '{mode}', defaulting to MANUAL")
                self.mode = AutomationMode.MANUAL
        else:
            if mode is not None:
                logger.warning(f"Invalid mode type {type(mode)}, defaulting to MANUAL")
            self.mode = AutomationMode.MANUAL
        
    def get_inactive_accounts(self, threshold_days: int = 14) -> List[Dict[str, Any]]:
        """Get accounts that haven't logged in for threshold_days"""
        try:
            current_time = datetime.now(timezone.utc)
            
            # Get all active company users
            users = self.db.query(CompanyUser).filter(
                CompanyUser.is_active == True
            ).all()
            
            inactive_accounts = []
            
            for user in users:
                try:
                    # Find corresponding company request
                    company_request = self.db.query(CompanyRequest).filter(
                        CompanyRequest.username == user.username
                    ).first()
                    
                    if not company_request:
                        continue
                    
                    # Calculate days inactive with proper timezone handling
                    days_inactive = 0
                    
                    if user.last_login_date:
                        last_login = user.last_login_date
                        if last_login.tzinfo is None:
                            last_login = last_login.replace(tzinfo=timezone.utc)
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
                    
                    # Only include if inactive for more than threshold
                    if days_inactive > threshold_days:
                        status_level, status_msg = self.get_inactivity_level(days_inactive)
                        
                        inactive_accounts.append({
                            "user_id": user.id,
                            "username": user.username,
                            "company_name": company_request.company_name,
                            "email": company_request.email or user.email,
                            "days_inactive": days_inactive,
                            "status": status_level,
                            "status_message": status_msg,
                            "last_login_date": user.last_login_date,
                            "company_request_id": company_request.id
                        })
                        
                except Exception as user_error:
                    logger.error(f"Error processing user {user.id}: {user_error}")
                    continue
            
            return inactive_accounts
            
        except Exception as e:
            logger.error(f"Error in get_inactive_accounts: {e}")
            logger.error(traceback.format_exc())
            return []
    
    def get_inactivity_level(self, days_inactive: int) -> Tuple[str, str]:
        """Determine inactivity level and message"""
        if days_inactive > 90:
            return "critical", f"Account inactive for {days_inactive} days. Immediate deletion recommended."
        elif days_inactive > 60:
            return "warning_3", f"Account inactive for {days_inactive} days. Final warning."
        elif days_inactive > 30:
            return "warning_2", f"Account inactive for {days_inactive} days. Second warning."
        elif days_inactive > 14:
            return "warning_1", f"Account inactive for {days_inactive} days. First warning."
        else:
            return "active", "Account is active"
    
    def get_low_accuracy_accounts(self, threshold: float = 0.65) -> List[Dict[str, Any]]:
        """Get accounts with model accuracy below threshold"""
        try:
            low_acc_accounts = []
            
            # Get all approved company requests
            company_requests = self.db.query(CompanyRequest).filter(
                CompanyRequest.status == "approved",
                CompanyRequest.model_accuracy != None
            ).all()
            
            for req in company_requests:
                try:
                    accuracy = float(req.model_accuracy or 0)
                    if accuracy < threshold:
                        user = self.db.query(CompanyUser).filter(
                            CompanyUser.username == req.username
                        ).first()
                        
                        if user:
                            low_acc_accounts.append({
                                "user_id": user.id,
                                "username": user.username,
                                "company_name": req.company_name,
                                "model_accuracy": accuracy,
                                "company_request_id": req.id,
                                "last_accuracy_check": req.updated_at
                            })
                except Exception as req_error:
                    continue
            
            return low_acc_accounts
            
        except Exception as e:
            logger.error(f"Error in get_low_accuracy_accounts: {e}")
            return []
    
    def send_inactivity_warning(self, user: CompanyUser, company_request: CompanyRequest, 
                              level: str, days_inactive: int) -> bool:
        """Send inactivity warning email (Called by batch or manual button)"""
        try:
            if not self.email_sender:
                logger.warning("Email sender not configured")
                return False
            
            subject = f"Action Required: Account Inactivity Warning - {company_request.company_name}"
            
            if level == "critical":
                warning_msg = "URGENT: Your account is scheduled for deletion in 7 days due to inactivity (>90 days)."
            elif level == "warning_3":
                warning_msg = "FINAL NOTICE: Your account has been inactive for over 60 days."
            elif level == "warning_2":
                warning_msg = "NOTICE: Your account has been inactive for over 30 days."
            else:
                warning_msg = "REMINDER: We noticed you haven't logged in recently."
            
            body = f"""
            Dear {company_request.contact_person},
            
            {warning_msg}
            
            Account Status:
            ----------------
            Company: {company_request.company_name}
            Days Inactive: {days_inactive}
            Last Login: {user.last_login_date.strftime('%Y-%m-%d') if user.last_login_date else 'Never'}
            
            To keep your account active, please log in immediately:
            http://localhost:5000/company-login
            
            Note: Accounts inactive for more than 90 days are automatically deleted by our system.
            
            Best regards,
            AI Salary Predictor System
            """
            
            return self.email_sender(
                subject=subject,
                body=body,
                to_emails=[company_request.email]
            )
            
        except Exception as e:
            logger.error(f"Error sending inactivity warning: {e}")
            return False
    
    def send_low_accuracy_warning(self, user: CompanyUser, company_request: CompanyRequest, 
                                 accuracy: float) -> bool:
        """Send low accuracy warning email (Called by batch or manual button)"""
        try:
            if not self.email_sender:
                return False
            
            subject = f"Model Performance Alert - {company_request.company_name}"
            
            body = f"""
            Dear {company_request.contact_person},
            
            Our automated system detected that your salary prediction model's accuracy has dropped.
            
            Current Accuracy: {accuracy:.1%}
            Threshold: 65.0%
            
            To improve predictions, we recommend uploading a new dataset and retraining your model via the dashboard.
            
            Login here: http://localhost:5000/company-login
            
            Best regards,
            AI Salary Predictor System
            """
            
            return self.email_sender(
                subject=subject,
                body=body,
                to_emails=[company_request.email]
            )
            
        except Exception as e:
            logger.error(f"Error sending low accuracy warning: {e}")
            return False
    
    def delete_inactive_account(self, user: CompanyUser, company_request: CompanyRequest) -> bool:
        """Delete inactive account (Called by batch or manual button)"""
        try:
            company_name = company_request.company_name
            
            if self.email_sender:
                subject = f"Account Deleted - {company_name}"
                body = f"""
                Dear {company_request.contact_person},
                
                Your account has been deleted due to inactivity (>90 days).
                
                If you wish to use our services again, please submit a new registration request.
                
                Best regards,
                AI Salary Predictor System
                """
                self.email_sender(
                    subject=subject,
                    body=body,
                    to_emails=[company_request.email]
                )
            
            user.is_active = False
            company_request.status = "deleted"
            company_request.updated_at = datetime.now(timezone.utc)
            
            self.db.commit()
            logger.info(f"✅ Automatically deleted inactive account: {company_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting account: {e}")
            self.db.rollback()
            return False
    
    def run_automation(self) -> Dict[str, Any]:
        """
        Run the automation logic.
        - Manual Mode: Identifies issues but takes ZERO actions.
        - Automated Mode: Sends warnings AND automatically deletes critical accounts.
        """
        try:
            logger.info(f"🚀 Running Automation Process (Mode: {self.mode.value})")
            
            results = {
                "inactive_warnings_sent": 0,
                "accuracy_warnings_sent": 0,
                "accounts_deleted": 0,
                "mode": self.mode.value
            }
            
            # 1. Fetch Data
            inactive_accounts = self.get_inactive_accounts(threshold_days=14)
            low_accuracy_accounts = self.get_low_accuracy_accounts(threshold=0.65)
            
            # 2. Process Inactive Accounts
            for account in inactive_accounts:
                try:
                    user = self.db.query(CompanyUser).filter(CompanyUser.id == account["user_id"]).first()
                    req = self.db.query(CompanyRequest).filter(CompanyRequest.id == account["company_request_id"]).first()
                    
                    if not user or not req: continue
                    
                    # LOGIC CHANGE: Only send warnings if mode is AUTOMATED
                    if self.mode == AutomationMode.AUTOMATED:
                        if self.send_inactivity_warning(user, req, account["status"], account["days_inactive"]):
                            results["inactive_warnings_sent"] += 1
                        
                        # LOGIC: DELETE only if mode is AUTOMATED and status is CRITICAL
                        if account["status"] == "critical":
                            if self.delete_inactive_account(user, req):
                                results["accounts_deleted"] += 1
                    else:
                        # Manual Mode: Do nothing (User must click buttons in UI)
                        pass
                            
                except Exception as e:
                    logger.error(f"Error processing inactive account {account.get('company_name')}: {e}")
            
            # 3. Process Low Accuracy Accounts
            for account in low_accuracy_accounts:
                try:
                    user = self.db.query(CompanyUser).filter(CompanyUser.id == account["user_id"]).first()
                    req = self.db.query(CompanyRequest).filter(CompanyRequest.id == account["company_request_id"]).first()
                    
                    if not user or not req: continue
                    
                    # LOGIC CHANGE: Only warn if mode is AUTOMATED
                    if self.mode == AutomationMode.AUTOMATED:
                        if self.send_low_accuracy_warning(user, req, account["model_accuracy"]):
                            results["accuracy_warnings_sent"] += 1
                    else:
                        # Manual Mode: Do nothing
                        pass
                        
                except Exception as e:
                    logger.error(f"Error processing low accuracy account {account.get('company_name')}: {e}")
            
            return results
            
        except Exception as e:
            logger.error(f"CRITICAL Automation Failure: {e}")
            logger.error(traceback.format_exc())
            return {
                "error": str(e), 
                "mode": self.mode.value if self.mode else "unknown"
            }