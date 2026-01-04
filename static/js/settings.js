// static/js/settings.js - Enhanced Settings Functionality

class EnhancedSettings {
    constructor() {
        this.currentTheme = localStorage.getItem('dashboard-theme') || 'default';
        this.customColor = localStorage.getItem('custom-theme-color') || '#667eea';
        this.datasetHistory = [];
        this.init();
    }

    init() {
        this.loadTheme();
        this.setupEventListeners();
        this.loadDatasetHistory();
    }

    loadTheme() {
        document.documentElement.setAttribute('data-theme', 
            this.currentTheme === 'dark' ? 'dark' : 'light');
        
        // Apply custom color if theme is custom
        if (this.currentTheme === 'custom') {
            this.applyCustomColor(this.customColor);
        }
        
        // Update theme selector UI
        this.updateThemeSelector();
    }

    updateThemeSelector() {
        document.querySelectorAll('.theme-option').forEach(option => {
            option.classList.remove('active');
            if (option.dataset.theme === this.currentTheme) {
                option.classList.add('active');
            }
        });

        // Show/hide color picker based on theme
        const colorPicker = document.getElementById('color-picker-container');
        if (colorPicker) {
            colorPicker.style.display = this.currentTheme === 'custom' ? 'block' : 'none';
        }
    }

    setupEventListeners() {
        // Theme selection
        document.querySelectorAll('.theme-option').forEach(option => {
            option.addEventListener('click', (e) => {
                const theme = e.currentTarget.dataset.theme;
                this.selectTheme(theme);
            });
        });

        // Custom color picker
        const colorPicker = document.getElementById('custom-color-picker');
        if (colorPicker) {
            colorPicker.value = this.customColor;
            colorPicker.addEventListener('input', (e) => {
                this.applyCustomColor(e.target.value);
            });
        }

        // Color presets
        document.querySelectorAll('.color-preset').forEach(preset => {
            preset.addEventListener('click', (e) => {
                const color = e.currentTarget.dataset.color;
                this.applyCustomColor(color);
                document.getElementById('custom-color-picker').value = color;
            });
        });

        // Color value input
        const colorValueInput = document.getElementById('custom-color-value');
        if (colorValueInput) {
            colorValueInput.value = this.customColor;
            colorValueInput.addEventListener('change', (e) => {
                const color = e.target.value;
                if (this.isValidColor(color)) {
                    this.applyCustomColor(color);
                    document.getElementById('custom-color-picker').value = color;
                }
            });
        }

        // Retrain model button
        const retrainBtn = document.getElementById('retrain-btn');
        if (retrainBtn) {
            retrainBtn.addEventListener('click', () => this.handleRetrainModel());
        }

        // Dataset download buttons (Event Delegation)
        document.addEventListener('click', (e) => {
            const btn = e.target.closest('.download-btn');
            if (btn) {
                const datasetId = btn.dataset.id;
                this.downloadDataset(datasetId);
            }
        });
    }

    selectTheme(theme) {
        this.currentTheme = theme;
        localStorage.setItem('dashboard-theme', theme);
        
        if (theme === 'custom') {
            this.applyCustomColor(this.customColor);
        } else if (theme === 'dark') {
            document.documentElement.setAttribute('data-theme', 'dark');
        } else {
            document.documentElement.setAttribute('data-theme', 'light');
        }
        
        this.updateThemeSelector();
        this.showNotification(`Theme changed to ${theme}`, 'success');
    }

    applyCustomColor(color) {
        if (!this.isValidColor(color)) return;
        
        this.customColor = color;
        localStorage.setItem('custom-theme-color', color);
        
        // Update CSS custom property
        document.documentElement.style.setProperty('--primary-hue', this.hexToHue(color));
        document.documentElement.style.setProperty('--primary', color);
        document.documentElement.style.setProperty('--primary-dark', this.darkenColor(color, 20));
        document.documentElement.style.setProperty('--primary-light', this.lightenColor(color, 90));
        
        // Update color value display
        const colorValueInput = document.getElementById('custom-color-value');
        if (colorValueInput) {
            colorValueInput.value = color;
        }
    }

    isValidColor(color) {
        const s = new Option().style;
        s.color = color;
        return s.color !== '';
    }

    hexToHue(hex) {
        // Convert hex to RGB
        const r = parseInt(hex.slice(1, 3), 16);
        const g = parseInt(hex.slice(3, 5), 16);
        const b = parseInt(hex.slice(5, 7), 16);
        
        // Convert RGB to HSL
        const rNormalized = r / 255;
        const gNormalized = g / 255;
        const bNormalized = b / 255;
        
        const max = Math.max(rNormalized, gNormalized, bNormalized);
        const min = Math.min(rNormalized, gNormalized, bNormalized);
        
        let h = 0;
        if (max !== min) {
            if (max === rNormalized) {
                h = ((gNormalized - bNormalized) / (max - min)) % 6;
            } else if (max === gNormalized) {
                h = (bNormalized - rNormalized) / (max - min) + 2;
            } else {
                h = (rNormalized - gNormalized) / (max - min) + 4;
            }
        }
        
        h = Math.round(h * 60);
        if (h < 0) h += 360;
        
        return h;
    }

