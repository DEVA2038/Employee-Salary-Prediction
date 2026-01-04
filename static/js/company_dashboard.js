// static/js/company_dashboard.js - ENHANCED VERSION

document.addEventListener('DOMContentLoaded', function() {
    checkSessionAndInitialize();
});

async function checkSessionAndInitialize() {
    try {
        const response = await fetch('/api/session/check');
        if (!response.ok) throw new Error('Session check failed');
        const sessionData = await response.json();
        
        if (sessionData.logged_in) {
            initializeDashboard(sessionData);
        } else {
            window.location.href = '/company-login';
        }
    } catch (error) {
        console.error('Session check failed:', error);
        showNotification('Session validation failed. Redirecting to login...', 'error');
        setTimeout(() => window.location.href = '/company-login', 2000);
    }
}

function initializeDashboard(sessionData) {
    document.getElementById('welcome-message').textContent = 'Welcome, User';
    document.getElementById('header-company-name').textContent = `Company: ${sessionData.company_name || 'N/A'}`;
    
    setupEventListeners();
    loadCompanyProfile();
    populateFormOptions();
    loadAnalyticsData(); // Load analytics immediately
    switchTab('predict');
}
function updateDashboardWithRealData() {
    // Force refresh all data
    loadCompanyProfile();
    loadAnalyticsData();
    
    // Show loading states
    document.getElementById('last-training').textContent = 'Loading...';
    document.getElementById('data-points').textContent = 'Loading...';
    document.getElementById('predictions-count').textContent = 'Loading...';
    document.getElementById('analytics-data-points').textContent = 'Loading...';
    document.getElementById('predictions-made').textContent = 'Loading...';
    document.getElementById('approval-date').textContent = 'Loading...';
}

function setupEventListeners() {
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', () => switchTab(btn.dataset.tab));
    });

    document.getElementById('predict-btn').addEventListener('click', makePrediction);
    document.getElementById('reset-btn').addEventListener('click', resetForm);
    
    // File upload area interactions
    const uploadArea = document.getElementById('upload-area');
    const fileInput = document.getElementById('dataset-file');
    
    if (uploadArea && fileInput) {
        uploadArea.addEventListener('click', () => fileInput.click());
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            if (e.dataTransfer.files.length) {
                fileInput.files = e.dataTransfer.files;
                updateFileUploadDisplay();
            }
        });
        fileInput.addEventListener('change', updateFileUploadDisplay);
    }
}

function updateFileUploadDisplay() {
    const fileInput = document.getElementById('dataset-file');
    const uploadArea = document.getElementById('upload-area');
    
    if (fileInput.files.length > 0) {
        const file = fileInput.files[0];
        uploadArea.innerHTML = `
            <div class="file-upload-icon">
                <i class="fa-solid fa-file-check"></i>
            </div>
            <div class="file-upload-text">
                <h4>${file.name}</h4>
                <p>${(file.size / 1024 / 1024).toFixed(2)} MB</p>
            </div>
            <button type="button" class="btn btn-outline" onclick="clearFileSelection()">
                <i class="fa-solid fa-times"></i> Change File
            </button>
        `;
    }
}

function clearFileSelection() {
    const fileInput = document.getElementById('dataset-file');
    if (fileInput) fileInput.value = '';
    const uploadArea = document.getElementById('upload-area');
    // Restore default area UI
    if (uploadArea) {
        uploadArea.innerHTML = `
            <div class="file-upload-icon">
                <i class="fa-solid fa-file-csv"></i>
            </div>
            <div class="file-upload-text">
                <h4>Upload New Dataset</h4>
                <p>Drag & drop your CSV file or click to browse</p>
            </div>
        `;
    }
}

function switchTab(tabId) {
    document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));

    const tabEl = document.getElementById(`${tabId}-tab`);
    if (tabEl) tabEl.classList.add('active');
    const navBtn = document.querySelector(`.nav-btn[data-tab='${tabId}']`);
    if (navBtn) navBtn.classList.add('active');

    if (tabId === 'analytics') {
        loadAnalyticsData();
    }
}

