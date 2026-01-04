// static/js/company.js - UPDATED

// --- NEW: Define required columns for client-side validation ---
const REQUIRED_COLUMNS = [
    'age', 'experience', 'gender', 'role', 'sector', 
    'company', 'department', 'education', 'salary'
];

document.addEventListener('DOMContentLoaded', function() {
    initializeThemeToggle();
    
    // File upload handling (for company request page)
    const uploadArea = document.getElementById('upload-area');
    const fileInput = document.getElementById('dataset');
    const fileInfo = document.getElementById('file-info');
    
    // Forms
    const companyForm = document.getElementById('company-form');
    const loginForm = document.getElementById('login-form');

    // --- NEW: Forgot Password Modal Elements ---
    const forgotPasswordBtn = document.getElementById('forgot-password-btn');
    const modal = document.getElementById('forgot-password-modal');
    const closeModalBtn = document.getElementById('modal-close-btn');
    const sendOtpForm = document.getElementById('send-otp-form');
    const verifyOtpForm = document.getElementById('verify-otp-form');
    
    // File upload handling
    if (uploadArea && fileInput) {
        setupFileUpload(uploadArea, fileInput, fileInfo);
    }
    
    // Company registration form
    if (companyForm) {
        companyForm.addEventListener('submit', handleCompanyRegistration);
    }
    
    // Login form handling
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }

    // --- NEW: Forgot Password Listeners ---
    if (forgotPasswordBtn && modal && closeModalBtn) {
        forgotPasswordBtn.addEventListener('click', () => {
            modal.classList.remove('hidden');
        });
        closeModalBtn.addEventListener('click', () => {
            modal.classList.add('hidden');
            resetModal();
        });
        // Close modal if clicking outside the content
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.add('hidden');
                resetModal();
            }
        });
    }

    // Handle Send OTP
    if (sendOtpForm) {
        sendOtpForm.addEventListener('submit', handleSendOtp);
    }

    // Handle Verify OTP
    if (verifyOtpForm) {
        verifyOtpForm.addEventListener('submit', handleVerifyOtp);
    }
});

function initializeThemeToggle() {
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        const icon = themeToggle.querySelector('i');

        // Load saved theme
        const savedTheme = localStorage.getItem('theme') || 'light';
        document.documentElement.setAttribute('data-theme', savedTheme);
        icon.className = savedTheme === 'dark' ? 'fa-solid fa-sun' : 'fa-solid fa-moon';

        themeToggle.addEventListener('click', function() {
            const currentTheme = document.documentElement.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', newTheme);
            icon.className = newTheme === 'dark' ? 'fa-solid fa-sun' : 'fa-solid fa-moon';
            localStorage.setItem('theme', newTheme);
        });
    }
}

function setupFileUpload(uploadArea, fileInput, fileInfo) {
    uploadArea.addEventListener('click', () => fileInput.click());
    
    uploadArea.addEventListener('dragover', (e) => { e.preventDefault(); uploadArea.classList.add('dragover'); });
    uploadArea.addEventListener('dragleave', () => { uploadArea.classList.remove('dragover'); });
    
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            fileInput.files = files;
            handleFileSelect(files[0], fileInfo);
        }
    });
    
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileSelect(e.target.files[0], fileInfo);
        }
    });
}

function getCsvHeader(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (event) => {
            try {
                const firstLine = event.target.result.split('\n')[0].trim();
                const headers = firstLine.split(',').map(h => h.trim().toLowerCase());
                resolve(headers);
            } catch (err) { reject('Could not read file header.'); }
        };
        reader.onerror = () => { reject('Error reading file.'); };
        reader.readAsText(file.slice(0, 1024));
    });
}

