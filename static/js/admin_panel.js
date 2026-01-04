// static/js/admin_panel.js

// Global variable to store all requests to avoid re-fetching
let allCompanyRequests = [];
let approvalChartInstance = null;
let currentAdminUsername = "Admin";

// --- Initialization ---

document.addEventListener('DOMContentLoaded', async function() {
    const hasAccess = await checkAdminAccess();
    if (hasAccess) {
        setupNavigation();
        setupEventListeners();
        loadCompanyRequests(); // Initial data load
        loadAdminsList(); // Load admin list
        updateAdminInfo(); // Update admin username
        
        // Auto-refresh every 30 seconds
        setInterval(loadCompanyRequests, 30000);
    }
});

async function checkAdminAccess() {
    try {
        const response = await fetch('/api/admin/session');
        const data = await response.json();
        
        if (!data.logged_in) {
            window.location.href = '/admin-login';
            return false;
        }
        currentAdminUsername = data.username || "Admin";
        return true;
    } catch (error) {
        console.error('Session check failed:', error);
        window.location.href = '/admin-login';
        return false;
    }
}

function updateAdminInfo() {
    const adminUsernameEl = document.getElementById('admin-username');
    if (adminUsernameEl) {
        adminUsernameEl.textContent = currentAdminUsername;
    }
}

function setupEventListeners() {
    const refreshBtn = document.querySelector('[onclick="refreshRequests()"]');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', refreshRequests);
    }
    
    // Setup filter buttons
    document.querySelectorAll('.filter-bar .btn').forEach(button => {
        button.addEventListener('click', () => {
            // Update active state
            document.querySelectorAll('.filter-bar .btn').forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            
            // Filter the table
            const filter = button.dataset.filter;
            filterRequestsTable(filter);
        });
    });
    
    // Confirm delete input listener
    const confirmDeleteInput = document.getElementById('confirm-delete');
    if (confirmDeleteInput) {
        confirmDeleteInput.addEventListener('input', function() {
            const deleteBtn = document.getElementById('confirm-delete-btn');
            deleteBtn.disabled = this.value !== 'DELETE';
        });
    }
}

function setupNavigation() {
    const navLinks = document.querySelectorAll('.sidebar-nav .nav-link');
    const pageSections = document.querySelectorAll('.page-section');
    const pageTitle = document.getElementById('page-title');
    const pageSubtitle = document.getElementById('page-subtitle');
    
    // Update pageDetails object
const pageDetails = {
    'dashboard-page': { title: 'Dashboard', subtitle: 'System Overview & Statistics' },
    'requests-page': { title: 'Company Requests', subtitle: 'Manage pending, approved, and rejected requests' },
    'companies-page': { title: 'Approved Companies', subtitle: 'View all active companies using the product' },
    'analytics-page': { title: 'Analytics', subtitle: 'View top performing company analytics' },
    'admin-page': { title: 'Notifications', subtitle: 'Monitor inactive and low accuracy accounts' }
};

    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const pageId = link.dataset.page;
            
            // Update nav link active state
            navLinks.forEach(l => l.classList.remove('active'));
            link.classList.add('active');
            
            // Show/hide pages
            pageSections.forEach(section => {
                if (section.id === pageId) {
                    section.classList.remove('hidden');
                    
                    // Load specific data for certain pages
                    if (pageId === 'force-deletion-page') {
                        loadCompaniesForDeletion();
                    }
                } else {
                    section.classList.add('hidden');
                }
            });
            
            // Update header title and subtitle
            const details = pageDetails[pageId];
            if (details) {
                pageTitle.textContent = details.title;
                pageSubtitle.textContent = details.subtitle;
            }

            // Redraw chart if analytics page is shown (Chart.js fix)
            if (pageId === 'dashboard-page' && approvalChartInstance) {
                approvalChartInstance.resize();
            }
        });
    });
    
    // Set initial page based on hash or default to dashboard
    const initialPage = window.location.hash.substring(1) || 'dashboard';
    const initialLink = document.querySelector(`.nav-link[href="#${initialPage}"]`);
    if (initialLink) {
        initialLink.click();
    }
}


// --- Data Loading and Display ---