async function populateFormOptions() {
    try {
        showNotification('Loading form options from your company dataset...', 'info');
        showFormLoadingState(true);

        const response = await fetch('/api/company/options');
        
        if (!response.ok) {
            throw new Error(`Failed to load options: ${response.status}`);
        }
        
        const options = await response.json();
        
        if (!options.categorical) {
            throw new Error('Invalid options format received');
        }

        const categoricalFields = ['gender', 'role', 'sector', 'company', 'department', 'education'];
        
        for (const field of categoricalFields) {
            const select = document.getElementById(field);
            if (select && options.categorical[field]) {
                select.innerHTML = '';
                
                const placeholder = document.createElement('option');
                placeholder.value = '';
                placeholder.textContent = `Select ${field.charAt(0).toUpperCase() + field.slice(1)}`;
                placeholder.disabled = true;
                placeholder.selected = true;
                select.appendChild(placeholder);

                options.categorical[field].forEach(value => {
                    if (value && value.trim() !== '') {
                        const option = document.createElement('option');
                        option.value = value;
                        option.textContent = formatOptionText(value);
                        select.appendChild(option);
                    }
                });
            }
        }

        if (options.numeric_meta) {
            const numericFields = ['age', 'experience'];
            numericFields.forEach(field => {
                const input = document.getElementById(field);
                if (input && options.numeric_meta[field]) {
                    const meta = options.numeric_meta[field];
                    input.min = meta.min;
                    input.max = meta.max;
                    input.step = meta.step || 1;
                    input.placeholder = `Range: ${meta.min}-${meta.max}`;
                }
            });
        }

        updateFeaturesList(options);
        
        showNotification('Form options loaded successfully!', 'success');
        showFormLoadingState(false);

    } catch (error) {
        console.error('Error loading form options:', error);
        showNotification('Using default form options.', 'info');
        loadDefaultOptions();
        showFormLoadingState(false);
    }
}

function formatOptionText(value) {
    if (!value) return value;
    return value.split(' ').map(word => {
        if (word.length > 0) {
            return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
        }
        return word;
    }).join(' ');
}

function updateFeaturesList(options) {
    const featuresGrid = document.getElementById('model-features-grid');
    if (!featuresGrid) return;
    
    featuresGrid.innerHTML = '';
    
    const fields = ['age', 'experience', 'gender', 'role', 'sector', 'company', 'department', 'education'];
    
    fields.forEach(field => {
        const description = options.field_descriptions?.[field] || `Employee ${field} information`;
        
        const featureItem = document.createElement('div');
        featureItem.className = 'feature-item';
        featureItem.innerHTML = `
            <i class="fa-solid fa-check"></i>
            <div class="feature-content">
                <strong class="feature-name">${formatOptionText(field)}</strong>
                <span class="feature-description">${description}</span>
            </div>
        `;
        featuresGrid.appendChild(featureItem);
    });
}

function showFormLoadingState(show) {
    const loadingElement = document.getElementById('options-loading');
    const formElement = document.getElementById('predict-form');
    
    if (loadingElement) {
        loadingElement.classList.toggle('hidden', !show);
    }
    if (formElement) {
        formElement.style.opacity = show ? '0.6' : '1';
    }
}

