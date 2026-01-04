# email_service.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import config

def send_email(to_email, subject, body, attachment_path=None):
    """Send email with optional attachment"""
    try:
        # Skip email if no configuration
        if not config.EMAIL_CONFIG['SENDER_EMAIL']:
            print(f"📧 Email skipped (no config): {to_email} - {subject}")
            return True
            
        msg = MIMEMultipart()
        msg['From'] = config.EMAIL_CONFIG['SENDER_EMAIL']
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'html'))
        
        # Attach file if provided
        if attachment_path and attachment_path.exists():
            with open(attachment_path, 'rb') as file:
                attach = MIMEApplication(file.read(), _subtype="csv")
                attach.add_header('Content-Disposition', 'attachment', 
                                filename=attachment_path.name)
                msg.attach(attach)
        
        # Send email
        server = smtplib.SMTP(config.EMAIL_CONFIG['SMTP_SERVER'], 
                            config.EMAIL_CONFIG['SMTP_PORT'])
        server.starttls()
        server.login(config.EMAIL_CONFIG['SENDER_EMAIL'], 
                    config.EMAIL_CONFIG['SENDER_PASSWORD'])
        server.send_message(msg)
        server.quit()
        print(f"✅ Email sent successfully to: {to_email}")
        return True
    except Exception as e:
        print(f"❌ Email error to {to_email}: {e}")
        return False

def send_admin_notification(company_request, db):
    """Send notification to admin about new company request"""
    subject = f"New Company Request: {company_request.company_name}"
    body = f"""
    <h3>New Company Registration Request</h3>
    <p><strong>Company:</strong> {company_request.company_name}</p>
    <p><strong>Contact Person:</strong> {company_request.contact_person}</p>
    <p><strong>Email:</strong> {company_request.email}</p>
    <p><strong>Phone:</strong> {company_request.phone or 'Not provided'}</p>
    <p><strong>Submitted:</strong> {company_request.created_at}</p>
    
    <p>Please review the request in the admin panel.</p>
    """
    
    attachment_path = config.UPLOAD_FOLDER / company_request.dataset_filename
    return send_email(config.EMAIL_CONFIG['ADMIN_EMAIL'], subject, body, attachment_path)

def send_company_credentials(company_request, username, password):
    """Send login credentials to company"""
    subject = f"Your AI Salary Predictor Credentials - {company_request.company_name}"
    body = f"""
    <h3>Welcome to AI Salary Predictor!</h3>
    <p>Your company registration has been approved.</p>
    
    <div style="background: #f5f7fa; padding: 20px; border-radius: 8px; margin: 15px 0;">
        <h4>Login Credentials:</h4>
        <p><strong>Username:</strong> {username}</p>
        <p><strong>Password:</strong> {password}</p>
        <p><strong>Login URL:</strong> http://your-domain.com/company-login</p>
    </div>
    
    <p>You can now access your company dashboard and start making salary predictions.</p>
    <p><strong>Note:</strong> Please keep your credentials secure.</p>
    """
    
    return send_email(company_request.email, subject, body)

# Email configuration helper
def setup_email_config(sender_email, sender_password, admin_email=None):
    """Helper function to setup email configuration"""
    config.EMAIL_CONFIG['SENDER_EMAIL'] = sender_email
    config.EMAIL_CONFIG['SENDER_PASSWORD'] = sender_password
    if admin_email:
        config.EMAIL_CONFIG['ADMIN_EMAIL'] = admin_email
    print("✅ Email configuration updated")