async function loadCompanyRequests() {
    const loadingElement = document.getElementById('loading-requests');
    const tableBody = document.getElementById('requests-body');
    
    try {
        loadingElement.classList.remove('hidden');
        
        const timestamp = new Date().getTime();
        const response = await fetch(`/api/admin/requests?t=${timestamp}`);
        
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            throw new Error('Server returned non-JSON response. API may be misconfigured.');
        }
        
        const requests = await response.json();
        if (!Array.isArray(requests)) {
            throw new Error('Invalid response format - expected array');
        }
        
        // Store globally
        allCompanyRequests = requests;
        
        // Populate all parts of the dashboard
        populateAllSections(allCompanyRequests);
        
    } catch (error) {
        console.error('Error loading requests:', error);
        tableBody.innerHTML = `
            <tr>
                <td colspan="5" style="text-align: center; color: var(--danger); padding: 2rem;">
                    <i class="fa-solid fa-exclamation-triangle"></i>
                    <div><strong>Failed to load requests</strong></div>
                    <div style="font-size: 0.875rem; opacity: 0.8;">${escapeHtml(error.message)}</div>
                    <button class="btn btn-outline" onclick="loadCompanyRequests()" style="margin-top: 1rem;">
                        <i class="fa-solid fa-refresh"></i> Try Again
                    </button>
                </td>
            </tr>
        `;
        resetStats();
    } finally {
        loadingElement.classList.add('hidden');
    }
}

function populateAllSections(requests) {
    // 1. Update Dashboard Stats
    updateStats(requests);
    
    // 2. Display Company Requests (with current filter)
    displayCompanyRequests(requests);
    
    // 3. Display Approved Companies
    displayApprovedCompanies(requests);
    
    // 4. Display Analytics
    displayAnalytics(requests);
}