async function handleFileSelect(file, fileInfo) {
    if (file && file.type === 'text/csv') {
        try {
            const headers = await getCsvHeader(file);
            const missingColumns = REQUIRED_COLUMNS.filter(col => !headers.includes(col.toLowerCase()));
            
            if (missingColumns.length > 0) {
                showResult(`Invalid CSV. Missing columns: ${missingColumns.join(', ')}`, 'error', 'result');
                removeFile();
                return;
            }

            const fileSize = (file.size / 1024 / 1024).toFixed(2);
            fileInfo.innerHTML = `
                <div>
                    <i class="fa-solid fa-file-csv"></i>
                    <span id="file-name">${file.name}</span>
                    <span id="file-size" class="text-muted">(${fileSize} MB)</span>
                </div>
                <button type="button" onclick="removeFile()" title="Remove file">
                    <i class="fa-solid fa-times"></i>
                </button>
            `;
            fileInfo.classList.remove('hidden');
            showResult('', 'success', 'result', 0); // Hide message
        } catch (err) {
            showResult(err, 'error', 'result');
            removeFile();
        }
    } else {
        showResult('Please upload a valid CSV file.', 'error', 'result');
        removeFile();
    }
}

function removeFile() {
    const fileInput = document.getElementById('dataset');
    const fileInfo = document.getElementById('file-info');
    if (fileInput) fileInput.value = '';
    if (fileInfo) fileInfo.classList.add('hidden');
}

async function handleCompanyRegistration(e) {
    e.preventDefault();
    const submitBtn = e.target.querySelector('#submit-btn');
    const originalText = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Submitting...';
    
    const formData = new FormData(e.target);

    if (!formData.get('dataset').name) {
        showResult('Please upload your salary dataset.', 'error', 'result');
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
        return;
    }
    
    // --- FIX: Re-enabled the original fetch call ---
    // The simulation code has been removed.
    
    try {
        const response = await fetch('/api/company/request', {
            method: 'POST',
            body: formData
        });
        const result = await response.json();
        
        if (response.ok) {
            // Show success modal and redirect
            showSuccessRedirectModal();
        } else {
            showResult(result.error || 'An unknown error occurred.', 'error', 'result');
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
        }
    } catch (error) {
        showResult('Network error. Please try again.', 'error', 'result');
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
    }
    // --- END FIX ---
}

// --- NEW FUNCTION: Show success modal (for registration) ---
function showSuccessRedirectModal() {
    const modal = document.getElementById('success-modal');
    const countdownSpan = document.getElementById('redirect-countdown');
    if (!modal || !countdownSpan) return;

    modal.classList.remove('hidden');
    let countdown = 5;
    countdownSpan.textContent = countdown;

    const interval = setInterval(() => {
        countdown--;
        countdownSpan.textContent = countdown;
        if (countdown <= 0) {
            clearInterval(interval);
            window.location.href = '/'; // Redirect to homepage
        }
    }, 1000);
}


