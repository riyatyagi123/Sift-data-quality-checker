document.addEventListener('DOMContentLoaded', () => {
    const loader = document.getElementById('cleaningLoader');
    const dashboard = document.getElementById('cleanedDashboard');
    
    // Banner details
    const bannerProcessed = document.getElementById('bannerProcessed');
    const bannerRetained = document.getElementById('bannerRetained');
    const bannerRemoved = document.getElementById('bannerRemoved');
    const bannerCorrected = document.getElementById('bannerCorrected');
    const bannerRetentionRate = document.getElementById('bannerRetentionRate');
    const bannerCorrectionRate = document.getElementById('bannerCorrectionRate');
    
    // Stats Cards (Primary)
    const cleanTotal = document.getElementById('cleanTotal');
    const cleanCorrected = document.getElementById('cleanCorrected');
    const cleanRemoved = document.getElementById('cleanRemoved');
    const cleanRetained = document.getElementById('cleanRetained');
    const cleanRetentionRate = document.getElementById('cleanRetentionRate');
    const cleanCorrectionRate = document.getElementById('cleanCorrectionRate');
    
    // Stats Cards (Secondary elements)
    const cleanPhonesFixed = document.getElementById('cleanPhonesFixed');
    const cleanEmailsFixed = document.getElementById('cleanEmailsFixed');
    const cleanDatesFixed = document.getElementById('cleanDatesFixed');
    const cleanCurrenciesFixed = document.getElementById('cleanCurrenciesFixed');
    const cleanDuplicatesRemoved = document.getElementById('cleanDuplicatesRemoved');
    const cleanImputed = document.getElementById('cleanImputed');
    const cleanSuccessRate = document.getElementById('cleanSuccessRate');
    
    // Selection and Rerun Elements
    const cleaningModeSelect = document.getElementById('cleaningModeSelect');
    const rerunCleaningBtn = document.getElementById('rerunCleaningBtn');
    const cleaningLogBody = document.getElementById('cleaningLogBody');

    // Audit Log Controls
    const auditSearchInput = document.getElementById('auditSearchInput');
    const auditSeverityFilter = document.getElementById('auditSeverityFilter');
    const auditActionFilter = document.getElementById('auditActionFilter');

    let currentAuditTrail = [];

    // Run clean engine initially on load
    runCleaning(cleaningModeSelect ? cleaningModeSelect.value : 'SMART');

    if (rerunCleaningBtn) {
        rerunCleaningBtn.addEventListener('click', () => {
            const selectedMode = cleaningModeSelect.value;
            runCleaning(selectedMode);
        });
    }

    if (auditSearchInput) {
        auditSearchInput.addEventListener('input', renderAuditTable);
    }
    if (auditSeverityFilter) {
        auditSeverityFilter.addEventListener('change', renderAuditTable);
    }
    if (auditActionFilter) {
        auditActionFilter.addEventListener('change', renderAuditTable);
    }

    function runCleaning(mode) {
        loader.classList.remove('hidden');
        dashboard.classList.add('hidden');

        fetch('/clean/run', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ mode: mode })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            populateDashboard(data);
        })
        .catch(err => {
            console.error('Cleaning Error:', err);
            alert('Failed to clean CSV dataset. Ensure the data file exists and contains valid tabular structures.');
            loader.classList.add('hidden');
        });
    }

    function populateDashboard(data) {
        const stats = data.stats || data;
        
        const processed = stats.total_processed || 0;
        const retained = stats.rows_retained || 0;
        const removed = stats.rows_removed || 0;
        const corrected = stats.rows_corrected || 0;

        const retRateVal = processed > 0 ? ((retained / processed) * 100).toFixed(1) : '100.0';
        const corRateVal = processed > 0 ? ((corrected / processed) * 100).toFixed(1) : '0.0';

        // Update banner text
        if (bannerProcessed) bannerProcessed.textContent = processed.toLocaleString();
        if (bannerRetained) bannerRetained.textContent = retained.toLocaleString();
        if (bannerRemoved) bannerRemoved.textContent = removed.toLocaleString();
        if (bannerCorrected) bannerCorrected.textContent = corrected.toLocaleString();
        if (bannerRetentionRate) bannerRetentionRate.textContent = `${retRateVal}%`;
        if (bannerCorrectionRate) bannerCorrectionRate.textContent = `${corRateVal}%`;
        
        const dateFormatInfo = document.getElementById('dateFormatInfo');
        const dateConfidenceInfo = document.getElementById('dateConfidenceInfo');
        const dateConfidenceWrapper = document.getElementById('dateConfidenceWrapper');

        if (window.hasDateColumn && stats.detected_date_format && stats.detected_date_format !== 'unknown') {
            if (dateFormatInfo) {
                dateFormatInfo.textContent = stats.detected_date_format;
                dateFormatInfo.className = "text-emerald-700 font-bold";
            }
            if (dateConfidenceInfo) dateConfidenceInfo.textContent = stats.date_confidence_score || '0%';
            if (dateConfidenceWrapper) dateConfidenceWrapper.classList.remove('hidden');
        } else {
            if (dateFormatInfo) {
                dateFormatInfo.textContent = 'No date columns detected';
                dateFormatInfo.className = "text-slate-500 font-bold";
            }
            if (dateConfidenceWrapper) dateConfidenceWrapper.classList.add('hidden');
        }

        // Update primary card metrics
        if (cleanTotal) cleanTotal.textContent = processed.toLocaleString();
        if (cleanRetained) cleanRetained.textContent = retained.toLocaleString();
        if (cleanRemoved) cleanRemoved.textContent = removed.toLocaleString();
        if (cleanCorrected) cleanCorrected.textContent = corrected.toLocaleString();
        if (cleanRetentionRate) cleanRetentionRate.textContent = `${retRateVal}%`;
        if (cleanCorrectionRate) cleanCorrectionRate.textContent = `${corRateVal}%`;

        // Setup secondary metrics visibility
        const secondaryMetrics = [
            { id: 'cardPhonesFixed', val: stats.phones_fixed || 0, el: cleanPhonesFixed },
            { id: 'cardEmailsFixed', val: stats.emails_fixed || 0, el: cleanEmailsFixed },
            { id: 'cardDatesFixed', val: stats.dates_fixed || 0, el: cleanDatesFixed },
            { id: 'cardCurrenciesFixed', val: stats.currencies_fixed || 0, el: cleanCurrenciesFixed },
            { id: 'cardDuplicatesRemoved', val: stats.duplicates_removed || 0, el: cleanDuplicatesRemoved },
            { id: 'cardImputed', val: stats.rows_imputed || 0, el: cleanImputed },
            { id: 'cardSuccessRate', val: stats.success_rate || 0, el: cleanSuccessRate }
        ];

        let anySecondaryVisible = false;
        secondaryMetrics.forEach(metric => {
            const card = document.getElementById(metric.id);
            if (card) {
                if (metric.val > 0) {
                    card.classList.remove('hidden');
                    anySecondaryVisible = true;
                    if (metric.el) {
                        if (metric.id === 'cardSuccessRate') {
                            metric.el.textContent = `${metric.val}%`;
                        } else {
                            metric.el.textContent = metric.val.toLocaleString();
                        }
                    }
                } else {
                    card.classList.add('hidden');
                }
            }
        });

        const secondaryMetricsSection = document.getElementById('secondaryMetricsSection');
        if (secondaryMetricsSection) {
            if (anySecondaryVisible) {
                secondaryMetricsSection.classList.remove('hidden');
            } else {
                secondaryMetricsSection.classList.add('hidden');
            }
        }

        // Populate Audit Trail Table data
        currentAuditTrail = data.audit_trail || [];

        // Collect unique actions to populate Action Filter dropdown
        const uniqueActions = new Set();
        currentAuditTrail.forEach(entry => {
            if (entry.action) {
                uniqueActions.add(entry.action);
            }
        });
        
        if (auditActionFilter) {
            auditActionFilter.innerHTML = '<option value="ALL">All Actions</option>';
            Array.from(uniqueActions).sort().forEach(action => {
                const option = document.createElement('option');
                option.value = action;
                option.textContent = action.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
                auditActionFilter.appendChild(option);
            });
        }

        // Initial render
        renderAuditTable();

        // Switch screens
        loader.classList.add('hidden');
        dashboard.classList.remove('hidden');
    }

    function renderAuditTable() {
        if (!cleaningLogBody) return;
        cleaningLogBody.innerHTML = '';

        const searchQuery = (auditSearchInput ? auditSearchInput.value : '').toLowerCase().trim();
        const severityFilter = auditSeverityFilter ? auditSeverityFilter.value : 'ALL';
        const actionFilter = auditActionFilter ? auditActionFilter.value : 'ALL';

        const filtered = currentAuditTrail.filter(entry => {
            // Severity filter
            if (severityFilter !== 'ALL' && (entry.severity || 'INFO') !== severityFilter) {
                return false;
            }
            
            // Action filter
            if (actionFilter !== 'ALL' && entry.action !== actionFilter) {
                return false;
            }

            // Search query
            if (searchQuery) {
                const rowStr = String(entry.row || '');
                const colStr = String(entry.column || '').toLowerCase();
                const origStr = String(entry.original || '').toLowerCase();
                const cleanStr = String(entry.cleaned || '').toLowerCase();
                const actStr = String(entry.action || '').toLowerCase().replace(/_/g, ' ');
                const actOrigStr = String(entry.action || '').toLowerCase();
                const sevStr = String(entry.severity || 'INFO').toLowerCase();

                if (!rowStr.includes(searchQuery) &&
                    !colStr.includes(searchQuery) &&
                    !origStr.includes(searchQuery) &&
                    !cleanStr.includes(searchQuery) &&
                    !actStr.includes(searchQuery) &&
                    !actOrigStr.includes(searchQuery) &&
                    !sevStr.includes(searchQuery)) {
                    return false;
                }
            }

            return true;
        });

        if (filtered.length > 0) {
            filtered.forEach(entry => {
                const tr = document.createElement('tr');
                tr.className = "hover:bg-slate-50/50 border-b border-slate-50 h-10";
                
                const tdRow = document.createElement('td');
                tdRow.className = "px-4 py-2 font-mono text-sm text-slate-500 font-bold";
                tdRow.textContent = entry.row;
                tr.appendChild(tdRow);
                
                const tdCol = document.createElement('td');
                tdCol.className = "px-4 py-2 font-mono text-sm text-slate-700 font-bold";
                tdCol.textContent = entry.column;
                tr.appendChild(tdCol);
                
                const tdOrig = document.createElement('td');
                tdOrig.className = "px-4 py-2 text-rose-600 font-mono text-sm truncate max-w-[150px]";
                tdOrig.textContent = entry.original === "" ? "NULL" : entry.original;
                tr.appendChild(tdOrig);
                
                const tdClean = document.createElement('td');
                tdClean.className = "px-4 py-2 text-emerald-600 font-mono text-sm font-bold truncate max-w-[150px]";
                tdClean.textContent = entry.cleaned === "" ? "NULL" : entry.cleaned;
                tr.appendChild(tdClean);
                
                const tdAction = document.createElement('td');
                tdAction.className = "px-4 py-2 text-slate-600 text-sm";
                tdAction.textContent = entry.action.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
                tr.appendChild(tdAction);
                
                const tdSev = document.createElement('td');
                tdSev.className = "px-4 py-2 text-center";
                const sev = entry.severity || 'INFO';
                const badge = document.createElement('span');
                badge.className = "px-2 py-0.5 rounded-full text-xs font-extrabold uppercase border shadow-sm";
                if (sev === 'CRITICAL' || sev === 'ERROR') {
                    badge.classList.add('bg-rose-50', 'text-rose-800', 'border-rose-100');
                } else if (sev === 'WARNING') {
                    badge.classList.add('bg-amber-50', 'text-amber-800', 'border-amber-100');
                } else {
                    badge.classList.add('bg-slate-50', 'text-slate-600', 'border-slate-100');
                }
                badge.textContent = sev;
                tdSev.appendChild(badge);
                tr.appendChild(tdSev);
                
                cleaningLogBody.appendChild(tr);
            });
        } else {
            cleaningLogBody.innerHTML = `
                <tr>
                    <td colspan="6" class="px-4 py-8 text-center text-slate-400 italic">No matching records found.</td>
                </tr>
            `;
        }
    }
});