function displayCompanyRequests(requests) {
    const tableBody = document.getElementById('requests-body');
    
    if (requests.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="6" style="text-align: center; color: var(--text-secondary); padding: 3rem;">
                    <i class="fa-solid fa-inbox" style="font-size: 2rem; opacity: 0.5;"></i>
                    <div>No Company Requests</div>
                </td>
            </tr>
        `;
        return;
    }
    
    tableBody.innerHTML = requests.map(request => `
        <tr data-request-id="${request.id}" data-status="${request.status}">
            <td>
                <div class="company-info">
                    <div class="company-name">${escapeHtml(request.company_name)}</div>
                    ${request.contact_person ? `<div class="contact-person">${escapeHtml(request.contact_person)}</div>` : ''}
                </div>
            </td>
            <td>
                <div class="contact-info">
                    ${request.phone ? `
                        <div class="phone-number">
                            <i class="fa-solid fa-phone"></i>
                            ${escapeHtml(request.phone)}
                        </div>
                    ` : '<div class="text-muted">No phone</div>'}
                </div>
            </td>
            <td>
                <div class="email-info">
                    <a href="mailto:${escapeHtml(request.email)}" class="email-link">
                        <i class="fa-solid fa-envelope"></i>
                        ${escapeHtml(request.email)}
                    </a>
                </div>
            </td>
            <td>
                <div class="date-info">
                    <div class="date">${new Date(request.created_at).toLocaleDateString()}</div>
                    <div class="time text-muted">${new Date(request.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</div>
                </div>
            </td>
            <td>
                ${getRequestStatusCell(request)}
            </td>
            <td>
                ${getRequestActionsCell(request)}
            </td>
        </tr>
    `).join('');
    
    // Apply the current filter
    const currentFilter = document.querySelector('.filter-bar .btn.active').dataset.filter;
    filterRequestsTable(currentFilter);
}

function getRequestStatusCell(request) {
    if (request.status === 'pending') {
        return `
            <span class="status-badge status-pending">
                <i class="fa-solid fa-clock"></i>
                PENDING
            </span>
        `;
    } else if (request.status === 'approved') {
        return `
            <span class="status-badge status-approved">
                <i class="fa-solid fa-check-circle"></i>
                APPROVED
            </span>
        `;
    } else if (request.status === 'rejected') {
        return `
            <span class="status-badge status-rejected">
                <i class="fa-solid fa-times-circle"></i>
                REJECTED
            </span>
        `;
    }
    return `<span class="status-badge">${request.status.toUpperCase()}</span>`;
}

function getRequestActionsCell(request) {
    if (request.status === 'pending') {
        return `
            <div class="action-buttons">
                <button class="btn btn-success btn-sm" onclick="approveRequest(${request.id})">
                    <i class="fa-solid fa-check"></i> Approve
                </button>
                <button class="btn btn-danger btn-sm" onclick="rejectRequest(${request.id})">
                    <i class="fa-solid fa-times"></i> Reject
                </button>
            </div>
        `;
    } else if (request.status === 'approved') {
        return `
            <div class="action-buttons">
                <span class="text-success">
                    <i class="fa-solid fa-check-circle"></i>
                    Approved on ${new Date(request.approved_at).toLocaleDateString()}
                </span>
            </div>
        `;
    } else if (request.status === 'rejected') {
        return `
            <div class="action-buttons">
                <span class="text-danger">
                    <i class="fa-solid fa-times-circle"></i>
                    Rejected
                </span>
            </div>
        `;
    }
    return '-';
}

function displayApprovedCompanies(requests) {
    const tableBody = document.getElementById('companies-body');
    const loadingElement = document.getElementById('loading-companies');
    loadingElement.classList.remove('hidden');
    
    const approvedCompanies = requests.filter(r => r.status === 'approved')
                                      .sort((a, b) => new Date(b.approved_at) - new Date(a.approved_at));
    
    if (approvedCompanies.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="7" style="text-align: center; color: var(--text-secondary); padding: 3rem;">
                    <i class="fa-solid fa-building-user" style="font-size: 2rem; opacity: 0.5;"></i>
                    <div>No Approved Companies Yet</div>
                </td>
            </tr>
        `;
        loadingElement.classList.add('hidden');
        return;
    }
    
    tableBody.innerHTML = approvedCompanies.map(company => `
        <tr class="company-row">
            <td class="company-name-cell">
                <div class="company-info">
                    <div class="company-name">${escapeHtml(company.company_name)}</div>
                </div>
            </td>
            <td><code>${escapeHtml(company.username)}</code></td>
            <td>
                <div>${escapeHtml(company.contact_person)}</div>
                <div class="text-muted">${escapeHtml(company.email)}</div>
            </td>
            <td>
                <div class="date-info">
                    <div class="date">${new Date(company.approved_at).toLocaleDateString()}</div>
                </div>
            </td>
            <td>${company.data_points || 'N/A'}</td>
            <td>${company.predictions_count || 0}</td>
            <td>
                <span class="accuracy-badge">
                    ${company.model_accuracy ? (company.model_accuracy * 100).toFixed(1) + '%' : 'N/A'}
                </span>
            </td>
        </tr>
    `).join('');
    
    loadingElement.classList.add('hidden');
}

function displayAnalytics(requests) {
    const approved = requests.filter(r => r.status === 'approved').length;
    const pending = requests.filter(r => r.status === 'pending').length;
    const rejected = requests.filter(r => r.status === 'rejected').length;

    // --- 1. Approval Rate Chart ---
    const ctx = document.getElementById('approval-chart').getContext('2d');
    if (approvalChartInstance) {
        approvalChartInstance.destroy();
    }
    approvalChartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Approved', 'Pending', 'Rejected'],
            datasets: [{
                data: [approved, pending, rejected],
                backgroundColor: [
                    'rgba(76, 201, 240, 0.7)', // success
                    'rgba(247, 37, 133, 0.7)', // warning
                    'rgba(230, 57, 70, 0.7)'  // danger
                ],
                borderColor: [
                    '#4cc9f0',
                    '#f72585',
                    '#e63946'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                }
            }
        }
    });

    // --- 2. Top Companies by Predictions ---
    const topCompaniesList = document.getElementById('top-companies-list');
    const topCompanies = requests
        .filter(r => r.status === 'approved' && r.predictions_count > 0)
        .sort((a, b) => b.predictions_count - a.predictions_count)
        .slice(0, 5); // Top 5

    if (topCompanies.length === 0) {
        topCompaniesList.innerHTML = `<p class="text-muted" style="padding: 1rem;">No prediction data available yet.</p>`;
    } else {
        topCompaniesList.innerHTML = topCompanies.map(company => `
            <div class="company-analytic-item">
                <span class="name">${escapeHtml(company.company_name)}</span>
                <span class="count">${company.predictions_count}</span>
            </div>
        `).join('');
    }

    // --- 3. Analytics Page Content ---
    const analyticsContent = document.getElementById('analytics-content');
    const totalPredictions = requests.reduce((acc, r) => acc + (r.predictions_count || 0), 0);
    const avgAccuracy = approved > 0 
        ? requests.filter(r => r.status === 'approved' && r.model_accuracy)
                  .reduce((acc, r) => acc + r.model_accuracy, 0) / approved
        : 0;

    analyticsContent.innerHTML = `
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-icon total"><i class="fa-solid fa-brain"></i></div>
                <div class="stat-content">
                    <div class="stat-number">${totalPredictions}</div>
                    <div class="stat-label">Total Predictions Made</div>
                </div>
            </div>
            <div class="stat-card">
                <div class="stat-icon approved"><i class="fa-solid fa-bullseye"></i></div>
                <div class="stat-content">
                    <div class="stat-number">${(avgAccuracy * 100).toFixed(1)}%</div>
                    <div class="stat-label">Avg. Model Accuracy</div>
                </div>
            </div>
        </div>
        <h3>Top Companies by Predictions</h3>
        <div id="top-companies-list-full" style="display: flex; flex-direction: column; gap: 1rem; margin-top: 1rem;">
            ${topCompanies.length > 0 ? topCompanies.map(c => `
                <div class="company-analytic-item">
                    <span class="name">${escapeHtml(c.company_name)}</span>
                    <span class="count">${c.predictions_count} predictions</span>
                </div>
            `).join('') : '<p class="text-muted">No prediction data.</p>'}
        </div>
    `;
}