async function handleLogin(e) {
    e.preventDefault();
    const loginBtn = e.target.querySelector('#login-btn');
    const originalText = loginBtn.innerHTML;
    loginBtn.disabled = true;
    loginBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Logging in...';
    
    const formData = new FormData(e.target);
    const data = Object.fromEntries(formData.entries());
    
    try {
        const response = await fetch('/api/company/login', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
        const result = await response.json();
        
        if (response.ok) {
            showResult('Login successful! Redirecting...', 'success', 'login-result');
            setTimeout(() => {
                window.location.href = '/company-dashboard';
            }, 1000);
        } else {
            showResult(result.error || 'Invalid credentials.', 'error', 'login-result');
            loginBtn.disabled = false;
            loginBtn.innerHTML = originalText;
        }
    } catch (error) {
        showResult('Network error. Please try again.', 'error', 'login-result');
        loginBtn.disabled = false;
        loginBtn.innerHTML = originalText;
    }
}

/**
 * --- MODIFIED: showResult function to accept a target ID ---
 */
function showResult(message, type, targetElementId = 'result', timeout = 5000) {
    const resultDiv = document.getElementById(targetElementId);
    if (!resultDiv) return;

    if (!message || timeout === 0) {
        resultDiv.classList.add('hidden');
        resultDiv.innerHTML = '';
        return;
    }
    
    resultDiv.innerHTML = `
        <div class="${type === 'success' ? 'success-message' : 'error-message'}">
            <i class="fa-solid fa-${type === 'success' ? 'check' : 'exclamation-triangle'}"></i>
            ${message}
        </div>
    `;
    resultDiv.classList.remove('hidden');
    
    if (timeout > 0) {
        setTimeout(() => {
            resultDiv.classList.add('hidden');
            resultDiv.innerHTML = '';
        }, timeout);
    }
}

// Make removeFile globally accessible
window.removeFile = removeFile;


// --- NEW: FORGOT PASSWORD FUNCTIONS ---

async function handleSendOtp(e) {
    e.preventDefault();
    const sendBtn = document.getElementById('send-otp-btn');
    const originalText = sendBtn.innerHTML;
    sendBtn.disabled = true;
    sendBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Sending...';

    const usernameOrEmail = document.getElementById('username_or_email').value;
    
    try {
        const response = await fetch('/api/company/forgot-password', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ "username_or_email": usernameOrEmail })
        });
        const result = await response.json();

        if (response.ok) {
            showResult(result.message, 'success', 'otp-send-result', 10000);
            // Switch to Verify OTP step
            document.getElementById('send-otp-step').classList.add('hidden');
            document.getElementById('verify-otp-step').classList.remove('hidden');
        } else {
            showResult(result.error || 'Failed to send OTP.', 'error', 'otp-send-result');
            sendBtn.disabled = false;
            sendBtn.innerHTML = originalText;
        }
    } catch (error) {
        showResult('Network error. Please try again.', 'error', 'otp-send-result');
        sendBtn.disabled = false;
        sendBtn.innerHTML = originalText;
    }
}

async function handleVerifyOtp(e) {
    e.preventDefault();
    const verifyBtn = document.getElementById('verify-otp-btn');
    const originalText = verifyBtn.innerHTML;
    verifyBtn.disabled = true;
    verifyBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Verifying...';

    // We need to send the username/email again for context
    const usernameOrEmail = document.getElementById('username_or_email').value;
    const otp = document.getElementById('otp_code').value;

    try {
        const response = await fetch('/api/company/verify-otp', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ 
                "username_or_email": usernameOrEmail,
                "otp": otp 
            })
        });
        const result = await response.json();

        if (response.ok) {
            showResult(result.message, 'success', 'otp-verify-result', 10000);
            verifyBtn.innerHTML = '<i class="fa-solid fa-check"></i> Success!';
            // Close modal after 3 seconds
            setTimeout(() => {
                document.getElementById('forgot-password-modal').classList.add('hidden');
                resetModal();
            }, 3000);
        } else {
            showResult(result.error || 'Verification failed.', 'error', 'otp-verify-result');
            verifyBtn.disabled = false;
            verifyBtn.innerHTML = originalText;
        }
    } catch (error) {
        showResult('Network error. Please try again.', 'error', 'otp-verify-result');
        verifyBtn.disabled = false;
        verifyBtn.innerHTML = originalText;
    }
}

// Resets the modal to its original state
function resetModal() {
    document.getElementById('send-otp-step').classList.remove('hidden');
    document.getElementById('verify-otp-step').classList.add('hidden');
    
    document.getElementById('send-otp-form').reset();
    document.getElementById('verify-otp-form').reset();

    showResult('', 'success', 'otp-send-result', 0);
    showResult('', 'success', 'otp-verify-result', 0);

    const sendBtn = document.getElementById('send-otp-btn');
    sendBtn.disabled = false;
    sendBtn.innerHTML = '<i class="fa-solid fa-mobile-alt"></i> Send OTP';

    const verifyBtn = document.getElementById('verify-otp-btn');
    verifyBtn.disabled = false;
    verifyBtn.innerHTML = '<i class="fa-solid fa-check-circle"></i> Verify & Recover';
}