function loadDefaultOptions() {
    const defaultOptions = {
        gender: ['Male', 'Female', 'Other'],
        role: ['Software Engineer', 'Data Scientist', 'Product Manager', 'HR Manager', 'Sales Executive'],
        sector: ['IT', 'Finance', 'Healthcare', 'Education', 'Manufacturing'],
        company: ['Private', 'Government', 'Startup', 'MNC'],
        department: ['Engineering', 'Sales', 'Marketing', 'HR', 'Finance'],
        education: ["Bachelor's", "Master's", "PhD", "Diploma", "High School"]
    };
    
    for (const [field, values] of Object.entries(defaultOptions)) {
        const select = document.getElementById(field);
        if (select) {
            select.innerHTML = `<option value="">Select ${field.charAt(0).toUpperCase() + field.slice(1)}</option>`;
            values.forEach(value => {
                const option = document.createElement('option');
                option.value = value;
                option.textContent = value;
                select.appendChild(option);
            });
        }
    }
}
async function loadCompanyProfile() {
    try {
        console.log("🔄 Loading company profile...");
        
        const response = await fetch('/api/company/profile');
        
        if (!response.ok) {
            console.error(`❌ Profile API error: ${response.status}`);
            if (response.status === 401) {
                window.location.href = '/company-login';
                return;
            }
            throw new Error(`Failed to load profile: ${response.status}`);
        }
        
        const profile = await response.json();
        console.log("✅ Profile data received:", profile);

        // Update welcome message
        if (profile.username) {
            document.getElementById('welcome-message').textContent = `Welcome, ${profile.username}`;
        }

        // Update profile tab content - REPLACE the loading placeholder
        const profileContent = document.getElementById('profile-content');
        if (profileContent) {
            profileContent.innerHTML = `
                <div class="profile-item">
                    <span class="profile-label">Company Name:</span>
                    <span class="profile-value">${escapeHtml(profile.company_name)}</span>
                </div>
                <div class="profile-item">
                    <span class="profile-label">Contact Person:</span>
                    <span class="profile-value">${escapeHtml(profile.contact_person)}</span>
                </div>
                <div class="profile-item">
                    <span class="profile-label">Email:</span>
                    <span class="profile-value">${escapeHtml(profile.email)}</span>
                </div>
                <div class="profile-item">
                    <span class="profile-label">Phone:</span>
                    <span class="profile-value">${escapeHtml(profile.phone)}</span>
                </div>
                <div class="profile-item">
                    <span class="profile-label">Status:</span>
                    <span class="profile-value">
                        <span class="status-badge status-${profile.status}">${profile.status.toUpperCase()}</span>
                    </span>
                </div>
                <div class="profile-item">
                    <span class="profile-label">Approval Date:</span>
                    <span class="profile-value">${profile.approved_at ? new Date(profile.approved_at).toLocaleDateString() : 'N/A'}</span>
                </div>
                <div class="profile-item">
                    <span class="profile-label">Username:</span>
                    <span class="profile-value">${escapeHtml(profile.username)}</span>
                </div>
            `;
        }

        // Update model information in profile section
        if (profile.model_accuracy) {
            document.getElementById('model-accuracy').textContent = profile.model_accuracy;
            document.getElementById('profile-accuracy').textContent = profile.model_accuracy;
            document.getElementById('accuracy-stat').textContent = profile.model_accuracy;
        }

        // Update additional profile information
        updateProfileFields(profile);

        // Update header company name
        document.getElementById('header-company-name').textContent = `Company: ${profile.company_name}`;

        console.log("✅ Company profile loaded successfully");

    } catch (error) {
        console.error('❌ Failed to load company profile:', error);
        showNotification('Error loading company profile: ' + error.message, 'error');
        
        // Set default values and show error state
        setDefaultProfileValues();
    }
}

function updateProfileFields(profile) {
    // Helper function to safely update fields
    const fields = {
        'last-training': profile.last_training || 'Never',
        'data-points': profile.data_points ? profile.data_points.toLocaleString() : '0',
        'predictions-count': profile.predictions_count ? profile.predictions_count.toLocaleString() : '0',
        'training-data': profile.data_points ? `${profile.data_points.toLocaleString()} records` : '0 records',
        'last-training-predict': profile.last_training || 'Never'
    };

    for (const [fieldId, value] of Object.entries(fields)) {
        const element = document.getElementById(fieldId);
        if (element) {
            element.textContent = value;
        }
    }
}

function setDefaultProfileValues() {
    // Set sensible defaults when profile loading fails
    const defaults = {
        'last-training': 'Never',
        'data-points': '0',
        'predictions-count': '0',
        'training-data': '0 records',
        'last-training-predict': 'Never',
        'profile-accuracy': 'N/A',
        'model-accuracy': 'N/A',
        'accuracy-stat': 'N/A'
    };

    for (const [fieldId, value] of Object.entries(defaults)) {
        const element = document.getElementById(fieldId);
        if (element) {
            element.textContent = value;
        }
    }

    // Also update the profile content area to show error state
    const profileContent = document.getElementById('profile-content');
    if (profileContent) {
        profileContent.innerHTML = `
            <div class="error-state">
                <i class="fa-solid fa-exclamation-triangle"></i>
                <p>Unable to load company profile. Please try refreshing the page.</p>
            </div>
        `;
    }
}