// --- Table Filtering ---

function filterRequestsTable(filter) {
    const tableBody = document.getElementById('requests-body');
    const rows = tableBody.querySelectorAll('tr');
    
    rows.forEach(row => {
        if (filter === 'all') {
            row.classList.remove('hidden');
        } else {
            if (row.dataset.status === filter) {
                row.classList.remove('hidden');
            } else {
                row.classList.add('hidden');
            }
        }
    });
}

function searchCompanies() {
    const searchTerm = document.getElementById('company-search').value.toLowerCase();
    const rows = document.querySelectorAll('#companies-body .company-row');
    
    rows.forEach(row => {
        const companyName = row.querySelector('.company-name-cell .company-name').textContent.toLowerCase();
        if (companyName.includes(searchTerm)) {
            row.classList.remove('hidden');
        } else {
            row.classList.add('hidden');
        }
    });
}

function searchCompaniesForDeletion() {
    const searchTerm = document.getElementById('deletion-search').value.toLowerCase();
    const rows = document.querySelectorAll('#deletion-body .deletion-row');
    
    rows.forEach(row => {
        const companyName = row.querySelector('.company-name-cell .company-name').textContent.toLowerCase();
        if (companyName.includes(searchTerm)) {
            row.classList.remove('hidden');
        } else {
            row.classList.add('hidden');
        }
    });
}

// --- Stat Updates ---

function updateStats(requests) {
    const total = requests.length;
    const pending = requests.filter(r => r.status === 'pending').length;
    const approved = requests.filter(r => r.status === 'approved').length;
    const rejected = requests.filter(r => r.status === 'rejected').length;
    
    animateStat('total-requests', total);
    animateStat('pending-requests', pending);
    animateStat('approved-requests', approved);
    animateStat('rejected-requests', rejected);
    
    // Highlight pending card
    const pendingCard = document.querySelector('.stat-icon.pending').closest('.stat-card');
    if (pending > 0) {
        pendingCard.classList.add('pending');
    } else {
        pendingCard.classList.remove('pending');
    }
}

function animateStat(elementId, newValue) {
    const element = document.getElementById(elementId);
    if (!element) return;
    const currentValue = parseInt(element.textContent) || 0;
    
    if (currentValue !== newValue) {
        element.style.transform = 'scale(1.1)';
        element.style.color = 'var(--primary)';
        
        setTimeout(() => {
            element.textContent = newValue;
            element.style.transform = 'scale(1)';
            setTimeout(() => {
                element.style.color = '';
            }, 500);
        }, 300);
    } else {
        element.textContent = newValue;
    }
}

