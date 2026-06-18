document.addEventListener('DOMContentLoaded', () => {
    const loader = document.getElementById('validationLoader');
    const dashboard = document.getElementById('validationDashboard');
    const rerunBtn = document.getElementById('rerunBtn');
    
    // Score Widgets
    const ring = document.getElementById('scoreProgressRing');
    const overallScoreText = document.getElementById('overallScoreText');
    const completenessScoreText = document.getElementById('completenessScoreText');
    const completenessProgressBar = document.getElementById('completenessProgressBar');
    const validityScoreText = document.getElementById('validityScoreText');
    const validityProgressBar = document.getElementById('validityProgressBar');
    const uniquenessScoreText = document.getElementById('uniquenessScoreText');
    const uniquenessProgressBar = document.getElementById('uniquenessProgressBar');

    // Stats
    const statTotal = document.getElementById('statTotal');
    const statValid = document.getElementById('statValid');
    const statInvalid = document.getElementById('statInvalid');
    const statRate = document.getElementById('statRate');
    
    // Profile Cards
    const profileColCount = document.getElementById('profileColCount');
    const profileDatasetType = document.getElementById('profileDatasetType');
    const profileColumnsBody = document.getElementById('profileColumnsBody');
    
    // Expectation Cards
    const cards = {
        email: document.getElementById('cardEmailExp'),
        phone: document.getElementById('cardPhoneExp'),
        date: document.getElementById('cardDateExp'),
        txn: document.getElementById('cardTxnRulesExp')
    };

    // Issue logs
    const issueLogsSection = document.getElementById('issueLogsSection');
    const issueLogsRows = document.getElementById('issueLogsRows');
    const noIssuesAlert = document.getElementById('noIssuesAlert');

    // Run validation immediately on load
    runValidation();

    rerunBtn.addEventListener('click', () => {
        runValidation();
    });

    function runValidation() {
        loader.classList.remove('hidden');
        dashboard.classList.add('hidden');
        issueLogsSection.classList.add('hidden');
        noIssuesAlert.classList.add('hidden');
        
        const startTime = performance.now();
        fetch('/validate/run', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            const endTime = performance.now();
            const durationSec = ((endTime - startTime) / 1000).toFixed(1);
            data.processed_time_sec = durationSec;
            console.log(data);
            populateDashboard(data);
        })
        .catch(err => {
            console.error('Validation Error:', err);
            alert('Failed to execute validation rules. Please ensure your CSV format is valid.');
            loader.classList.add('hidden');
        });
    }

    function updateBadge(badge, status) {
        if (!badge) return;
        badge.textContent = status;
        badge.className = "px-2 py-0.5 rounded text-xs font-extrabold uppercase border shadow-sm";
        if (status === 'PASSED') {
            badge.classList.add('bg-emerald-50', 'text-emerald-800', 'border-emerald-100');
        } else if (status === 'FAILED') {
            badge.classList.add('bg-rose-50', 'text-rose-800', 'border-rose-100');
        } else if (status === 'WARNING') {
            badge.classList.add('bg-amber-50', 'text-amber-800', 'border-amber-100');
        } else {
            badge.classList.add('bg-slate-100', 'text-slate-500', 'border-slate-200/50');
        }
    }

    function populateDashboard(data) {
        // --- 0. Top Summary Cards Data Binding & Header Metadata ---
        const cardTotalRows = document.getElementById('cardTotalRows');
        const cardTotalCols = document.getElementById('cardTotalCols');
        const cardFilesize = document.getElementById('cardFilesize');
        const cardDatasetType = document.getElementById('cardDatasetType');
        const cardConfidence = document.getElementById('cardConfidence');
        const cardValidRows = document.getElementById('cardValidRows');
        const cardInvalidRows = document.getElementById('cardInvalidRows');
        const cardSuccessRate = document.getElementById('cardSuccessRate');
        const cardEmptyCols = document.getElementById('cardEmptyCols');
        const cardOverallScore = document.getElementById('cardOverallScore');

        // Header Metadata
        const headerDatasetType = document.getElementById('headerDatasetType');
        const headerTotalRows = document.getElementById('headerTotalRows');
        const headerFilesize = document.getElementById('headerFilesize');
        const headerProcessedTime = document.getElementById('headerProcessedTime');

        if (headerDatasetType) headerDatasetType.textContent = data.dataset_type || 'Unknown Type';
        if (headerTotalRows) headerTotalRows.textContent = `${(data.total_records !== undefined ? data.total_records : 0).toLocaleString()} rows`;
        
        let sizeStr = '0 KB';
        if (data.filesize_kb !== undefined) {
            if (data.filesize_kb >= 1024) {
                sizeStr = `${(data.filesize_kb / 1024).toFixed(2)} MB`;
            } else {
                sizeStr = `${data.filesize_kb} KB`;
            }
        }
        if (headerFilesize) headerFilesize.textContent = sizeStr;
        if (headerProcessedTime) headerProcessedTime.textContent = `Processed in ${data.processed_time_sec || '0.0'} sec`;

        if (cardTotalRows) cardTotalRows.textContent = (data.total_records !== undefined ? data.total_records : 0).toLocaleString();
        if (cardTotalCols) cardTotalCols.textContent = data.column_types ? Object.keys(data.column_types).length : 0;
        if (cardFilesize) cardFilesize.textContent = sizeStr;
        if (cardDatasetType) cardDatasetType.textContent = data.dataset_type || 'Unknown';
        if (cardConfidence) {
            const confVal = data.schema_confidence !== undefined ? data.schema_confidence : 100;
            cardConfidence.textContent = confVal + '%';
        }
        if (cardValidRows) cardValidRows.textContent = (data.valid_records !== undefined ? data.valid_records : 0).toLocaleString();
        if (cardInvalidRows) cardInvalidRows.textContent = (data.invalid_records !== undefined ? data.invalid_records : 0).toLocaleString();
        if (cardSuccessRate) cardSuccessRate.textContent = (data.success_rate !== undefined ? data.success_rate : 100) + '%';
        
        let emptyColsCount = 0;
        if (data.column_completeness) {
            Object.values(data.column_completeness).forEach(comp => {
                if (comp === 0) {
                    emptyColsCount++;
                }
            });
        }
        if (cardEmptyCols) cardEmptyCols.textContent = emptyColsCount;
        if (cardOverallScore) cardOverallScore.textContent = (data.overall_score !== undefined ? data.overall_score : 100) + '%';

        // Card Subtitles/Details
        const cardOverallScoreSub = document.getElementById('cardOverallScoreSub');
        if (cardOverallScoreSub) {
            cardOverallScoreSub.textContent = data.quality_rating || 'Fair Quality';
        }
        
        const cardSuccessRateSub = document.getElementById('cardSuccessRateSub');
        if (cardSuccessRateSub) {
            const validCount = data.valid_records !== undefined ? data.valid_records : 0;
            const totalCount = data.total_records !== undefined ? data.total_records : 0;
            cardSuccessRateSub.textContent = `${validCount.toLocaleString()} / ${totalCount.toLocaleString()} rows valid`;
        }

        const cardInvalidRowsSub = document.getElementById('cardInvalidRowsSub');
        if (cardInvalidRowsSub) {
            const invalidCount = data.invalid_records !== undefined ? data.invalid_records : 0;
            cardInvalidRowsSub.textContent = invalidCount === 0 ? 'No issues' : `${invalidCount.toLocaleString()} rows failed`;
        }

        const cardConfidenceSub = document.getElementById('cardConfidenceSub');
        if (cardConfidenceSub) {
            const confidenceVal = data.schema_confidence !== undefined ? data.schema_confidence : 100;
            cardConfidenceSub.textContent = confidenceVal >= 90 ? 'High certainty' : (confidenceVal >= 70 ? 'Moderate certainty' : 'Low certainty');
        }

        // --- 1. Overall Quality Gauge & Dimensions ---
        const score = data.overall_score !== undefined ? data.overall_score : 100;
        if (overallScoreText) overallScoreText.textContent = `${score}%`;
        if (ring) {
            const offset = 251.2 - (score / 100) * 251.2;
            ring.style.strokeDashoffset = offset;

            // Colors based on score thresholds
            if (score >= 90) {
                ring.className.baseVal = "text-emerald-500 transition-all duration-700 ease-out";
            } else if (score >= 70) {
                ring.className.baseVal = "text-amber-500 transition-all duration-700 ease-out";
            } else {
                ring.className.baseVal = "text-rose-500 transition-all duration-700 ease-out";
            }
        }

        const comp = data.completeness_score !== undefined ? data.completeness_score : 100;
        if (completenessScoreText) completenessScoreText.textContent = `${comp}%`;
        if (completenessProgressBar) completenessProgressBar.style.width = `${comp}%`;
        const completenessDesc = document.getElementById('completenessDesc');
        if (completenessDesc) {
            completenessDesc.textContent = comp >= 95 ? 'Almost complete' : (comp >= 80 ? 'Partially complete' : 'Needs improvement');
        }

        const val = data.validity_score !== undefined ? data.validity_score : 100;
        if (validityScoreText) validityScoreText.textContent = `${val}%`;
        if (validityProgressBar) validityProgressBar.style.width = `${val}%`;
        const validityDesc = document.getElementById('validityDesc');
        if (validityDesc) {
            validityDesc.textContent = val >= 95 ? 'Valid data' : (val >= 80 ? 'Partially valid' : 'Needs improvement');
        }

        const uniq = data.uniqueness_score !== undefined ? data.uniqueness_score : 100;
        if (uniquenessScoreText) uniquenessScoreText.textContent = `${uniq}%`;
        if (uniquenessProgressBar) uniquenessProgressBar.style.width = `${uniq}%`;
        const uniquenessDesc = document.getElementById('uniquenessDesc');
        if (uniquenessDesc) {
            uniquenessDesc.textContent = uniq >= 95 ? 'Duplicate free' : (uniq >= 80 ? 'Partially unique' : 'Contains duplicates');
        }

        const qualitySummaryLabel = document.getElementById('qualitySummaryLabel');
        if (qualitySummaryLabel) {
            qualitySummaryLabel.textContent = data.quality_rating || 'Fair Quality';
        }

        // --- 2. Stats Breakdown ---
        if (statTotal) statTotal.textContent = data.total_records.toLocaleString();
        if (statValid) statValid.textContent = data.valid_records.toLocaleString();
        if (statInvalid) statInvalid.textContent = data.invalid_records.toLocaleString();
        if (statRate) statRate.textContent = `${data.success_rate}%`;

        // --- 3. Dataset Profile ---
        if (profileColCount) profileColCount.textContent = Object.keys(data.column_types || {}).length;
        if (profileDatasetType) profileDatasetType.textContent = data.dataset_type || "Unknown Dataset";

        const profileDateFormat = document.getElementById('profileDateFormat');
        if (profileDateFormat) {
            profileDateFormat.textContent = (data.date_profile && data.date_profile.detected_format) || 'N/A';
        }
        const profileDateConfidence = document.getElementById('profileDateConfidence');
        if (profileDateConfidence) {
            profileDateConfidence.textContent = (data.date_profile && data.date_profile.confidence) || '0%';
        }

        // Columns List Table
        profileColumnsBody.innerHTML = '';
        if (data.column_types) {
            Object.keys(data.column_types).forEach(col => {
                const type = data.column_types[col];
                const completeness = data.column_completeness ? data.column_completeness[col] : 100;
                
                const tr = document.createElement('tr');
                tr.className = "hover:bg-slate-50/50";
                
                const tdName = document.createElement('td');
                tdName.className = "px-4 py-2 font-mono text-sm text-slate-700";
                tdName.textContent = col;
                tr.appendChild(tdName);
                
                const tdType = document.createElement('td');
                tdType.className = "px-4 py-2";
                const badge = document.createElement('span');
                badge.className = "inline-block px-1.5 py-0.5 rounded text-xs font-bold bg-slate-100 text-slate-600 uppercase";
                badge.textContent = type;
                
                // Colorize common type badges
                if (type === 'Email') badge.className = "inline-block px-1.5 py-0.5 rounded text-xs font-bold bg-indigo-50 text-indigo-700 border border-indigo-100 uppercase";
                if (type === 'Phone') badge.className = "inline-block px-1.5 py-0.5 rounded text-xs font-bold bg-purple-50 text-purple-700 border border-purple-100 uppercase";
                if (type === 'Date') badge.className = "inline-block px-1.5 py-0.5 rounded text-xs font-bold bg-blue-50 text-blue-700 border border-blue-100 uppercase";
                if (type === 'Numeric') badge.className = "inline-block px-1.5 py-0.5 rounded text-xs font-bold bg-amber-50 text-amber-700 border border-amber-100 uppercase";
                
                tdType.appendChild(badge);
                tr.appendChild(tdType);
                
                const tdComplete = document.createElement('td');
                tdComplete.className = "px-4 py-2 font-semibold text-slate-500 text-sm";
                tdComplete.innerHTML = `
                    <div class="flex items-center space-x-2">
                        <span>${completeness}%</span>
                        <div class="w-12 h-1 bg-slate-100 rounded-full overflow-hidden">
                            <div class="h-full bg-emerald-500" style="width: ${completeness}%"></div>
                        </div>
                    </div>
                `;
                tr.appendChild(tdComplete);
                
                profileColumnsBody.appendChild(tr);
            });
        }

        // --- 4. Expectation Suites ---
        
        // A. Completeness Card
        const compStatus = data.rule_status['mandatory'] === 'FAILED' || data.rule_status['integrity'] === 'FAILED' ? 'FAILED' : 'PASSED';
        updateBadge(document.getElementById('badgeCompleteness'), compStatus);
        document.getElementById('scoreCompleteness').textContent = `${comp}%`;
        document.getElementById('chkCompleteness').textContent = data.total_records.toLocaleString();
        
        // Sum total missing cells
        let totalMissing = 0;
        if (data.column_completeness) {
            Object.values(data.column_completeness).forEach(pct => {
                totalMissing += Math.round(((100 - pct) / 100) * data.total_records);
            });
        }
        document.getElementById('affCompleteness').textContent = totalMissing.toLocaleString();
        
        const failCompleteness = document.getElementById('failCompleteness');
        if (failCompleteness) failCompleteness.textContent = totalMissing.toLocaleString();
        const reasonCompleteness = document.getElementById('reasonCompleteness');
        if (reasonCompleteness) {
            reasonCompleteness.textContent = totalMissing > 0 ? `${totalMissing} missing values` : 'No missing values';
        }

        // Populate completeness Column Bars
        const compColumnBars = document.getElementById('completenessColumnBars');
        compColumnBars.innerHTML = '';
        if (data.column_completeness) {
            Object.keys(data.column_completeness).forEach(col => {
                const pct = data.column_completeness[col];
                const bar = document.createElement('div');
                bar.className = "flex items-center justify-between text-sm font-medium p-1 border border-slate-50 rounded bg-slate-50/20";
                bar.innerHTML = `
                    <span class="font-mono text-slate-500 truncate max-w-[150px]">${col}</span>
                    <div class="flex items-center space-x-2 flex-shrink-0">
                        <span class="${pct === 100 ? 'text-emerald-600 font-bold' : 'text-amber-500 font-bold'}">${pct}%</span>
                        <div class="w-16 h-1 bg-slate-100 rounded-full overflow-hidden">
                            <div class="h-full ${pct === 100 ? 'bg-emerald-500' : 'bg-amber-400'}" style="width: ${pct}%"></div>
                        </div>
                    </div>
                `;
                compColumnBars.appendChild(bar);
            });
        }

        // B. Email Card
        const hasEmail = data.column_mapping && data.column_mapping['email'];
        if (hasEmail && data.email_profile) {
            cards.email.classList.remove('hidden');
            const emailStatus = data.rule_status['email'] || 'PASSED';
            updateBadge(document.getElementById('badgeEmail'), emailStatus);
            
            const emailPresent = data.total_records - data.email_profile.missing_count;
            const emailScoreVal = emailPresent > 0 ? Math.round((emailPresent - data.email_profile.invalid_count) / emailPresent * 100) : 100;
            document.getElementById('scoreEmail').textContent = `${emailScoreVal}%`;
            document.getElementById('chkEmail').textContent = emailPresent.toLocaleString();
            document.getElementById('affEmail').textContent = data.email_profile.invalid_count.toLocaleString();
            document.getElementById('missEmail').textContent = data.email_profile.missing_count.toLocaleString();
            
            const failEmail = document.getElementById('failEmail');
            if (failEmail) failEmail.textContent = data.email_profile.invalid_count.toLocaleString();
            const reasonEmail = document.getElementById('reasonEmail');
            if (reasonEmail) {
                reasonEmail.textContent = data.email_profile.invalid_count > 0 ? `${data.email_profile.invalid_count} invalid emails` : 'All emails valid';
            }

            const examplesList = document.getElementById('emailExamplesList');
            examplesList.innerHTML = '';
            if (data.email_profile.examples && data.email_profile.examples.length > 0) {
                document.getElementById('emailExamplesDiv').classList.remove('hidden');
                data.email_profile.examples.forEach(ex => {
                    const span = document.createElement('span');
                    span.className = "px-2 py-0.5 bg-rose-50 text-rose-700 rounded font-mono text-xs border border-rose-100/50";
                    span.textContent = ex || "(empty)";
                    examplesList.appendChild(span);
                });
            } else {
                document.getElementById('emailExamplesDiv').classList.add('hidden');
            }
        } else {
            cards.email.classList.add('hidden');
        }

        // C. Phone Card
        const hasPhone = data.column_mapping && data.column_mapping['phone_number'];
        if (hasPhone && data.phone_profile) {
            cards.phone.classList.remove('hidden');
            const phoneStatus = data.rule_status['phone'] || 'PASSED';
            updateBadge(document.getElementById('badgePhone'), phoneStatus);
            
            const phoneCount = data.total_records; // Approximate checked
            const phoneScoreVal = phoneCount > 0 ? Math.round((phoneCount - data.phone_profile.invalid_count) / phoneCount * 100) : 100;
            document.getElementById('scorePhone').textContent = `${phoneScoreVal}%`;
            
            document.getElementById('chkPhone').textContent = phoneCount.toLocaleString();
            document.getElementById('affectedPhone').textContent = data.phone_profile.invalid_count.toLocaleString();
            
            const failPhone = document.getElementById('failPhone');
            if (failPhone) failPhone.textContent = data.phone_profile.invalid_count.toLocaleString();
            const reasonPhone = document.getElementById('reasonPhone');
            if (reasonPhone) {
                reasonPhone.textContent = data.phone_profile.invalid_count > 0 ? `${data.phone_profile.invalid_count} invalid numbers` : 'All numbers valid';
            }

            const examplesList = document.getElementById('phoneExamplesList');
            examplesList.innerHTML = '';
            if (data.phone_profile.examples && data.phone_profile.examples.length > 0) {
                document.getElementById('phoneExamplesDiv').classList.remove('hidden');
                data.phone_profile.examples.forEach(ex => {
                    const span = document.createElement('span');
                    span.className = "px-2 py-0.5 bg-rose-50 text-rose-700 rounded font-mono text-xs border border-rose-100/50";
                    span.textContent = ex || "(empty)";
                    examplesList.appendChild(span);
                });
            } else {
                document.getElementById('phoneExamplesDiv').classList.add('hidden');
            }
        } else {
            cards.phone.classList.add('hidden');
        }

        // D. Date Card
        const hasDate = data.column_mapping && data.column_mapping['transaction_date'];
        if (hasDate && data.date_profile) {
            cards.date.classList.remove('hidden');
            const dateStatus = data.rule_status['date'] || 'PASSED';
            updateBadge(document.getElementById('badgeDate'), dateStatus);
            
            const dateScoreVal = data.total_records > 0 ? Math.round((data.total_records - data.date_profile.invalid_count) / data.total_records * 100) : 100;
            document.getElementById('scoreDate').textContent = `${dateScoreVal}%`;
            
            document.getElementById('chkDate').textContent = data.total_records.toLocaleString();
            document.getElementById('affectedDate').textContent = data.date_profile.invalid_count.toLocaleString();
            document.getElementById('dateDetectedFormat').textContent = data.date_profile.detected_format || 'Unknown';
            document.getElementById('dateMinVal').textContent = data.date_profile.min_date || 'N/A';
            document.getElementById('dateMaxVal').textContent = data.date_profile.max_date || 'N/A';
            
            const failDate = document.getElementById('failDate');
            if (failDate) failDate.textContent = data.date_profile.invalid_count.toLocaleString();
            const reasonDate = document.getElementById('reasonDate');
            if (reasonDate) {
                reasonDate.textContent = data.date_profile.invalid_count > 0 ? `${data.date_profile.invalid_count} invalid dates` : 'All dates valid';
            }

            const examplesList = document.getElementById('dateExamplesList');
            examplesList.innerHTML = '';
            if (data.date_profile.examples && data.date_profile.examples.length > 0) {
                document.getElementById('dateExamplesDiv').classList.remove('hidden');
                data.date_profile.examples.forEach(ex => {
                    const span = document.createElement('span');
                    span.className = "px-2 py-0.5 bg-rose-50 text-rose-700 rounded font-mono text-xs border border-rose-100/50";
                    span.textContent = ex || "(empty)";
                    examplesList.appendChild(span);
                });
            } else {
                document.getElementById('dateExamplesDiv').classList.add('hidden');
            }
        } else {
            cards.date.classList.add('hidden');
        }

        // E. Duplicates Card
        const dupStatus = data.rule_status['duplicates'] === 'FAILED' ? 'FAILED' : 'PASSED';
        updateBadge(document.getElementById('badgeDuplicates'), dupStatus);
        document.getElementById('scoreDuplicates').textContent = `${uniq}%`;
        document.getElementById('chkDuplicates').textContent = data.total_records.toLocaleString();
        
        const dupIdsCountEl = document.getElementById('dupIdsCount');
        if (dupIdsCountEl) {
            dupIdsCountEl.textContent = data.duplicate_profile.duplicate_ids_count.toLocaleString();
        }
        const dupIdsExamplesEl = document.getElementById('dupIdsExamples');
        if (dupIdsExamplesEl) {
            dupIdsExamplesEl.textContent = data.duplicate_profile.duplicate_ids_examples.length > 0
                ? `e.g. ${data.duplicate_profile.duplicate_ids_examples.join(', ')}`
                : 'No duplicates';
        }
            
        const dupEmailsCountEl = document.getElementById('dupEmailsCount');
        if (dupEmailsCountEl) {
            dupEmailsCountEl.textContent = data.duplicate_profile.duplicate_emails_count.toLocaleString();
        }
        const dupEmailsExamplesEl = document.getElementById('dupEmailsExamples');
        if (dupEmailsExamplesEl) {
            dupEmailsExamplesEl.textContent = data.duplicate_profile.duplicate_emails_examples.length > 0
                ? `e.g. ${data.duplicate_profile.duplicate_emails_examples.join(', ')}`
                : 'No duplicates';
        }
            
        const dupPhonesCountEl = document.getElementById('dupPhonesCount');
        if (dupPhonesCountEl) {
            dupPhonesCountEl.textContent = data.duplicate_profile.duplicate_phones_count.toLocaleString();
        }
        const dupPhonesExamplesEl = document.getElementById('dupPhonesExamples');
        if (dupPhonesExamplesEl) {
            dupPhonesExamplesEl.textContent = data.duplicate_profile.duplicate_phones_examples.length > 0
                ? `e.g. ${data.duplicate_profile.duplicate_phones_examples.join(', ')}`
                : 'No duplicates';
        }

        const failDuplicates = document.getElementById('failDuplicates');
        if (failDuplicates) failDuplicates.textContent = data.duplicate_profile.duplicate_ids_count.toLocaleString();
        const reasonDuplicates = document.getElementById('reasonDuplicates');
        if (reasonDuplicates) {
            reasonDuplicates.textContent = data.duplicate_profile.duplicate_ids_count > 0 ? `${data.duplicate_profile.duplicate_ids_count} duplicate IDs` : 'All keys unique';
        }

        // F. Transaction Rules Card
        if (data.dataset_type !== "Customer Dataset") {
            cards.txn.classList.remove('hidden');
            
            const txnStatus = data.rule_status['currency'] === 'FAILED' || data.rule_status['payment_mode'] === 'FAILED' ? 'FAILED' : 'PASSED';
            updateBadge(document.getElementById('badgeTxnRules'), txnStatus);
            document.getElementById('scoreTxnRules').textContent = `${val}%`;

            updateBadge(document.getElementById('badgeCurrency'), data.rule_status['currency'] || 'PASSED');
            document.getElementById('affectedCurrency').textContent = data.affected_rows['currency'].toLocaleString();
            
            updateBadge(document.getElementById('badgePaymentMode'), data.rule_status['payment_mode'] || 'PASSED');
            document.getElementById('affectedPaymentMode').textContent = data.affected_rows['payment_mode'].toLocaleString();
            
            // Amount integrity status
            const amtIssues = data.issue_summary ? data.issue_summary.some(x => x.column === (data.column_mapping && data.column_mapping['amount'])) : false;
            const amtStatusBadge = document.getElementById('badgeAmount');
            updateBadge(amtStatusBadge, amtIssues ? 'FAILED' : 'PASSED');
            
            // Amount affected
            let amtAffected = 0;
            if (data.issue_summary) {
                const amtRule = data.issue_summary.find(x => x.column === (data.column_mapping && data.column_mapping['amount']));
                if (amtRule) amtAffected = amtRule.count;
            }
            document.getElementById('affectedAmount').textContent = amtAffected.toLocaleString();

            const failTxnRulesVal = (data.affected_rows['currency'] || 0) + (data.affected_rows['payment_mode'] || 0) + amtAffected;
            const failTxnRules = document.getElementById('failTxnRules');
            if (failTxnRules) failTxnRules.textContent = failTxnRulesVal.toLocaleString();
            const reasonTxnRules = document.getElementById('reasonTxnRules');
            if (reasonTxnRules) {
                reasonTxnRules.textContent = failTxnRulesVal > 0 ? `${failTxnRulesVal} txn issues` : 'All metrics valid';
            }
        } else {
            cards.txn.classList.add('hidden');
        }

        // --- 5. Aggregated Issue Logs Table ---
        issueLogsRows.innerHTML = '';
        if (data.issue_summary && data.issue_summary.length > 0) {
            data.issue_summary.forEach(issue => {
                const tr = document.createElement('tr');
                tr.className = 'hover:bg-slate-50/50';

                // Expectation Rule
                const tdRule = document.createElement('td');
                tdRule.className = 'px-4 py-3 font-mono text-sm text-slate-500 font-bold';
                tdRule.textContent = issue.rule;
                tr.appendChild(tdRule);

                // Column
                const tdCol = document.createElement('td');
                tdCol.className = 'px-4 py-3 font-mono text-sm text-slate-600 font-bold';
                tdCol.textContent = issue.column || 'N/A';
                tr.appendChild(tdCol);

                // Message Detail
                const tdMsg = document.createElement('td');
                tdMsg.className = 'px-4 py-3 text-slate-700 font-semibold';
                tdMsg.textContent = issue.message;
                tr.appendChild(tdMsg);

                // Severity
                const tdSeverity = document.createElement('td');
                tdSeverity.className = 'px-4 py-3 text-center';
                const sevBadge = document.createElement('span');
                const sev = (issue.severity || 'ERROR').toUpperCase();
                let sevClass = '';
                if (sev === 'CRITICAL') {
                    sevClass = 'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-extrabold bg-rose-100 text-rose-950 border border-rose-300 shadow-sm';
                } else if (sev === 'ERROR') {
                    sevClass = 'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-extrabold bg-red-100 text-red-900 border border-red-200 shadow-sm';
                } else if (sev === 'WARNING') {
                    sevClass = 'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-extrabold bg-amber-100 text-amber-950 border border-amber-300 shadow-sm';
                } else { // INFO
                    sevClass = 'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-extrabold bg-sky-100 text-sky-900 border border-sky-200 shadow-sm';
                }
                sevBadge.className = sevClass;
                sevBadge.textContent = sev;
                tdSeverity.appendChild(sevBadge);
                tr.appendChild(tdSeverity);

                // Recoverability
                const tdRecover = document.createElement('td');
                tdRecover.className = 'px-4 py-3 text-center';
                const recBadge = document.createElement('span');
                const ruleLower = issue.rule.toLowerCase();
                let isRecoverable = true;
                let recMethod = 'Auto-Clean';
                
                if (ruleLower.includes('country') || ruleLower.includes('payment')) {
                    isRecoverable = false;
                    recMethod = 'Manual Review';
                } else if (ruleLower.includes('missing')) {
                    recMethod = 'Imputation';
                } else if (ruleLower.includes('duplicate')) {
                    recMethod = 'Deduplicate';
                } else {
                    recMethod = 'Standardize';
                }
                
                if (isRecoverable) {
                    recBadge.className = 'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-extrabold bg-emerald-50 text-emerald-800 border border-emerald-200 shadow-sm';
                    recBadge.textContent = `RECOVERABLE (${recMethod.toUpperCase()})`;
                } else {
                    recBadge.className = 'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-extrabold bg-slate-100 text-slate-800 border border-slate-200 shadow-sm';
                    recBadge.textContent = recMethod.toUpperCase();
                }
                tdRecover.appendChild(recBadge);
                tr.appendChild(tdRecover);

                // Failed Rows
                const tdCount = document.createElement('td');
                tdCount.className = 'px-4 py-3 text-center text-slate-800 font-extrabold font-outfit';
                tdCount.textContent = issue.count.toLocaleString();
                tr.appendChild(tdCount);

                // Examples
                const tdExamples = document.createElement('td');
                tdExamples.className = 'px-4 py-3';
                const examplesContainer = document.createElement('div');
                examplesContainer.className = 'flex flex-wrap gap-1 max-w-xs';
                
                if (issue.examples && issue.examples.length > 0) {
                    issue.examples.forEach(ex => {
                        const span = document.createElement('span');
                        span.className = 'px-1.5 py-0.5 bg-slate-50 text-slate-600 rounded font-mono text-xs border border-slate-100';
                        span.textContent = ex || '(empty)';
                        examplesContainer.appendChild(span);
                    });
                } else {
                    const span = document.createElement('span');
                    span.className = 'text-slate-400 font-semibold italic text-xs';
                    span.textContent = 'None';
                    examplesContainer.appendChild(span);
                }
                tdExamples.appendChild(examplesContainer);
                tr.appendChild(tdExamples);

                issueLogsRows.appendChild(tr);
            });
            issueLogsSection.classList.remove('hidden');
            noIssuesAlert.classList.add('hidden');
        } else {
            issueLogsSection.classList.add('hidden');
            noIssuesAlert.classList.remove('hidden');
        }

        // --- 6. Render Radar Chart ---
        const radarCanvas = document.getElementById('radarChart');
        if (radarCanvas) {
            if (window.myRadarChart) {
                window.myRadarChart.destroy();
            }
            window.myRadarChart = new Chart(radarCanvas, {
                type: 'radar',
                data: {
                    labels: ['Completeness', 'Validity', 'Uniqueness'],
                    datasets: [{
                        label: 'Dataset Quality Dimensions',
                        data: [comp, val, uniq],
                        fill: true,
                        backgroundColor: 'rgba(16, 185, 129, 0.2)',
                        borderColor: 'rgb(16, 185, 129)',
                        pointBackgroundColor: 'rgb(16, 185, 129)',
                        pointBorderColor: '#fff',
                        pointHoverBackgroundColor: '#fff',
                        pointHoverBorderColor: 'rgb(16, 185, 129)'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    layout: {
                        padding: 0
                    },
                    elements: {
                        point: {
                            radius: 2,
                            hoverRadius: 3
                        },
                        line: {
                            borderWidth: 2
                        }
                    },
                    scales: {
                        r: {
                            angleLines: {
                                display: true,
                                color: 'rgba(148, 163, 184, 0.2)'
                             },
                             grid: {
                                 color: 'rgba(148, 163, 184, 0.15)'
                             },
                             pointLabels: {
                                 font: {
                                     size: 9,
                                     weight: 'bold',
                                     family: 'sans-serif'
                                 },
                                 color: '#1e293b'
                             },
                             suggestedMin: 0,
                             suggestedMax: 100,
                             ticks: {
                                 display: false
                             }
                         }
                     },
                     plugins: {
                         legend: {
                             display: false
                         }
                     }
                 }
             });
         }

        // Calculate expectations evaluated
        let expectationsCount = 2; // Completeness and Uniqueness are always evaluated
        if (data.column_mapping && data.column_mapping['email']) expectationsCount++;
        if (data.column_mapping && data.column_mapping['phone_number']) expectationsCount++;
        if (data.column_mapping && data.column_mapping['transaction_date']) expectationsCount++;
        if (data.dataset_type !== "Customer Dataset") expectationsCount++;

        const footerExpectationsCount = document.getElementById('footerExpectationsCount');
        if (footerExpectationsCount) {
            footerExpectationsCount.textContent = `${expectationsCount} expectations evaluated`;
        }
        const footerLastAnalysis = document.getElementById('footerLastAnalysis');
        if (footerLastAnalysis) {
            footerLastAnalysis.textContent = `Last analysis: ${new Date().toLocaleTimeString()}`;
        }

        // Display dashboard
        loader.classList.add('hidden');
        dashboard.classList.remove('hidden');
    }
});