// Utility function to prevent XSS
function escapeHtml(unsafe) {
    if (unsafe === null || unsafe === undefined) return '';
    return unsafe.toString()
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
async function loadAnalyticsData() {
    try {
        const response = await fetch('/api/company/analytics');
        if (!response.ok) throw new Error('Failed to load analytics');
        const analytics = await response.json();

        // Update analytics cards
        document.getElementById('analytics-data-points').textContent = analytics.data_points.toLocaleString();
        document.getElementById('predictions-made').textContent = analytics.predictions_count.toLocaleString();
        document.getElementById('approval-date').textContent = analytics.days_active;
        document.getElementById('accuracy-stat').textContent = analytics.model_accuracy ? `${analytics.model_accuracy}%` : '0%';

        // Update model details
        if (analytics.model_details) {
            document.getElementById('model-type').textContent = analytics.model_details.type || 'Random Forest Regressor';
            document.getElementById('model-algorithm').textContent = analytics.model_details.algorithm || 'Ensemble Learning';
            document.getElementById('model-features').textContent = analytics.model_details.features_count || '8';
            document.getElementById('training-method').textContent = analytics.model_details.training_method || 'Supervised Learning';
            document.getElementById('cross-validation').textContent = analytics.model_details.cross_validation || '5-fold';
            document.getElementById('hyperparameters').textContent = analytics.model_details.hyperparameters || 'Optimized';
        }

        // Also update the profile accuracy if it's different
        if (analytics.model_accuracy) {
            document.getElementById('profile-accuracy').textContent = `${analytics.model_accuracy}%`;
        }

    } catch (error) {
        console.error('Failed to load analytics:', error);
        showNotification('Error loading analytics data', 'error');
        
        // Set default values
        document.getElementById('analytics-data-points').textContent = '0';
        document.getElementById('predictions-made').textContent = '0';
        document.getElementById('approval-date').textContent = '0';
        document.getElementById('accuracy-stat').textContent = '0%';
    }
}

async function makePrediction() {
    const form = document.getElementById('predict-form');
    const predictBtn = document.getElementById('predict-btn');
    
    if (!form.checkValidity()) {
        form.reportValidity();
        showNotification('Please fill all fields with valid values.', 'warning');
        return;
    }

    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());
    data.age = parseFloat(data.age);
    data.experience = parseFloat(data.experience);

    predictBtn.disabled = true;
    predictBtn.innerHTML = '<span class="spinner"></span> Predicting...';

    try {
        const response = await fetch('/api/company/predict', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            if (response.status === 401) window.location.href = '/company-login';
            const errData = await response.json();
            throw new Error(errData.error || 'Prediction failed');
        }
        
        const result = await response.json();
        displayPredictionResult(result);
        showNotification('Prediction completed successfully!', 'success');

        // Refresh analytics to update predictions count
        loadAnalyticsData();

    } catch (error) {
        console.error('Prediction error:', error);
        showNotification(error.message, 'error');
    } finally {
        predictBtn.disabled = false;
        predictBtn.innerHTML = '<i class="fa-solid fa-bolt"></i> Predict Salary';
    }
}

function displayPredictionResult(result) {
    const resultDiv = document.getElementById('prediction-result');
    const salaryAmount = document.getElementById('salary-amount');
    const resultCompany = document.getElementById('result-company');
    const resultAccuracy = document.getElementById('result-accuracy');
    
    const formattedSalary = new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR',
        maximumFractionDigits: 0
    }).format(result.predicted_salary);

    salaryAmount.textContent = formattedSalary;
    resultCompany.textContent = result.company_name;
    resultAccuracy.textContent = `${(result.model_accuracy * 100).toFixed(1)}%`;
    
    resultDiv.classList.remove('hidden');
    resultDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function resetForm() {
    document.getElementById('predict-form').reset();
    document.getElementById('prediction-result').classList.add('hidden');
    showNotification('Form has been reset', 'info');
}

// Settings Functions
async function changePassword() {
    const currentPassword = document.getElementById('current-password').value;
    const newPassword = document.getElementById('new-password').value;
    const confirmPassword = document.getElementById('confirm-password').value;

    if (!currentPassword || !newPassword || !confirmPassword) {
        showNotification('Please fill all password fields.', 'warning');
        return;
    }

    if (newPassword !== confirmPassword) {
        showNotification('New passwords do not match.', 'error');
        return;
    }

    if (newPassword.length < 6) {
        showNotification('Password must be at least 6 characters long.', 'error');
        return;
    }

    try {
        const response = await fetch('/api/company/change-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                current_password: currentPassword,
                new_password: newPassword
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Password change failed');
        }

        const result = await response.json();
        showNotification(result.message || 'Password changed successfully!', 'success');
        
        // Clear password fields
        document.getElementById('current-password').value = '';
        document.getElementById('new-password').value = '';
        document.getElementById('confirm-password').value = '';

    } catch (error) {
        showNotification(error.message, 'error');
    }
}