function resetStats() {
    animateStat('total-requests', 0);
    animateStat('pending-requests', 0);
    animateStat('approved-requests', 0);
    animateStat('rejected-requests', 0);
}


// --- Actions (Approve, Reject, Delete, etc.) ---

async function adminLogout() {
    try {
        await fetch('/api/admin/logout', { method: 'POST' });
        window.location.href = '/admin-login';
    } catch (error) {
        console.error('Logout error:', error);
        window.location.href = '/admin-login';
    }
}

async function approveRequest(requestId) {
    if (!confirm('Are you sure you want to approve this company request? This will train a custom model and send login credentials.')) {
        return;
    }
    
    // Find the approve button and disable it
    const row = document.querySelector(`tr[data-request-id="${requestId}"]`);
    if (row) {
        const approveBtn = row.querySelector('.btn-success');
        if (approveBtn) {
            approveBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Processing...';
            approveBtn.disabled = true;
        }
        
        // Also disable reject button
        const rejectBtn = row.querySelector('.btn-danger');
        if (rejectBtn) {
            rejectBtn.disabled = true;
        }
    }
    
    try {
        const response = await fetch(`/api/admin/approve/${requestId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showModal('Request Approved', `
                <div class="success-header">
                    <i class="fa-solid fa-check-circle"></i>
                    <h4>Company Approved Successfully</h4>
                </div>
                <p><strong>Generated Credentials:</strong></p>
                <div class="credential-display">
                    <div class="credential-item"><label>Username:</label> <code class="credential-value">${escapeHtml(result.username)}</code></div>
                    <div class="credential-item"><label>Password:</label> <code class="credential-value">${escapeHtml(result.password)}</code></div>
                    <div class="credential-item"><label>Model Accuracy:</label> <strong class="accuracy-highlight">${(result.model_accuracy * 100).toFixed(1)}%</strong></div>
                </div>
                <div class="success-footer">
                    <i class="fa-solid fa-envelope"></i>
                    <span>Credentials sent to the company's email.</span>
                </div>
            `);
            loadCompanyRequests(); // Refresh all data
        } else {
            throw new Error(result.error || 'Approval failed');
        }
    } catch (error) {
        showModal('Approval Failed', `
            <div class="error-header">
                <i class="fa-solid fa-exclamation-triangle"></i>
                <h4>Approval Failed</h4>
            </div>
            <p>${escapeHtml(error.message)}</p>
        `);
        // Re-enable buttons if failed
        const row = document.querySelector(`tr[data-request-id="${requestId}"]`);
        if (row) {
            const approveBtn = row.querySelector('.btn-success');
            if (approveBtn) {
                approveBtn.innerHTML = '<i class="fa-solid fa-check"></i> Approve';
                approveBtn.disabled = false;
            }
            const rejectBtn = row.querySelector('.btn-danger');
            if (rejectBtn) {
                rejectBtn.disabled = false;
            }
        }
    }
}

async function rejectRequest(requestId) {
    if (!confirm('Are you sure you want to reject this company request?')) {
        return;
    }
    
    // Find the reject button and disable it
    const row = document.querySelector(`tr[data-request-id="${requestId}"]`);
    if (row) {
        const rejectBtn = row.querySelector('.btn-danger');
        if (rejectBtn) {
            rejectBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Rejecting...';
            rejectBtn.disabled = true;
        }
        
        // Also disable approve button
        const approveBtn = row.querySelector('.btn-success');
        if (approveBtn) {
            approveBtn.disabled = true;
        }
    }

    try {
        const response = await fetch(`/api/admin/reject/${requestId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showModal('Request Rejected', `
                <div class="info-header">
                    <i class="fa-solid fa-info-circle"></i>
                    <h4>Request Rejected</h4>
                </div>
                <p>Company request has been rejected successfully.</p>
            `);
            loadCompanyRequests(); // Refresh all data
        } else {
            throw new Error(result.error || 'Rejection failed');
        }
    } catch (error) {
        showModal('Rejection Failed', `
            <div class="error-header">
                <i class="fa-solid fa-exclamation-triangle"></i>
                <h4>Rejection Failed</h4>
            </div>
            <p>${escapeHtml(error.message)}</p>
        `);
        // Re-enable buttons if failed
        const row = document.querySelector(`tr[data-request-id="${requestId}"]`);
        if (row) {
            const rejectBtn = row.querySelector('.btn-danger');
            if (rejectBtn) {
                rejectBtn.innerHTML = '<i class="fa-solid fa-times"></i> Reject';
                rejectBtn.disabled = false;
            }
            const approveBtn = row.querySelector('.btn-success');
            if (approveBtn) {
                approveBtn.disabled = false;
            }
        }
    }
}

// --- Admin Management Functions ---

async function loadAdminsList() {
    try {
        const response = await fetch('/api/admin/list');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const admins = await response.json();
        
        const tableBody = document.getElementById('admins-body');
        if (!admins || admins.length === 0) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="6" style="text-align: center; color: var(--text-secondary); padding: 2rem;">
                        <i class="fa-solid fa-users" style="font-size: 2rem; opacity: 0.5;"></i>
                        <div>No additional admins found</div>
                    </td>
                </tr>
            `;
            return;
        }
        
        tableBody.innerHTML = admins.map(admin => `
            <tr>
                <td>${escapeHtml(admin.full_name)}</td>
                <td><code>${escapeHtml(admin.username)}</code></td>
                <td>${escapeHtml(admin.email)}</td>
                <td>${new Date(admin.created_at).toLocaleDateString()}</td>
                <td>
                    <span class="status-badge status-${admin.is_active ? 'approved' : 'rejected'}">
                        ${admin.is_active ? 'ACTIVE' : 'INACTIVE'}
                    </span>
                </td>
                <td>
                    <button class="btn btn-danger btn-sm" onclick="deleteAdmin(${admin.id}, '${escapeHtml(admin.full_name)}')" title="Delete Admin">
                        <i class="fa-solid fa-trash"></i> Delete
                    </button>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Error loading admins:', error);
        const tableBody = document.getElementById('admins-body');
        tableBody.innerHTML = `
            <tr>
                <td colspan="6" style="text-align: center; color: var(--danger); padding: 2rem;">
                    <i class="fa-solid fa-exclamation-triangle"></i>
                    <div><strong>Failed to load admins</strong></div>
                    <div style="font-size: 0.875rem; opacity: 0.8;">${escapeHtml(error.message)}</div>
                    <button class="btn btn-outline" onclick="loadAdminsList()" style="margin-top: 1rem;">
                        <i class="fa-solid fa-refresh"></i> Try Again
                    </button>
                </td>
            </tr>
        `;
    }
}

function showAddAdminModal() {
    const modal = document.getElementById('add-admin-modal');
    const form = document.getElementById('add-admin-form');
    const credentialsDisplay = document.getElementById('admin-credentials-display');
    
    // Reset form and hide credentials
    form.reset();
    form.classList.remove('hidden');
    credentialsDisplay.classList.add('hidden');
    
    // Reset create button
    const createBtn = document.getElementById('create-admin-btn');
    createBtn.innerHTML = '<i class="fa-solid fa-user-plus"></i> Create Admin';
    createBtn.disabled = false;
    
    modal.classList.remove('hidden');
}

function closeAddAdminModal() {
    document.getElementById('add-admin-modal').classList.add('hidden');
}

async function createNewAdmin() {
    const fullName = document.getElementById('admin-fullname').value.trim();
    const email = document.getElementById('admin-email').value.trim();
    const createBtn = document.getElementById('create-admin-btn');
    
    if (!fullName || !email) {
        showModal('Validation Error', 'Please fill in all required fields.');
        return;
    }
    
    // Validate email format
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        showModal('Validation Error', 'Please enter a valid email address.');
        return;
    }
    
    // Disable button and show loading
    const originalText = createBtn.innerHTML;
    createBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Creating...';
    createBtn.disabled = true;
    
    try {
        const response = await fetch('/api/admin/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ full_name: fullName, email: email })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            // Show credentials
            const form = document.getElementById('add-admin-form');
            const credentialsDisplay = document.getElementById('admin-credentials-display');
            
            form.classList.add('hidden');
            credentialsDisplay.classList.remove('hidden');
            
            document.getElementById('generated-username').textContent = result.username;
            document.getElementById('generated-password').textContent = result.password;
            
            // Update create button
            createBtn.innerHTML = '<i class="fa-solid fa-check"></i> Done';
            createBtn.disabled = true;
            
            // Reload admin list after 3 seconds
            setTimeout(() => {
                loadAdminsList();
                createBtn.innerHTML = originalText;
                createBtn.disabled = false;
            }, 3000);
        } else {
            throw new Error(result.error || 'Failed to create admin');
        }
    } catch (error) {
        showModal('Admin Creation Failed', `
            <div class="error-header">
                <i class="fa-solid fa-exclamation-triangle"></i>
                <h4>Failed to Create Admin</h4>
            </div>
            <p>${escapeHtml(error.message)}</p>
        `);
        createBtn.innerHTML = originalText;
        createBtn.disabled = false;
    }
}

