// admin_notifications.js - Enhanced with better error handling and animations
document.addEventListener('DOMContentLoaded', function() {
    // Initialize theme
    initTheme();
    
    // Setup navigation
    setupNavigation();
    
    // Load initial data
    loadInitialData();
    
    // Setup event listeners
    setupEventListeners();
    
    // Check for notifications
    checkForNotifications();
});

function initTheme() {
    // Check for saved theme or use system preference
    const savedTheme = localStorage.getItem('admin-theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
}

function setupNavigation() {
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const pageId = this.getAttribute('data-page');
            
            // Add loading animation
            this.classList.add('loading');
            
            showPage(pageId);
            
            // Update active state
            navLinks.forEach(l => {
                l.classList.remove('active');
                l.classList.remove('loading');
            });
            this.classList.add('active');
            
            // Add page transition animation
            const page = document.getElementById(pageId);
            page.style.animation = 'fadeIn 0.3s ease';
        });
    });
    
    // Set initial active page based on hash or default
    const hash = window.location.hash.substring(1);
    const initialPage = hash || 'dashboard-page';
    const initialLink = document.querySelector(`.nav-link[data-page="${initialPage}"]`);
    if (initialLink) {
        initialLink.click();
    }
}

async function loadInitialData() {
    try {
        await Promise.all([
            loadAdminInfo(),
            loadDashboardStats(),
            loadCompanyRequests(),
            loadApprovedCompanies()
        ]);
        
        showSuccessToast('Dashboard loaded successfully');
    } catch (error) {
        console.error('Initial load error:', error);
        showErrorToast('Failed to load initial data');
    }
}

function setupEventListeners() {
    // Logout button
    document.querySelector('.btn-logout').addEventListener('click', adminLogout);
    
    // Refresh button
    document.querySelector('[onclick="refreshRequests()"]')?.addEventListener('click', refreshRequests);
    
    // Automation controls
    setupAutomationToggle();
    setupRunAutomationButton();
    
    // Modal close buttons
    document.addEventListener('click', (e) => {
        if (e.target.classList.contains('modal')) {
            e.target.classList.add('hidden');
        }
    });
    
    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeModal();
        if (e.ctrlKey && e.key === 'r') {
            e.preventDefault();
            refreshRequests();
        }
    });
}

async function checkForNotifications() {
    try {
        const response = await fetch('/api/admin/notifications');
        if (response.ok) {
            const data = await response.json();
            if (data.count > 0) {
                showNotificationBadge(data.count);
            }
        }
    } catch (error) {
        // Silent fail - notifications are optional
    }
}

function showNotificationBadge(count) {
    const badge = document.createElement('span');
    badge.className = 'notification-badge';
    badge.textContent = count;
    badge.style.cssText = `
        position: absolute;
        top: -5px;
        right: -5px;
        background: var(--danger);
        color: white;
        border-radius: 50%;
        width: 20px;
        height: 20px;
        font-size: 0.75rem;
        display: flex;
        align-items: center;
        justify-content: center;
        animation: pulse 2s infinite;
    `;
    
    const automationLink = document.querySelector('.nav-link[data-page="automation-page"]');
    if (automationLink) {
        automationLink.style.position = 'relative';
        automationLink.appendChild(badge);
    }
}

// Remove the updateSessionTimer function and any calls to it

async function loadAdminInfo() {
    try {
        const res = await fetch('/api/admin/session');
        if (!res.ok) throw new Error('Session expired');
        
        const data = await res.json();
        if (data.logged_in) {
            document.getElementById('admin-username').textContent = data.username;
            
            // Update avatar with initials
            const avatar = document.getElementById('admin-avatar');
            if (avatar && data.username) {
                const initials = data.username.charAt(0).toUpperCase();
                avatar.textContent = initials;
            }
        } else {
            window.location.href = '/admin-login';
        }
    } catch (error) {
        console.error('Session check failed:', error);
        window.location.href = '/admin-login';
    }
}

// Remove the entire updateSessionTimer function
function updateSessionTimer(hoursRemaining) {
    const timer = document.createElement('div');
    timer.className = 'session-timer';
    timer.style.cssText = `
        font-size: 0.7rem;
        color: #94a3b8;
        margin-top: 2px;
    `;
    timer.textContent = `Session expires in ${Math.floor(hoursRemaining)}h`;
    
    const adminDetails = document.querySelector('.admin-details');
    if (!document.querySelector('.session-timer')) {
        adminDetails.appendChild(timer);
    }
}