async function uploadAndRetrain() {
    const fileInput = document.getElementById('dataset-file');
    if (!fileInput || !fileInput.files.length) {
        showNotification('Please choose a CSV file to upload.', 'warning');
        return;
    }

    const file = fileInput.files[0];
    if (!file.name.toLowerCase().endsWith('.csv')) {
        showNotification('Only CSV files are allowed.', 'warning');
        return;
    }

    const formData = new FormData();
    formData.append('dataset', file);

    const progressContainer = document.getElementById('upload-progress');
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    
    progressContainer.classList.remove('hidden');
    progressFill.style.width = '0%';
    progressText.textContent = 'Uploading...';

    try {
        const response = await fetch('/api/company/retrain', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.error || 'Retraining failed');
        }

        // Simulate progress
        let progress = 0;
        const progressInterval = setInterval(() => {
            progress += 10;
            progressFill.style.width = `${progress}%`;
            progressText.textContent = `Uploading... ${progress}%`;
            
            if (progress >= 100) {
                clearInterval(progressInterval);
                progressText.textContent = 'Processing data and retraining model...';
            }
        }, 200);

        const res = await response.json();
        clearInterval(progressInterval);
        progressFill.style.width = '100%';
        progressText.textContent = 'Complete!';

        showNotification(res.message || 'Model retrained successfully!', 'success');
        
        setTimeout(() => {
            progressContainer.classList.add('hidden');
            clearFileSelection();
        }, 2000);
        
        // Refresh all data
        await loadCompanyProfile();
        await populateFormOptions();
        await loadAnalyticsData();
        
    } catch (error) {
        document.getElementById('upload-progress').classList.add('hidden');
        showNotification(error.message, 'error');
    }
}

// OTP Deletion Functions (frontend)
let otpTimer;
let otpExpiryTime;