async function deleteAdmin(adminId, adminName) {
    if (!confirm(`Are you sure you want to delete admin "${adminName}"?`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/admin/delete/${adminId}`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showModal('Admin Deleted', `
                <div class="success-header">
                    <i class="fa-solid fa-trash"></i>
                    <h4>Admin Deleted Successfully</h4>
                </div>
                <p>Admin "${escapeHtml(adminName)}" has been deleted.</p>
            `);
            loadAdminsList();
        } else {
            throw new Error(result.error || 'Failed to delete admin');
        }
    } catch (error) {
        showModal('Deletion Failed', `
            <div class="error-header">
                <i class="fa-solid fa-exclamation-triangle"></i>
                <h4>Failed to Delete Admin</h4>
            </div>
            <p>${escapeHtml(error.message)}</p>
        `);
    }
}

// --- Force Deletion Functions ---

async function loadCompaniesForDeletion() {
    const loadingElement = document.getElementById('loading-deletion');
    const tableBody = document.getElementById('deletion-body');
    
    try {
        loadingElement.classList.remove('hidden');
        
        // Use the existing allCompanyRequests data that we already have
        const approvedCompanies = allCompanyRequests.filter(r => r.status === 'approved');
        
        if (approvedCompanies.length === 0) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="7" style="text-align: center; color: var(--text-secondary); padding: 3rem;">
                        <i class="fa-solid fa-building-user" style="font-size: 2rem; opacity: 0.5;"></i>
                        <div>No companies available for deletion</div>
                    </td>
                </tr>
            `;
            loadingElement.classList.add('hidden');
            return;
        }
        
        tableBody.innerHTML = approvedCompanies.map(company => `
            <tr class="deletion-row" data-company-id="${company.id}">
                <td class="company-name-cell">
                    <div class="company-info">
                        <div class="company-name">${escapeHtml(company.company_name)}</div>
                    </div>
                </td>
                <td><code>${escapeHtml(company.username || 'N/A')}</code></td>
                <td>${escapeHtml(company.contact_person)}</td>
                <td>${escapeHtml(company.email)}</td>
                <td>${company.data_points || 0}</td>
                <td>${company.predictions_count || 0}</td>
                <td>
                    <button class="btn btn-danger btn-sm" onclick="showForceDeleteModal(${company.id}, '${escapeHtml(company.company_name)}', '${escapeHtml(company.username || 'N/A')}', ${company.data_points || 0}, ${company.predictions_count || 0})">
                        <i class="fa-solid fa-trash"></i> Delete
                    </button>
                </td>
            </tr>
        `).join('');
        
        loadingElement.classList.add('hidden');
        
    } catch (error) {
        console.error('Error loading companies for deletion:', error);
        tableBody.innerHTML = `
            <tr>
                <td colspan="7" style="text-align: center; color: var(--danger); padding: 2rem;">
                    <i class="fa-solid fa-exclamation-triangle"></i>
                    <div><strong>Failed to load companies</strong></div>
                    <div style="font-size: 0.875rem; opacity: 0.8;">${escapeHtml(error.message)}</div>
                </td>
            </tr>
        `;
        loadingElement.classList.add('hidden');
    }
}