async function loadDashboardStats() {
    try {
        const res = await fetch('/api/admin/requests');
        if (!res.ok) throw new Error('Failed to fetch stats');
        
        const data = await res.json();
        
        const total = data.length;
        const pending = data.filter(r => r.status === 'pending').length;
        const approved = data.filter(r => r.status === 'approved').length;
        const rejected = data.filter(r => r.status === 'rejected').length;
        
        // Update stats with animation
        updateStatWithAnimation('total-requests', total);
        updateStatWithAnimation('pending-requests', pending);
        updateStatWithAnimation('approved-requests', approved);
        updateStatWithAnimation('rejected-requests', rejected);
        
        // Update chart
        updateApprovalChart(pending, approved, rejected);
        
    } catch (error) {
        console.error('Error loading stats:', error);
        showErrorToast('Failed to load dashboard statistics');
    }
}

function updateStatWithAnimation(elementId, newValue) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    const currentValue = parseInt(element.textContent) || 0;
    
    if (currentValue !== newValue) {
        // Add animation class
        element.parentElement.classList.add('stat-updated');
        
        // Animate the number change
        animateCounter(element, currentValue, newValue);
        
        // Remove animation class after animation
        setTimeout(() => {
            element.parentElement.classList.remove('stat-updated');
        }, 500);
    }
}

function animateCounter(element, start, end) {
    const duration = 500;
    const startTime = performance.now();
    
    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        const current = Math.floor(start + (end - start) * progress);
        element.textContent = current;
        
        if (progress < 1) {
            requestAnimationFrame(update);
        } else {
            element.textContent = end;
        }
    }
    
    requestAnimationFrame(update);
}

