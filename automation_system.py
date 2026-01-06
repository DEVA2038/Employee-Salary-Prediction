# automation_system.py - FIXED VERSION
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
        if isinstance(mode, AutomationMode):
            self.mode = mode
        elif isinstance(mode, str):
            try:
                self.mode = AutomationMode(mode)
            except ValueError:
                logger.warning(f"Invalid mode '{mode}', defaulting to MANUAL")
                self.mode = AutomationMode.MANUAL
        else:
            logger.warning(f"Invalid mode type {type(mode)}, defaulting to MANUAL")
            self.mode = AutomationMode.MANUAL
        
    def get_inactive_accounts(self, threshold_days: int = 14) -> List[Dict[str, Any]]:
        """Get accounts that haven't logged in for threshold_days"""
        try:
            current_time = datetime.now(timezone.utc)
            cutoff_date = current_time - timedelta(days=threshold_days)
            
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
                        logger.warning(f"No company request found for user: {user.username}")
                        continue
                    
                    # Calculate days inactive with proper timezone handling
                    days_inactive = 0
                    
                    if user.last_login_date:
                        # Ensure both datetimes are timezone-aware
                        last_login = user.last_login_date
                        if last_login.tzinfo is None:
                            # Make naive datetime timezone-aware (assume UTC)
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
                    
                    # Only include if inactive for more than threshold
                    if days_inactive > threshold_days:
                        # Determine status based on days
                        status = self.get_inactivity_level(days_inactive)
                        
                        inactive_accounts.append({
                            "user_id": user.id,
                            "username": user.username,
                            "company_name": company_request.company_name,
                            "email": company_request.email or user.email,
                            "days_inactive": days_inactive,
                            "status": status,
                            "last_login_date": user.last_login_date,
                            "company_request_id": company_request.id
                        })
                        
                except Exception as user_error:
                    logger.error(f"Error processing user {user.id}: {user_error}")
                    continue
            
            logger.info(f"Found {len(inactive_accounts)} inactive accounts (>{threshold_days} days)")
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
                        # Find corresponding user
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
                    logger.error(f"Error processing request {req.id}: {req_error}")
                    continue
            
            logger.info(f"Found {len(low_acc_accounts)} accounts with accuracy < {threshold}")
            return low_acc_accounts
            
        except Exception as e:
            logger.error(f"Error in get_low_accuracy_accounts: {e}")
            return []
    
    def send_inactivity_warning(self, user: CompanyUser, company_request: CompanyRequest, 
                              level: str, days_inactive: int) -> bool:
        """Send inactivity warning email"""
        try:
            if not self.email_sender:
                logger.warning("Email sender not configured")
                return False
            
            subject = f"Account Inactivity Warning - {company_request.company_name}"
            
            # Customize message based on level
            if level == "critical":
                warning_msg = "IMMEDIATE ACTION REQUIRED: Your account will be deleted in 7 days due to prolonged inactivity."
            elif level == "warning_3":
                warning_msg = "FINAL WARNING: Your account will be deleted soon due to inactivity."
            elif level == "warning_2":
                warning_msg = "SECOND WARNING: Your account has been inactive for an extended period."
            else:
                warning_msg = "REMINDER: Your account has been inactive for a while."
            
            body = f"""
            Dear {company_request.contact_person},
            
            {warning_msg}
            
            Account Details:
            - Company: {company_request.company_name}
            - Days Inactive: {days_inactive}
            - Last Login: {user.last_login_date.strftime('%Y-%m-%d %H:%M:%S') if user.last_login_date else 'Never'}
            
            To keep your account active, please login to the system.
            
            Login URL: http://localhost:5000/company-login
            
            If you no longer wish to use our services, you can ignore this email.
            Accounts inactive for more than 90 days are automatically deleted.
            
            Best regards,
            AI Salary Predictor Admin Team
            """
            
            # Send email
            success = self.email_sender(
                subject=subject,
                body=body,
                to_emails=[company_request.email]
            )
            
            if success:
                logger.info(f"Sent inactivity warning to {company_request.company_name} (Level: {level})")
            else:
                logger.warning(f"Failed to send inactivity warning to {company_request.company_name}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending inactivity warning: {e}")
            return False
    
    def send_low_accuracy_warning(self, user: CompanyUser, company_request: CompanyRequest, 
                                 accuracy: float) -> bool:
        """Send low accuracy warning email"""
        try:
            if not self.email_sender:
                logger.warning("Email sender not configured")
                return False
            
            subject = f"Model Accuracy Alert - {company_request.company_name}"
            
            body = f"""
            Dear {company_request.contact_person},
            
            Your salary prediction model accuracy has dropped below acceptable levels.
            
            Model Details:
            - Current Accuracy: {accuracy:.2%}
            - Recommended Action: Retrain your model with updated data
            
            Low accuracy can lead to unreliable predictions. We recommend:
            1. Uploading more recent salary data
            2. Retraining your model via the dashboard
            3. Contacting support if you need assistance
            
            Login to your dashboard to retrain: http://localhost:5000/company-dashboard
            
            If accuracy remains low, your access to predictions may be limited.
            
            Best regards,
            AI Salary Predictor Admin Team
            """
            
            # Send email
            success = self.email_sender(
                subject=subject,
                body=body,
                to_emails=[company_request.email]
            )
            
            if success:
                logger.info(f"Sent low accuracy warning to {company_request.company_name}")
            else:
                logger.warning(f"Failed to send low accuracy warning to {company_request.company_name}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending low accuracy warning: {e}")
            return False
    
    def delete_inactive_account(self, user: CompanyUser, company_request: CompanyRequest) -> bool:
        """Delete inactive account and associated data"""
        try:
            company_name = company_request.company_name
            
            # Send deletion notification
            if self.email_sender:
                subject = f"Account Deleted - {company_name}"
                body = f"""
                Dear {company_request.contact_person},
                
                Your account for {company_name} has been deleted due to prolonged inactivity.
                
                Account Details:
                - Company: {company_name}
                - Username: {user.username}
                - Deletion Reason: Account inactive for more than 90 days
                
                If this was a mistake or you wish to reactivate your account, 
                please contact our support team.
                
                All associated data including your custom model has been removed.
                
                Best regards,
                AI Salary Predictor Admin Team
                """
                
                self.email_sender(
                    subject=subject,
                    body=body,
                    to_emails=[company_request.email]
                )
            
            # Mark user as inactive (soft delete)
            user.is_active = False
            user.updated_at = datetime.now(timezone.utc)
            
            # Mark company request as deleted
            company_request.status = "deleted"
            company_request.updated_at = datetime.now(timezone.utc)
            
            # Commit changes
            self.db.commit()
            
            logger.info(f"Deleted inactive account: {company_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting account: {e}")
            self.db.rollback()
            return False
    
    def run_automation(self) -> Dict[str, Any]:
        """Run all automation processes"""
        try:
            logger.info("Running automation processes...")
            
            # Handle both string and enum mode values
            mode_value = self.mode.value if hasattr(self.mode, 'value') else str(self.mode)
            
            results = {
                "inactive_warnings_sent": 0,
                "accuracy_warnings_sent": 0,
                "accounts_deleted": 0,
                "mode": mode_value  # Use the converted value
            }
            
            # Get inactive accounts
            inactive_accounts = self.get_inactive_accounts(threshold_days=14)
            low_accuracy_accounts = self.get_low_accuracy_accounts(threshold=0.65)
            
            # Convert mode to enum for comparisons
            current_mode = self.mode
            if isinstance(current_mode, str):
                # Convert string to enum for comparison
                current_mode = AutomationMode(current_mode)
            
            # Process inactive accounts
            for account in inactive_accounts:
                try:
                    user = self.db.query(CompanyUser).filter(
                        CompanyUser.id == account["user_id"]
                    ).first()
                    
                    company_request = self.db.query(CompanyRequest).filter(
                        CompanyRequest.id == account["company_request_id"]
                    ).first()
                    
                    if not user or not company_request:
                        continue
                    
                    # Check if we should take action based on mode
                    should_warn = (
                        current_mode == AutomationMode.AUTOMATED or 
                        account["status"] in ["critical", "warning_3"]
                    )
                    
                    if should_warn:
                        # Send warning based on level
                        success = self.send_inactivity_warning(
                            user, company_request, 
                            account["status"], account["days_inactive"]
                        )
                        
                        if success:
                            results["inactive_warnings_sent"] += 1
                    
                    # Delete critical accounts (90+ days) in automated mode
                    if current_mode == AutomationMode.AUTOMATED and account["status"] == "critical":
                        success = self.delete_inactive_account(user, company_request)
                        if success:
                            results["accounts_deleted"] += 1
                            
                except Exception as e:
                    logger.error(f"Error processing inactive account {account.get('user_id')}: {e}")
                    continue
            
            # Process low accuracy accounts
            for account in low_accuracy_accounts:
                try:
                    user = self.db.query(CompanyUser).filter(
                        CompanyUser.id == account["user_id"]
                    ).first()
                    
                    company_request = self.db.query(CompanyRequest).filter(
                        CompanyRequest.id == account["company_request_id"]
                    ).first()
                    
                    if not user or not company_request:
                        continue
                    
                    # Send warning in automated mode or for very low accuracy
                    if current_mode == AutomationMode.AUTOMATED or account["model_accuracy"] < 0.5:
                        success = self.send_low_accuracy_warning(
                            user, company_request, account["model_accuracy"]
                        )
                        
                        if success:
                            results["accuracy_warnings_sent"] += 1
                            
                except Exception as e:
                    logger.error(f"Error processing low accuracy account {account.get('user_id')}: {e}")
                    continue
            
            logger.info(f"Automation completed: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Error in run_automation: {e}")
            logger.error(traceback.format_exc())
            
            # Handle both string and enum mode values in error response too
            mode_value = self.mode.value if hasattr(self.mode, 'value') else str(self.mode)
            
            return {
                "error": str(e),
                "inactive_warnings_sent": 0,
                "accuracy_warnings_sent": 0,
                "accounts_deleted": 0,
                "mode": mode_value
            }