function showForceDeleteModal(companyId, companyName, username, dataPoints, predictions) {
    const modal = document.getElementById('force-delete-modal');
    
    // Populate modal with company info
    document.getElementById('delete-company-name').textContent = companyName;
    document.getElementById('delete-company-username').textContent = username || 'N/A';
    document.getElementById('delete-data-points').textContent = dataPoints;
    document.getElementById('delete-predictions').textContent = predictions;
    
    // Store company ID in modal for later use
    modal.dataset.companyId = companyId;
    modal.dataset.companyName = companyName;
    
    // Reset confirmation input
    document.getElementById('confirm-delete').value = '';
    document.getElementById('confirm-delete-btn').disabled = true;
    
    modal.classList.remove('hidden');
}

function closeForceDeleteModal() {
    document.getElementById('force-delete-modal').classList.add('hidden');
}

async function confirmForceDeletion() {
    const modal = document.getElementById('force-delete-modal');
    const companyId = modal.dataset.companyId;
    const companyName = modal.dataset.companyName;
    
    const deleteBtn = document.getElementById('confirm-delete-btn');
    const originalText = deleteBtn.innerHTML;
    deleteBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Deleting...';
    deleteBtn.disabled = true;
    
    try {
        const response = await fetch(`/api/admin/force-delete/${companyId}`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showModal('Company Force Deleted', `
                <div class="success-header">
                    <i class="fa-solid fa-trash"></i>
                    <h4>Company Permanently Deleted</h4>
                </div>
                <p><strong>"${escapeHtml(companyName)}" has been permanently deleted.</strong></p>
                <div class="deletion-summary">
                    <p><strong>Removed:</strong></p>
                    <ul>
                        <li>Company request record</li>
                        <li>User credentials</li>
                        <li>Trained model file</li>
                        <li>Dataset file</li>
                        <li>All prediction history</li>
                        <li>All analytics data</li>
                    </ul>
                </div>
            `);
            
            // Close modals and refresh data
            closeForceDeleteModal();
            loadCompaniesForDeletion();
            loadCompanyRequests(); // Refresh main requests list
        } else {
            throw new Error(result.error || 'Force deletion failed');
        }
    } catch (error) {
        showModal('Deletion Failed', `
            <div class="error-header">
                <i class="fa-solid fa-exclamation-triangle"></i>
                <h4>Force Deletion Failed</h4>
            </div>
            <p>${escapeHtml(error.message)}</p>
        `);
    } finally {
        deleteBtn.innerHTML = originalText;
        deleteBtn.disabled = false;
    }
}