    darkenColor(color, percent) {
        const num = parseInt(color.replace("#", ""), 16);
        const amt = Math.round(2.55 * percent);
        const R = (num >> 16) - amt;
        const G = (num >> 8 & 0x00FF) - amt;
        const B = (num & 0x0000FF) - amt;
        return "#" + (0x1000000 + (R < 255 ? R < 1 ? 0 : R : 255) * 0x10000 +
            (G < 255 ? G < 1 ? 0 : G : 255) * 0x100 +
            (B < 255 ? B < 1 ? 0 : B : 255)).toString(16).slice(1);
    }

    lightenColor(color, percent) {
        const num = parseInt(color.replace("#", ""), 16);
        const amt = Math.round(2.55 * percent);
        const R = (num >> 16) + amt;
        const G = (num >> 8 & 0x00FF) + amt;
        const B = (num & 0x0000FF) + amt;
        return "#" + (0x1000000 + (R > 255 ? 255 : R) * 0x10000 +
            (G > 255 ? 255 : G) * 0x100 +
            (B > 255 ? 255 : B)).toString(16).slice(1);
    }

    async loadDatasetHistory() {
        try {
            // Updated Endpoint
            const response = await fetch('/api/company/datasets');
            if (!response.ok) throw new Error('Failed to load dataset history');
            
            this.datasetHistory = await response.json();
            this.renderDatasetHistory();
        } catch (error) {
            console.error('Error loading dataset history:', error);
            // Optional: fail silently on init to not disturb user, or show toast
        }
    }

    renderDatasetHistory() {
        const container = document.getElementById('dataset-history-list');
        if (!container) return;

        if (!this.datasetHistory || this.datasetHistory.length === 0) {
            container.innerHTML = `
                <div class="no-datasets">
                    <i class="fa-solid fa-database"></i>
                    <p>No datasets found</p>
                </div>
            `;
            return;
        }

        const html = this.datasetHistory.map(dataset => `
            <li class="dataset-item">
                <div class="dataset-icon">
                    <i class="fa-solid fa-file-csv"></i>
                </div>
                <div class="dataset-info">
                    <div class="dataset-name">
                        ${dataset.filename}
                        ${dataset.is_active ? '<span class="active-badge">ACTIVE</span>' : ''}
                    </div>
                    <div class="dataset-meta">
                        <span>${this.formatFileSize(dataset.size)}</span>
                        <span>${new Date(dataset.upload_date).toLocaleDateString()}</span>
                        <span>${dataset.records} records</span>
                    </div>
                </div>
                <div class="dataset-actions">
                    <button class="download-btn" data-id="${dataset.id}" title="Download">
                        <i class="fa-solid fa-download"></i>
                    </button>
                </div>
            </li>
        `).join('');

        container.innerHTML = html;
    }

    async downloadDataset(datasetId) {
        try {
            const dataset = this.datasetHistory.find(d => d.id == datasetId);
            if (!dataset) throw new Error('Dataset info not found');

            this.showNotification('Starting download...', 'info');

            // Updated Endpoint
            const response = await fetch(`/api/company/datasets/download/${datasetId}`);
            if (!response.ok) throw new Error('Download failed');

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = dataset.filename; // Use original filename
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

            this.showNotification('Dataset downloaded successfully', 'success');
        } catch (error) {
            console.error('Download error:', error);
            this.showNotification('Failed to download dataset', 'error');
        }
    }

    async handleRetrainModel() {
        const fileInput = document.getElementById('dataset-file');
        if (!fileInput.files.length) {
            this.showNotification('Please select a dataset file', 'warning');
            return;
        }

        const formData = new FormData();
        formData.append('dataset', fileInput.files[0]);

        this.showNotification('Retraining model... This may take a moment.', 'info');

        try {
            const response = await fetch('/api/company/retrain', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) throw new Error('Retraining failed');

            const result = await response.json();
            this.showNotification(result.message, 'success');
            
            // Clear input
            fileInput.value = '';

            // Refresh dataset history
            await this.loadDatasetHistory();
            
            // Refresh analytics if function exists globally
            if (typeof window.loadAnalyticsData === 'function') {
                window.loadAnalyticsData();
            }

        } catch (error) {
            this.showNotification(error.message, 'error');
        }
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    showNotification(message, type = 'info') {
        // Use existing notification system if available
        if (typeof window.showNotification === 'function') {
            window.showNotification(message, type);
        } else {
            // Fallback simple notification
            const notification = document.createElement('div');
            notification.className = `notification notification-${type}`;
            notification.style.position = 'fixed';
            notification.style.bottom = '20px';
            notification.style.right = '20px';
            notification.style.background = 'var(--bg-card, #fff)';
            notification.style.padding = '1rem';
            notification.style.borderRadius = '8px';
            notification.style.boxShadow = '0 4px 6px rgba(0,0,0,0.1)';
            notification.style.zIndex = '9999';
            notification.style.borderLeft = `4px solid var(--${type === 'error' ? 'danger' : 'success'}, #667eea)`;
            
            notification.innerHTML = `
                <div class="notification-content" style="display:flex; align-items:center; gap:10px;">
                    <i class="fa-solid fa-${this.getNotificationIcon(type)}"></i>
                    <span>${message}</span>
                </div>
            `;
            document.body.appendChild(notification);
            setTimeout(() => notification.remove(), 3000);
        }
    }

    getNotificationIcon(type) {
        const icons = {
            success: 'check-circle',
            error: 'exclamation-circle',
            warning: 'exclamation-triangle',
            info: 'info-circle'
        };
        return icons[type] || 'info-circle';
    }
}

// Initialize settings when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.settingsManager = new EnhancedSettings();
});