async function requestAccountDeletion() {
    // Confirm user intent first
    if (!confirm('Are you sure you want to delete your account? This action is PERMANENT and cannot be undone.')) {
        return;
    }
    
    const confirmation = prompt('Type "DELETE" to confirm account deletion:');
    if (confirmation !== 'DELETE') {
        showNotification('Account deletion cancelled.', 'info');
        return;
    }
    
    try {
        showNotification('Requesting OTP for account deletion...', 'info');
        
        const response = await fetch('/api/company/request-delete-otp', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        if (!response.ok) {
            const error = await response.json().catch(()=>({error:'Failed to request OTP'}));
            throw new Error(error.error || 'Failed to request OTP');
        }
        
        const result = await response.json();
        // If email couldn't be sent server-side, result may include a warning.
        showNotification(result.message || 'OTP requested. Check your email.', 'success');
        
        // Show OTP modal
        showOtpModal();
        startOtpTimer(5 * 60); // 5 minutes
        
    } catch (error) {
        showNotification(error.message, 'error');
    }
}

function showOtpModal() {
    const modal = document.getElementById('otp-modal');
    if (!modal) return;
    modal.classList.remove('hidden');
    modal.setAttribute('aria-hidden', 'false');
    const otpInput = document.getElementById('otp-input');
    if (otpInput) otpInput.value = '';
    const status = document.getElementById('otp-status');
    if (status) status.classList.add('hidden');
    document.getElementById('timer-countdown').textContent = '05:00';
    document.body.style.overflow = 'hidden'; // Prevent page scroll while modal is open
}

function closeOtpModal() {
    const modal = document.getElementById('otp-modal');
    if (!modal) return;
    modal.classList.add('hidden');
    modal.setAttribute('aria-hidden', 'true');
    clearInterval(otpTimer);
    document.body.style.overflow = ''; // restore scroll
}

function startOtpTimer(seconds) {
    clearInterval(otpTimer);
    otpExpiryTime = Date.now() + seconds * 1000;
    
    otpTimer = setInterval(() => {
        const now = Date.now();
        const remaining = Math.max(0, otpExpiryTime - now);
        
        if (remaining <= 0) {
            clearInterval(otpTimer);
            document.getElementById('timer-countdown').textContent = 'Expired';
            const verifyBtn = document.getElementById('verify-otp-btn');
            if (verifyBtn) verifyBtn.disabled = true;
            showOtpStatus('OTP has expired. Please request a new one.', 'error');
            return;
        }
        
        const minutes = Math.floor(remaining / 60000);
        const secs = Math.floor((remaining % 60000) / 1000);
        document.getElementById('timer-countdown').textContent = 
            `${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }, 1000);
}

function showOtpStatus(message, type = 'info') {
    const statusDiv = document.getElementById('otp-status');
    if (!statusDiv) return;
    statusDiv.className = `${type === 'error' ? 'error-message' : 'success-message'}`;
    statusDiv.innerHTML = `
        <i class="fa-solid fa-${type === 'error' ? 'exclamation-circle' : 'check-circle'}"></i>
        ${message}
    `;
    statusDiv.classList.remove('hidden');
}

async function verifyDeleteOtp() {
    const otpInput = document.getElementById('otp-input');
    if (!otpInput) return;
    const otp = otpInput.value.trim();
    
    if (!otp || otp.length !== 6) {
        showOtpStatus('Please enter a valid 6-digit OTP', 'error');
        return;
    }
    
    const verifyBtn = document.getElementById('verify-otp-btn');
    if (verifyBtn) {
        verifyBtn.disabled = true;
        verifyBtn.innerHTML = '<span class="spinner"></span> Verifying...';
    }
    
    try {
        const response = await fetch('/api/company/verify-delete-otp', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ otp: otp })
        });
        
        if (!response.ok) {
            const error = await response.json().catch(()=>({error:'OTP verification failed'}));
            throw new Error(error.error || 'OTP verification failed');
        }
        
        const result = await response.json();
        
        showNotification(result.message || 'Account deleted successfully!', 'success');
        
        // Close modal and redirect after delay
        closeOtpModal();
        
        setTimeout(() => {
            if (result.redirect_url) {
                window.location.href = result.redirect_url;
            } else {
                window.location.href = '/company-login';
            }
        }, 1800);
        
    } catch (error) {
        showOtpStatus(error.message, 'error');
        if (verifyBtn) {
            verifyBtn.disabled = false;
            verifyBtn.innerHTML = '<i class="fa-solid fa-trash"></i> Verify & Delete Account';
        }
    }
}

async function resendDeleteOtp() {
    try {
        const response = await fetch('/api/company/request-delete-otp', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        if (!response.ok) {
            const error = await response.json().catch(()=>({error:'Failed to resend OTP'}));
            throw new Error(error.error || 'Failed to resend OTP');
        }
        
        const result = await response.json();
        showOtpStatus(result.message || 'New OTP sent successfully!', 'success');
        
        // Restart timer
        startOtpTimer(5 * 60);
        
    } catch (error) {
        showOtpStatus(error.message, 'error');
    }
}
function logout() {
    // Show a small notification or change button state if desired
    showNotification('Logging out...', 'info');
    
    // Redirect to the logout route handled by Flask
    // using .replace() prevents the user from clicking "Back" to return
    window.location.replace('/company-logout');
}

// Add OTP modal styles to company.css (if not already present) were appended server-side in earlier code.
// Update the window functions to include OTP functions
window.requestAccountDeletion = requestAccountDeletion;
window.closeOtpModal = closeOtpModal;
window.verifyDeleteOtp = verifyDeleteOtp;
window.resendDeleteOtp = resendDeleteOtp;
// Make functions globally available
window.logout = logout;
window.resetForm = resetForm;
window.downloadResult = function() { 
    showNotification('Download feature coming soon!', 'info');
};
window.clearFileSelection = clearFileSelection;
window.changePassword = changePassword;
window.uploadAndRetrain = uploadAndRetrain;
window.requestAccountDeletion = requestAccountDeletion;

// notification helpers
function showNotification(message, type = 'info') {
    document.querySelectorAll('.notification').forEach(n => n.remove());
    
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <i class="fa-solid fa-${getNotificationIcon(type)}"></i>
            <span>${message}</span>
        </div>
        <button class="notification-close" onclick="this.parentElement.remove()">
            <i class="fa-solid fa-times"></i>
        </button>
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, 5000);
}

function getNotificationIcon(type) {
    const icons = {
        success: 'check-circle',
        error: 'exclamation-circle',
        warning: 'exclamation-triangle',
        info: 'info-circle'
    };
    return icons[type] || 'info-circle';
}