// --- Modal & Helpers ---

function showModal(title, content) {
    const modal = document.getElementById('action-modal');
    const modalTitle = document.getElementById('modal-title');
    const modalMessage = document.getElementById('modal-message');
    
    modalTitle.textContent = title;
    modalMessage.innerHTML = content;
    modal.classList.remove('hidden');
    modal.style.animation = 'fadeIn 0.3s ease';
}

function closeModal() {
    const modal = document.getElementById('action-modal');
    modal.classList.add('hidden');
}

function refreshRequests() {
    const refreshBtn = document.querySelector('[onclick="refreshRequests()"]');
    refreshBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Refreshing...';
    refreshBtn.disabled = true;
    
    loadCompanyRequests();
    
    setTimeout(() => {
        refreshBtn.innerHTML = '<i class="fa-solid fa-check"></i> Refreshed!';
        setTimeout(() => {
            refreshBtn.innerHTML = '<i class="fa-solid fa-refresh"></i> Refresh';
            refreshBtn.disabled = false;
        }, 1000);
    }, 500);
}

function escapeHtml(unsafe) {
    if (!unsafe) return '';
    return unsafe
        .toString()
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function getStatusIcon(status) {
    const icons = {
        'pending': 'fa-clock',
        'approved': 'fa-check-circle',
        'rejected': 'fa-times-circle'
    };
    return icons[status] || 'fa-question';
}

// Close modal when clicking outside
document.addEventListener('click', function(event) {
    const actionModal = document.getElementById('action-modal');
    const addAdminModal = document.getElementById('add-admin-modal');
    const forceDeleteModal = document.getElementById('force-delete-modal');
    
    if (event.target === actionModal) {
        closeModal();
    }
    if (event.target === addAdminModal) {
        closeAddAdminModal();
    }
    if (event.target === forceDeleteModal) {
        closeForceDeleteModal();
    }
});