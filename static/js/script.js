// static/js/script.js - UPDATED VERSION
document.addEventListener("DOMContentLoaded", () => {
   // --- Theme Switcher Logic ---
const themeToggleBtn = document.getElementById("theme-toggle");

// Helper to apply & save theme
function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("theme", theme);
}

// Initialize theme on page load
const savedTheme = localStorage.getItem("theme");
if (savedTheme) {
    applyTheme(savedTheme);
} else {
    // if nothing saved, keep whatever is in HTML (light) but still store it
    const initial = document.documentElement.getAttribute("data-theme") || "light";
    applyTheme(initial);
}

// Toggle on button click
themeToggleBtn.addEventListener("click", () => {
    const current = document.documentElement.getAttribute("data-theme") || "light";
    const next = current === "light" ? "dark" : "light";
    applyTheme(next);
});

    // --- App Logic ---
    const inputsDiv = document.getElementById("inputs");
    const resultDiv = document.getElementById("result");
    const form = document.getElementById("predict-form");
    const predictBtn = document.getElementById("predict-btn");

    initializeTabs();
    fetchInitialData();

    function initializeTabs() {
        // *** UPDATED SELECTOR ***
        const tabs = document.querySelectorAll('.sidebar-link'); 
        tabs.forEach(tab => {
            tab.addEventListener('click', () => switchTab(tab.dataset.tab));
        });
    }

    function switchTab(tabName) {
        // *** UPDATED SELECTOR ***
        document.querySelectorAll('.sidebar-link').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.tab === tabName);
        });
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.toggle('active', content.id === `${tabName}-tab`);
        });
    }

    async function fetchInitialData() {
        try {
            const [optionsRes, comparisonRes] = await Promise.all([
                fetch("/options"),
                fetch("/model-comparison")
            ]);
            
            if (!optionsRes.ok) throw new Error('Failed to fetch options data.');
            if (!comparisonRes.ok) throw new Error('Failed to fetch comparison data.');
            
            const optionsData = await optionsRes.json();
            const comparisonData = await comparisonRes.json();
            
            console.log("Options data:", optionsData);
            console.log("Comparison data:", comparisonData);
            
            buildFormInputs(optionsData);
            buildModelComparison(comparisonData);
        } catch (error) {
            console.error('Initialization Error:', error);
            inputsDiv.innerHTML = `<div class="card" style="text-align:center; border-color:var(--danger); color:var(--danger);">
                <h4><i class="fa-solid fa-triangle-exclamation"></i> Error</h4>
                <p>Could not load model data. Please ensure:</p>
                <ol style="text-align:left; margin:1rem 0;">
                    <li>The server is running</li>
                    <li>You have run train.py to generate the model</li>
                    <li>All required files are in the models/ directory</li>
                </ol>
                <p><strong>Solution:</strong> Run <code>python train.py</code> first, then restart the app.</p>
            </div>`;
        }
    }

    function buildFormInputs(data) {
        inputsDiv.innerHTML = '';
        const { numeric_cols, categorical_cols, categorical, numeric_meta } = data;

        console.log("Building form with data:", data);

        // Define the exact order of fields we want
        const fieldOrder = [
            { type: 'numeric', field: 'age' },
            { type: 'numeric', field: 'experience' },
            { type: 'categorical', field: 'gender' },
            { type: 'categorical', field: 'role' },
            { type: 'categorical', field: 'sector' },
            { type: 'categorical', field: 'company' },
            { type: 'categorical', field: 'department' },
            { type: 'categorical', field: 'education' }
        ];

        fieldOrder.forEach(({ type, field }) => {
            let inputGroup = '';
            
            if (type === 'numeric' && numeric_cols.includes(field)) {
                const meta = numeric_meta[field] || { min: 0, max: 100, median: 30, mean: 35 };
                inputGroup = `
                    <div class="input-group">
                        <label for="${field}">${formatLabel(field)} *</label>
                        <input class="input" type="number" id="${field}" name="${field}"
                               value="${meta.median || ''}" min="${meta.min || 0}" max="${meta.max || 100}"
                               placeholder="e.g., ${meta.median || 30}" required 
                               step="${field === 'age' ? '1' : '0.1'}"/>
                        <small style="color: var(--text-secondary); margin-top: 0.5rem; display: block;">
                            Range: ${meta.min || 0} - ${meta.max || 100}
                        </small>
                    </div>`;
            }
            else if (type === 'categorical' && categorical_cols.includes(field)) {
                const optionsList = categorical[field] || ['Option 1', 'Option 2', 'Option 3'];
                const options = optionsList
                    .map(opt => `<option value="${opt}">${opt}</option>`).join('');
                inputGroup = `
                    <div class="input-group">
                        <label for="${field}">${formatLabel(field)} *</label>
                        <select class="input" id="${field}" name="${field}" required>
                            <option value="">-- Select ${formatLabel(field)} --</option>
                            ${options}
                        </select>
                        <small style="color: var(--text-secondary); margin-top: 0.5rem; display: block;">
                            ${optionsList.length} options available
                        </small>
                    </div>`;
            }
            
            if (inputGroup) {
                inputsDiv.innerHTML += inputGroup;
            }
        });
        
        // Add event listener for form validation
        form.addEventListener('input', validateForm);
        validateForm();
        
        console.log("Form inputs built successfully");
    }

    function buildModelComparison(data) {
        const container = document.getElementById('comparison-tab');
        const { model_comparison, best_model, cv_score, all_models } = data;
        
        let comparisonHTML = `
            <div class="card">
                <h2><i class="fa-solid fa-balance-scale"></i> Model Performance</h2>
                <p class="description">Models are evaluated using R² score. The best model is chosen and further optimized with hyperparameter tuning.</p>
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-number">${all_models?.length || 0}</div>
                        <div class="stat-label">Models Evaluated</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">${((cv_score || 0) * 100).toFixed(1)}%</div>
                        <div class="stat-label">Best Model CV Score</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">${best_model?.replace(" (Tuned)", "") || 'N/A'}</div>
                        <div class="stat-label">Best Performing Algorithm</div>
                    </div>
                </div>
            </div>
        `;

        if (model_comparison && Object.keys(model_comparison).length > 0) {
            comparisonHTML += `<div class="models-grid">`;
            
            Object.entries(model_comparison).forEach(([name, metrics]) => {
                const isBest = name === best_model;
                comparisonHTML += `
                    <div class="model-card ${isBest ? 'best' : ''}">
                        ${isBest ? '<div class="best-badge"><i class="fa-solid fa-star"></i> BEST & TUNED</div>' : ''}
                        <h4>${name}</h4>
                        <div class="metric"><span>R² Score:</span><span class="metric-value">${metrics.r2?.toFixed(4) || 'N/A'}</span></div>
                        <div class="metric"><span>RMSE:</span><span class="metric-value">${metrics.rmse?.toLocaleString(undefined, {maximumFractionDigits: 0}) || 'N/A'}</span></div>
                        <div class="metric"><span>MAE:</span><span class="metric-value">${metrics.mae?.toLocaleString(undefined, {maximumFractionDigits: 0}) || 'N/A'}</span></div>
                    </div>
                `;
            });
            
            comparisonHTML += `</div>`;
        } else {
            comparisonHTML += `
                <div class="card">
                    <p style="text-align: center; color: var(--text-secondary);">
                        No model comparison data available. Please train the model first.
                    </p>
                </div>
            `;
        }
        
        container.innerHTML = comparisonHTML;
    }

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        if (!validateForm()) return;

        predictBtn.disabled = true;
        predictBtn.innerHTML = `<div class="spinner"></div> Predicting...`;
        resultDiv.classList.remove("hidden");
        resultDiv.innerHTML = `<div class="loading-placeholder"><div class="spinner"></div><p>AI is analyzing your profile...</p></div>`;
        
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());

        console.log("Form data before processing:", data);

        // Convert numeric fields to numbers
        for (const key in data) {
            if (['age', 'experience'].includes(key)) {
                data[key] = parseFloat(data[key]);
            }
        }

        console.log("Form data after processing:", data);

        try {
            const response = await fetch("/predict", {
                method: "POST",
                headers: { 
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify(data)
            });
            
            const result = await response.json();
            
            console.log("Prediction response:", response.status, result);
            
            if (!response.ok) {
                throw new Error(result.error || `Prediction failed with status ${response.status}`);
            }
            
            displayResult(result);
        } catch (error) {
            console.error("Prediction error:", error);
            displayError(error.message);
        } finally {
            predictBtn.disabled = false;
            predictBtn.innerHTML = `<i class="fa-solid fa-bolt"></i> Predict My Salary`;
        }
    });

    function displayResult(data) {
        const formattedSalary = data.predicted_salary.toLocaleString('en-IN', {
            style: 'currency', 
            currency: 'INR', 
            maximumFractionDigits: 0
        });
        
        resultDiv.innerHTML = `
            <div class="result-card">
                <h3>🎉 Predicted Monthly Salary</h3>
                <div class="salary-display">${formattedSalary}</div>
                <div class="model-badge">
                    <i class="fa-solid fa-microchip"></i> 
                    Powered by: ${data.model_used || 'AI Model'}
                </div>
                <p style="margin-top: 1rem; opacity: 0.9; font-size: 0.9rem;">
                    Based on your profile and industry standards
                </p>
            </div>`;
    }

    function displayError(message) {
        resultDiv.innerHTML = `
            <div class="card" style="text-align:center; border-left: 4px solid var(--danger);">
                <h4 style="color: var(--danger);">
                    <i class="fa-solid fa-triangle-exclamation"></i> Prediction Error
                </h4>
                <p style="color: var(--text-secondary); margin: 1rem 0;">${message}</p>
                <div style="background: var(--bg-input); padding: 1rem; border-radius: 8px; margin: 1rem 0;">
                    <p style="font-size: 0.9rem; color: var(--text-secondary); margin: 0;">
                        <strong>Tips:</strong>
                    </p>
                    <ul style="text-align: left; margin: 0.5rem 0; font-size: 0.9rem;">
                        <li>Ensure all fields are filled correctly</li>
                        <li>Check that age and experience are valid numbers</li>
                        <li>Make sure the model is trained (run train.py)</li>
                    </ul>
                </div>
            </div>`;
    }

    function validateForm() {
        const inputs = form.querySelectorAll('input[required], select[required]');
        let isValid = true;
        
        inputs.forEach(input => {
            if (!input.value.trim()) {
                isValid = false;
            }
            // Additional validation for numeric fields
            if (input.type === 'number' && input.value.trim() !== '') {
                const value = parseFloat(input.value);
                const min = parseFloat(input.min) || 0;
                const max = parseFloat(input.max) || 100;
                if (value < min || value > max) {
                    isValid = false;
                }
            }
        });
        
        predictBtn.disabled = !isValid;
        return isValid;
    }

    function formatLabel(text) {
        return text.replace(/_/g, ' ')
                  .replace(/\b\w/g, char => char.toUpperCase());
    }
});