function updateApprovalChart(pending, approved, rejected) {
    const ctx = document.getElementById('approval-chart').getContext('2d');
    
    if (window.approvalChart) {
        window.approvalChart.destroy();
    }
    
    window.approvalChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Pending', 'Approved', 'Rejected'],
            datasets: [{
                data: [pending, approved, rejected],
                backgroundColor: [
                    'rgba(245, 158, 11, 0.8)',
                    'rgba(16, 185, 129, 0.8)',
                    'rgba(239, 68, 68, 0.8)'
                ],
                borderColor: [
                    '#f59e0b',
                    '#10b981',
                    '#ef4444'
                ],
                borderWidth: 2,
                borderRadius: 8,
                hoverOffset: 15
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '70%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 20,
                        usePointStyle: true,
                        font: {
                            size: 12,
                            family: "'Inter', sans-serif"
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.raw || 0;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = Math.round((value / total) * 100);
                            return `${label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            },
            animation: {
                animateScale: true,
                animateRotate: true,
                duration: 1000,
                easing: 'easeOutQuart'
            }
        }
    });
}

async function loadCompanyRequests() {
    try {
        showLoading('requests-body');
        
        const res = await fetch('/api/admin/requests');
        if (!res.ok) throw new Error('Failed to fetch requests');
        
        const data = await res.json();
        renderCompanyRequests(data);
        
    } catch (error) {
        console.error('Error loading requests:', error);
        showErrorInTable('requests-body', 'Failed to load company requests');
    }
}

function renderCompanyRequests(requests) {
    const tbody = document.getElementById('requests-body');
    
    if (requests.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" style="text-align: center; padding: 3rem;">
                    <div style="opacity: 0.5;">
                        <i class="fa-solid fa-inbox" style="font-size: 3rem; margin-bottom: 1rem;"></i>
                        <p style="font-size: 1.1rem; color: var(--text-muted);">No company requests found</p>
                    </div>
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = requests.map(request => `
        <tr data-request-id="${request.id}" data-status="${request.status}" class="fade-in">
            <td>
                <div style="display: flex; align-items: center; gap: 1rem;">
                    <div style="width: 40px; height: 40px; background: linear-gradient(135deg, #4f46e5, #8b5cf6); border-radius: 10px; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold;">
                        ${request.company_name.charAt(0).toUpperCase()}
                    </div>
                    <div>
                        <div style="font-weight: 600; margin-bottom: 0.25rem;">${escapeHtml(request.company_name)}</div>
                        <div style="font-size: 0.875rem; color: var(--text-muted);">${escapeHtml(request.email)}</div>
                    </div>
                </div>
            </td>
            <td>
                <div style="font-weight: 500;">${escapeHtml(request.contact_person)}</div>
                ${request.phone ? `<div style="font-size: 0.875rem; color: var(--text-muted);"><i class="fa-solid fa-phone"></i> ${escapeHtml(request.phone)}</div>` : ''}
            </td>
            <td>
                <div>${new Date(request.created_at).toLocaleDateString()}</div>
                <div style="font-size: 0.875rem; color: var(--text-muted);">${new Date(request.created_at).toLocaleTimeString()}</div>
            </td>
            <td>
                <span class="status-badge status-${request.status}">
                    <i class="fa-solid ${getStatusIcon(request.status)}"></i>
                    ${request.status.toUpperCase()}
                </span>
            </td>
            <td>
                <div style="display: flex; gap: 0.5rem;">
                    ${request.status === 'pending' ? `
                        <button class="btn-icon success" onclick="approveRequest(${request.id})" title="Approve">
                            <i class="fa-solid fa-check"></i>
                        </button>
                        <button class="btn-icon danger" onclick="rejectRequest(${request.id})" title="Reject">
                            <i class="fa-solid fa-xmark"></i>
                        </button>
                    ` : `
                        <span style="color: var(--text-muted); font-size: 0.875rem;">
                            ${request.status === 'approved' ? 'Approved' : 'Rejected'}
                        </span>
                    `}
                </div>
            </td>
        </tr>
    `).join('');
}

async function loadApprovedCompanies() {
    try {
        showLoading('companies-body');
        
        const res = await fetch('/api/admin/requests');
        if (!res.ok) throw new Error('Failed to fetch companies');
        
        const data = await res.json();
        const approved = data.filter(r => r.status === 'approved');
        renderApprovedCompanies(approved);
        
    } catch (error) {
        console.error('Error loading companies:', error);
        showErrorInTable('companies-body', 'Failed to load approved companies');
    }
}

function renderApprovedCompanies(companies) {
    const tbody = document.getElementById('companies-body');
    
    if (companies.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" style="text-align: center; padding: 3rem;">
                    <div style="opacity: 0.5;">
                        <i class="fa-solid fa-building" style="font-size: 3rem; margin-bottom: 1rem;"></i>
                        <p style="font-size: 1.1rem; color: var(--text-muted);">No approved companies yet</p>
                    </div>
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = companies.map(company => `
        <tr class="fade-in">
            <td>
                <div style="display: flex; align-items: center; gap: 1rem;">
                    <div style="width: 40px; height: 40px; background: linear-gradient(135deg, #10b981, #34d399); border-radius: 10px; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold;">
                        ${company.company_name.charAt(0).toUpperCase()}
                    </div>
                    <div>
                        <div style="font-weight: 600; margin-bottom: 0.25rem;">${escapeHtml(company.company_name)}</div>
                        <div style="font-size: 0.875rem; color: var(--text-muted);">Since ${new Date(company.approved_at).toLocaleDateString()}</div>
                    </div>
                </div>
            </td>
            <td>
                <code style="background: var(--bg-body); padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.875rem;">
                    ${escapeHtml(company.username)}
                </code>
            </td>
            <td>
                ${company.model_accuracy ? `
                    <div style="display: flex; align-items: center; gap: 0.5rem;">
                        <div style="width: 60px; height: 6px; background: var(--border); border-radius: 3px; overflow: hidden;">
                            <div style="width: ${company.model_accuracy * 100}%; height: 100%; background: linear-gradient(90deg, #10b981, #34d399);"></div>
                        </div>
                        <span style="font-weight: 600; color: ${company.model_accuracy > 0.7 ? '#10b981' : company.model_accuracy > 0.5 ? '#f59e0b' : '#ef4444'}">
                            ${Math.round(company.model_accuracy * 100)}%
                        </span>
                    </div>
                ` : 'N/A'}
            </td>
            <td>
                <span style="font-weight: 600; color: var(--primary);">
                    ${company.data_points || 0}
                </span>
            </td>
            <td>
                ${new Date(company.approved_at).toLocaleDateString()}
            </td>
        </tr>
    `).join('');
}

function showPage(pageId) {
    // Hide all pages
    document.querySelectorAll('.page-section').forEach(page => {
        page.classList.add('hidden');
    });
    
    // Show selected page
    const selectedPage = document.getElementById(pageId);
    if (selectedPage) {
        selectedPage.classList.remove('hidden');
        
        // Update page title
        const titles = {
            'dashboard-page': { title: 'Dashboard', subtitle: 'System Overview & Analytics' },
            'requests-page': { title: 'Company Requests', subtitle: 'Manage pending requests and approvals' },
            'companies-page': { title: 'Approved Companies', subtitle: 'Active companies and their performance' },
            'automation-page': { title: 'Automation Center', subtitle: 'Monitor and manage automated processes' }
        };
        
        const pageInfo = titles[pageId];
        if (pageInfo) {
            document.getElementById('page-title').textContent = pageInfo.title;
            document.getElementById('page-subtitle').textContent = pageInfo.subtitle;
        }
        
        // Load specific data for certain pages
        if (pageId === 'automation-page') {
            setTimeout(() => {
                loadInactiveAccounts();
                loadLowAccuracyAccounts();
            }, 100);
        }
    }
}

// --- Automation Functions ---

async function setupAutomationToggle() {
    const toggle = document.getElementById('automation-mode-toggle');
    const desc = document.getElementById('mode-description');
    
    try {
        const res = await fetch('/api/admin/automation/settings');
        if (!res.ok) throw new Error('Failed to load settings');
        
        const data = await res.json();
        // Compare with string values
        toggle.checked = (data.mode === 'automated');
        updateModeText(toggle.checked);
        
        toggle.addEventListener('change', async (e) => {
            const mode = e.target.checked ? 'automated' : 'manual';  // String values
            const button = e.target;
            button.disabled = true;
            
            try {
                const res = await fetch('/api/admin/automation/settings', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({mode: mode})  // Send string
                });
                
                if (res.ok) {
                    updateModeText(e.target.checked);
                    showSuccessToast(`Mode changed to ${mode}`);
                } else {
                    throw new Error('Failed to update mode');
                }
            } catch (error) {
                showErrorToast('Failed to update automation mode');
                toggle.checked = !e.target.checked; // Revert toggle
            } finally {
                button.disabled = false;
            }
        });
        
    } catch (error) {
        console.error('Error setting up toggle:', error);
        showErrorToast('Failed to load automation settings');
    }
}
function updateModeText(isAuto) {
    const desc = document.getElementById('mode-description');
    if (isAuto) {
        desc.innerHTML = `
            <i class="fa-solid fa-robot" style="color: var(--success); margin-right: 0.5rem;"></i>
            System is in <strong style="color: var(--success);">Automated Mode</strong>. 
            Warnings and deletions occur automatically based on configured rules.
        `;
        desc.style.borderLeftColor = 'var(--success)';
        desc.style.background = 'linear-gradient(135deg, var(--success-light), white)';
    } else {
        desc.innerHTML = `
            <i class="fa-solid fa-hand" style="color: var(--warning); margin-right: 0.5rem;"></i>
            System is in <strong style="color: var(--warning);">Manual Mode</strong>. 
            Actions require admin approval and manual intervention.
        `;
        desc.style.borderLeftColor = 'var(--warning)';
        desc.style.background = 'linear-gradient(135deg, var(--warning-light), white)';
    }
}

function setupRunAutomationButton() {
    const button = document.getElementById('run-automation-btn');
    if (!button) return;
    
    button.addEventListener('click', async () => {
        if (!confirm("Run automation logic now? This will check all accounts for inactivity and low accuracy.")) return;
        
        button.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Running...';
        button.disabled = true;
        
        try {
            const res = await fetch('/api/admin/automation/run', {method: 'POST'});
            const data = await res.json();
            
            if (res.ok) {
                showModal("Automation Results", `
                    <div style="text-align: center; padding: 1rem;">
                        <i class="fa-solid fa-check-circle" style="font-size: 3rem; color: var(--success); margin-bottom: 1rem;"></i>
                        <h3 style="margin-bottom: 1rem;">Automation Completed</h3>
                        
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin: 1.5rem 0;">
                            <div style="background: var(--bg-body); padding: 1rem; border-radius: 8px;">
                                <div style="font-size: 2rem; font-weight: 800; color: var(--primary);">${data.results.inactive_accounts_found}</div>
                                <div style="font-size: 0.875rem; color: var(--text-muted);">Inactive Accounts</div>
                            </div>
                            <div style="background: var(--bg-body); padding: 1rem; border-radius: 8px;">
                                <div style="font-size: 2rem; font-weight: 800; color: var(--primary);">${data.results.low_accuracy_accounts_found}</div>
                                <div style="font-size: 0.875rem; color: var(--text-muted);">Low Accuracy</div>
                            </div>
                        </div>
                        
                        ${data.note ? `<p style="color: var(--text-muted); font-size: 0.875rem; margin-top: 1rem;">${data.note}</p>` : ''}
                    </div>
                `);
                
                // Refresh data
                loadInactiveAccounts();
                loadLowAccuracyAccounts();
            } else {
                throw new Error(data.error || 'Automation failed');
            }
        } catch (error) {
            showErrorToast('Automation run failed');
            console.error('Automation error:', error);
        } finally {
            button.innerHTML = '<i class="fa-solid fa-play"></i> Run Now';
            button.disabled = false;
        }
    });
}

// In admin_notifications.js, update the loadInactiveAccounts function
async function loadInactiveAccounts() {
    try {
        showLoading('inactive-accounts-body');
        
        const res = await fetch('/api/admin/inactive-accounts');
        if (!res.ok) {
            throw new Error(`HTTP error! status: ${res.status}`);
        }
        
        const data = await res.json();
        
        // Check if we got an error response
        if (data.error) {
            throw new Error(data.error);
        }
        
        // Make sure data.accounts exists
        const accounts = data.accounts || [];
        renderInactiveAccounts(accounts);
        
    } catch (error) {
        console.error('Error loading inactive accounts:', error);
        showErrorInTable('inactive-accounts-body', 'Failed to load inactive accounts: ' + error.message);
    }
}

// Update the renderInactiveAccounts function
function renderInactiveAccounts(accounts) {
    const tbody = document.getElementById('inactive-accounts-body');
    const countElement = document.getElementById('inactive-count');
    
    if (countElement) {
        countElement.textContent = accounts.length;
    }
    
    if (accounts.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="4" style="text-align: center; padding: 2rem;">
                    <div style="opacity: 0.5;">
                        <i class="fa-solid fa-user-check" style="font-size: 2rem; margin-bottom: 0.5rem;"></i>
                        <p style="color: var(--text-muted);">All accounts are active</p>
                    </div>
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = accounts.map(account => {
        const days = account.days_inactive || 0;
        const status = account.status || 'warning';
        const statusClass = getStatusClass(status);
        const statusText = getStatusText(status);
        
        return `
        <tr class="fade-in">
            <td>
                <div style="display: flex; align-items: center; gap: 0.75rem;">
                    <div style="width: 36px; height: 36px; background: ${getInactivityGradient(days)}; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: white;">
                        <i class="fa-solid fa-building"></i>
                    </div>
                    <div>
                        <div style="font-weight: 600;">${escapeHtml(account.company_name || 'Unknown Company')}</div>
                        <div style="font-size: 0.875rem; color: var(--text-muted);">${escapeHtml(account.email || '')}</div>
                    </div>
                </div>
            </td>
            <td>
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                    <span style="font-weight: 700; color: ${getInactivityColor(days)};">
                        ${days}
                    </span>
                    <span style="font-size: 0.875rem; color: var(--text-muted);">days</span>
                </div>
            </td>
            <td>
                <span class="status-badge ${statusClass}">
                    ${statusText}
                </span>
            </td>
            <td>
                <div style="display: flex; gap: 0.5rem;">
                    <button class="btn btn-sm btn-outline" onclick="warnInactive(${account.user_id})" title="Send Warning">
                        <i class="fa-solid fa-bell"></i> Warn
                    </button>
                    <button class="btn btn-sm btn-danger" onclick="deleteAccount(${account.user_id})" title="Delete Account">
                        <i class="fa-solid fa-trash"></i> Delete
                    </button>
                </div>
            </td>
        </tr>
        `;
    }).join('');
}

// Helper functions
function getInactivityColor(days) {
    if (days > 90) return '#ef4444';
    if (days > 60) return '#f97316';
    if (days > 30) return '#f59e0b';
    if (days > 14) return '#eab308';
    return '#64748b';
}

function getInactivityGradient(days) {
    if (days > 90) return 'linear-gradient(135deg, #ef4444, #dc2626)';
    if (days > 60) return 'linear-gradient(135deg, #f97316, #ea580c)';
    if (days > 30) return 'linear-gradient(135deg, #f59e0b, #d97706)';
    if (days > 14) return 'linear-gradient(135deg, #eab308, #ca8a04)';
    return 'linear-gradient(135deg, #64748b, #475569)';
}

function getStatusClass(status) {
    const statusMap = {
        'critical': 'status-red',
        'warning_3': 'status-orange',
        'warning_2': 'status-yellow',
        'warning_1': 'status-yellow',
        'warning': 'status-yellow',
        'active': 'status-green'
    };
    return statusMap[status] || 'status-yellow';
}

function getStatusText(status) {
    const textMap = {
        'critical': 'CRITICAL',
        'warning_3': 'HIGH RISK',
        'warning_2': 'MEDIUM RISK',
        'warning_1': 'LOW RISK',
        'warning': 'WARNING',
        'active': 'ACTIVE'
    };
    return textMap[status] || 'WARNING';
}

// Update showErrorInTable function
function showErrorInTable(tableId, message) {
    const tbody = document.getElementById(tableId);
    if (tbody) {
        tbody.innerHTML = `
            <tr>
                <td colspan="4" style="text-align: center; padding: 3rem; color: var(--danger);">
                    <i class="fa-solid fa-exclamation-triangle" style="font-size: 2rem; margin-bottom: 1rem;"></i>
                    <p>${message}</p>
                    <button class="btn btn-sm btn-outline" onclick="loadInactiveAccounts()" style="margin-top: 1rem;">
                        <i class="fa-solid fa-refresh"></i> Retry
                    </button>
                </td>
            </tr>
        `;
    }
}

function renderInactiveAccounts(accounts) {
    const tbody = document.getElementById('inactive-accounts-body');
    document.getElementById('inactive-count').textContent = accounts.length;
    
    if (accounts.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="4" style="text-align: center; padding: 2rem;">
                    <div style="opacity: 0.5;">
                        <i class="fa-solid fa-user-check" style="font-size: 2rem; margin-bottom: 0.5rem;"></i>
                        <p style="color: var(--text-muted);">All accounts are active</p>
                    </div>
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = accounts.map(account => `
        <tr class="fade-in">
            <td>
                <div style="display: flex; align-items: center; gap: 0.75rem;">
                    <div style="width: 36px; height: 36px; background: linear-gradient(135deg, #f59e0b, #fbbf24); border-radius: 8px; display: flex; align-items: center; justify-content: center; color: white;">
                        <i class="fa-solid fa-building"></i>
                    </div>
                    <div>
                        <div style="font-weight: 600;">${escapeHtml(account.company_name)}</div>
                        <div style="font-size: 0.875rem; color: var(--text-muted);">${escapeHtml(account.email || '')}</div>
                    </div>
                </div>
            </td>
            <td>
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                    <span style="font-weight: 700; color: ${getInactivityColor(account.days_inactive)};">
                        ${account.days_inactive || 0}
                    </span>
                    <span style="font-size: 0.875rem; color: var(--text-muted);">days</span>
                </div>
            </td>
            <td>
                <span class="status-badge status-${account.status || 'warning'}">
                    ${(account.status || 'warning').toUpperCase()}
                </span>
            </td>
            <td>
                <div style="display: flex; gap: 0.5rem;">
                    <button class="btn btn-sm btn-outline" onclick="warnInactive(${account.user_id})" title="Send Warning">
                        <i class="fa-solid fa-bell"></i> Warn
                    </button>
                    <button class="btn btn-sm btn-danger" onclick="deleteAccount(${account.user_id})" title="Delete Account">
                        <i class="fa-solid fa-trash"></i> Delete
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

function getInactivityColor(days) {
    if (days > 90) return '#ef4444';
    if (days > 60) return '#f97316';
    if (days > 30) return '#f59e0b';
    if (days > 14) return '#eab308';
    return '#64748b';
}

async function loadLowAccuracyAccounts() {
    try {
        const res = await fetch('/api/admin/low-accuracy-accounts');
        if (!res.ok) throw new Error('Failed to load low accuracy accounts');
        
        const data = await res.json();
        renderLowAccuracyAccounts(data.accounts);
        
    } catch (error) {
        console.error('Error loading low accuracy accounts:', error);
        showErrorInTable('low-accuracy-body', 'Failed to load low accuracy accounts');
    }
}

function renderLowAccuracyAccounts(accounts) {
    const tbody = document.getElementById('low-accuracy-body');
    document.getElementById('low-acc-count').textContent = accounts.length;
    
    if (accounts.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="4" style="text-align: center; padding: 2rem;">
                    <div style="opacity: 0.5;">
                        <i class="fa-solid fa-chart-line" style="font-size: 2rem; margin-bottom: 0.5rem;"></i>
                        <p style="color: var(--text-muted);">All models performing well</p>
                    </div>
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = accounts.map(account => `
        <tr class="fade-in">
            <td>
                <div style="display: flex; align-items: center; gap: 0.75rem;">
                    <div style="width: 36px; height: 36px; background: linear-gradient(135deg, #ef4444, #f87171); border-radius: 8px; display: flex; align-items: center; justify-content: center; color: white;">
                        <i class="fa-solid fa-chart-line"></i>
                    </div>
                    <div>
                        <div style="font-weight: 600;">${escapeHtml(account.company_name)}</div>
                        <div style="font-size: 0.875rem; color: var(--text-muted);">Model needs improvement</div>
                    </div>
                </div>
            </td>
            <td>
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                    <div style="font-weight: 800; color: #ef4444; font-size: 1.1rem;">
                        ${Math.round(account.model_accuracy * 100)}%
                    </div>
                    <div style="width: 80px; height: 6px; background: var(--border); border-radius: 3px; overflow: hidden;">
                        <div style="width: ${account.model_accuracy * 100}%; height: 100%; background: linear-gradient(90deg, #ef4444, #f87171);"></div>
                    </div>
                </div>
            </td>
            <td>
                ${account.last_accuracy_check ? 
                    new Date(account.last_accuracy_check).toLocaleDateString() : 
                    '<span style="color: var(--text-muted); font-size: 0.875rem;">Never</span>'
                }
            </td>
            <td>
                <div style="display: flex; gap: 0.5rem;">
                    <button class="btn btn-sm btn-outline" onclick="warnAccuracy(${account.company_request_id})" title="Send Warning">
                        <i class="fa-solid fa-bell"></i> Warn
                    </button>
                    <button class="btn btn-sm btn-danger" onclick="deleteAccount(${account.user_id})" title="Delete Account">
                        <i class="fa-solid fa-trash"></i> Delete
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

// --- Action Functions ---

async function approveRequest(id) {
    if (!confirm('Approve this company request? This will train a custom model and send login credentials.')) return;
    
    const row = document.querySelector(`tr[data-request-id="${id}"]`);
    if (row) {
        const approveBtn = row.querySelector('.btn-icon.success');
        if (approveBtn) {
            approveBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
            approveBtn.disabled = true;
        }
    }
    
    try {
        const response = await fetch(`/api/admin/approve/${id}`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'}
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showModal('Request Approved', `
                <div style="text-align: center; padding: 1rem;">
                    <i class="fa-solid fa-check-circle" style="font-size: 3rem; color: var(--success); margin-bottom: 1rem;"></i>
                    <h3 style="margin-bottom: 1rem;">Company Approved Successfully</h3>
                    
                    <div style="background: var(--bg-body); padding: 1.5rem; border-radius: 12px; margin: 1.5rem 0;">
                        <p style="color: var(--text-muted); margin-bottom: 1rem;">Generated Credentials:</p>
                        <div style="display: grid; gap: 0.75rem;">
                            <div>
                                <label style="display: block; font-size: 0.875rem; color: var(--text-muted); margin-bottom: 0.25rem;">Username</label>
                                <code style="background: white; padding: 0.5rem 1rem; border-radius: 6px; font-size: 1.1rem; font-weight: 600; display: block;">
                                    ${escapeHtml(result.username)}
                                </code>
                            </div>
                            <div>
                                <label style="display: block; font-size: 0.875rem; color: var(--text-muted); margin-bottom: 0.25rem;">Password</label>
                                <code style="background: white; padding: 0.5rem 1rem; border-radius: 6px; font-size: 1.1rem; font-weight: 600; display: block; color: var(--primary);">
                                    ${escapeHtml(result.password)}
                                </code>
                            </div>
                        </div>
                    </div>
                    
                    <div style="display: flex; align-items: center; justify-content: center; gap: 0.5rem; margin-top: 1.5rem; color: var(--text-muted);">
                        <i class="fa-solid fa-envelope"></i>
                        <span>Credentials sent to the company's email</span>
                    </div>
                </div>
            `);
            
            // Refresh data
            loadCompanyRequests();
            loadDashboardStats();
            
        } else {
            throw new Error(result.error || 'Approval failed');
        }
    } catch (error) {
        showErrorToast('Approval failed: ' + error.message);
        
        // Re-enable button
        const row = document.querySelector(`tr[data-request-id="${id}"]`);
        if (row) {
            const approveBtn = row.querySelector('.btn-icon.success');
            if (approveBtn) {
                approveBtn.innerHTML = '<i class="fa-solid fa-check"></i>';
                approveBtn.disabled = false;
            }
        }
    }
}

async function rejectRequest(id) {
    if (!confirm('Reject this company request?')) return;
    
    const row = document.querySelector(`tr[data-request-id="${id}"]`);
    if (row) {
        const rejectBtn = row.querySelector('.btn-icon.danger');
        if (rejectBtn) {
            rejectBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
            rejectBtn.disabled = true;
        }
    }
    
    try {
        const response = await fetch(`/api/admin/reject/${id}`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'}
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showSuccessToast('Request rejected successfully');
            loadCompanyRequests();
            loadDashboardStats();
        } else {
            throw new Error(result.error || 'Rejection failed');
        }
    } catch (error) {
        showErrorToast('Rejection failed: ' + error.message);
        
        // Re-enable button
        const row = document.querySelector(`tr[data-request-id="${id}"]`);
        if (row) {
            const rejectBtn = row.querySelector('.btn-icon.danger');
            if (rejectBtn) {
                rejectBtn.innerHTML = '<i class="fa-solid fa-xmark"></i>';
                rejectBtn.disabled = false;
            }
        }
    }
}

async function warnInactive(userId) {
    try {
        const response = await fetch(`/api/admin/manual/warn-inactive/${userId}`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'}
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showSuccessToast('Warning email sent successfully');
        } else {
            throw new Error(result.error || 'Failed to send warning');
        }
    } catch (error) {
        showErrorToast('Failed to send warning: ' + error.message);
    }
}

async function warnAccuracy(reqId) {
    try {
        const response = await fetch(`/api/admin/manual/warn-low-accuracy/${reqId}`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'}
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showSuccessToast('Low accuracy warning sent');
        } else {
            throw new Error(result.error || 'Failed to send warning');
        }
    } catch (error) {
        showErrorToast('Failed to send warning: ' + error.message);
    }
}

async function deleteAccount(userId) {
    if (!confirm('Are you sure you want to delete this account? This action cannot be undone.')) return;
    
    try {
        const response = await fetch(`/api/admin/manual/delete-account/${userId}`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'}
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showSuccessToast('Account deleted successfully');
            loadInactiveAccounts();
            loadLowAccuracyAccounts();
        } else {
            throw new Error(result.error || 'Deletion failed');
        }
    } catch (error) {
        showErrorToast('Deletion failed: ' + error.message);
    }
}

// --- Utility Functions ---

function showLoading(tableId) {
    const tbody = document.getElementById(tableId);
    if (tbody) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" style="text-align: center; padding: 3rem;">
                    <div class="loading" style="width: 40px; height: 40px; margin: 0 auto;"></div>
                    <p style="margin-top: 1rem; color: var(--text-muted);">Loading...</p>
                </td>
            </tr>
        `;
    }
}

function showErrorInTable(tableId, message) {
    const tbody = document.getElementById(tableId);
    if (tbody) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" style="text-align: center; padding: 3rem; color: var(--danger);">
                    <i class="fa-solid fa-exclamation-triangle" style="font-size: 2rem; margin-bottom: 1rem;"></i>
                    <p>${message}</p>
                    <button class="btn btn-sm btn-outline" onclick="location.reload()" style="margin-top: 1rem;">
                        <i class="fa-solid fa-refresh"></i> Retry
                    </button>
                </td>
            </tr>
        `;
    }
}

function showModal(title, content) {
    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal-message').innerHTML = content;
    document.getElementById('action-modal').classList.remove('hidden');
}

function closeModal() {
    document.getElementById('action-modal').classList.add('hidden');
}

function showSuccessToast(message) {
    showToast(message, 'success');
}

function showErrorToast(message) {
    showToast(message, 'error');
}

function showToast(message, type = 'info') {
    // Remove existing toasts
    document.querySelectorAll('.toast').forEach(toast => toast.remove());
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'success' ? 'var(--success)' : 'var(--danger)'};
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        box-shadow: var(--shadow-lg);
        z-index: 10000;
        display: flex;
        align-items: center;
        gap: 0.75rem;
        animation: slideInRight 0.3s ease, fadeOut 0.3s ease 2.7s;
        animation-fill-mode: forwards;
    `;
    
    const icon = type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle';
    toast.innerHTML = `
        <i class="fa-solid ${icon}" style="font-size: 1.25rem;"></i>
        <span>${message}</span>
    `;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, 3000);
}

function getStatusIcon(status) {
    const icons = {
        'pending': 'fa-clock',
        'approved': 'fa-check-circle',
        'rejected': 'fa-times-circle'
    };
    return icons[status] || 'fa-question-circle';
}

function escapeHtml(unsafe) {
    if (!unsafe) return '';
    return unsafe.toString()
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function refreshRequests() {
    const button = document.querySelector('[onclick="refreshRequests()"]');
    if (button) {
        const originalHTML = button.innerHTML;
        button.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Refreshing...';
        button.disabled = true;
        
        Promise.all([
            loadCompanyRequests(),
            loadDashboardStats(),
            loadApprovedCompanies()
        ]).then(() => {
            showSuccessToast('Data refreshed successfully');
            button.innerHTML = '<i class="fa-solid fa-check"></i> Refreshed';
            setTimeout(() => {
                button.innerHTML = originalHTML;
                button.disabled = false;
            }, 1000);
        }).catch(() => {
            button.innerHTML = originalHTML;
            button.disabled = false;
        });
    }
}

function adminLogout() {
    if (confirm('Are you sure you want to logout?')) {
        fetch('/api/admin/logout', { method: 'POST' })
            .then(() => window.location.href = '/admin-login')
            .catch(() => window.location.href = '/admin-login');
    }
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    @keyframes slideInRight {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    @keyframes fadeOut {
        from { opacity: 1; }
        to { opacity: 0; }
    }
    
    @keyframes pulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.1); }
    }
    
    .fade-in {
        animation: fadeIn 0.3s ease;
    }
    
    .stat-updated {
        animation: pulse 0.5s ease;
    }
    
    .loading {
        border: 3px solid #f3f4f6;
        border-top-color: #4f46e5;
        border-radius: 50%;
        animation: spin 1s linear infinite;
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
`;
document.head.appendChild(style);