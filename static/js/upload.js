document.addEventListener('DOMContentLoaded', () => {
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('fileInput');
    
    const progressContainer = document.getElementById('uploadProgressContainer');
    const progressBar = document.getElementById('uploadProgressBar');
    const progressPercent = document.getElementById('uploadPercent');
    const statusText = document.getElementById('uploadStatusText');
    
    const fileDetailsCard = document.getElementById('fileDetailsCard');
    const detailFilename = document.getElementById('detailFilename');
    const detailRows = document.getElementById('detailRows');
    const detailCols = document.getElementById('detailCols');
    const detailSize = document.getElementById('detailSize');
    const detailTime = document.getElementById('detailTime');
    
    const previewContainer = document.getElementById('previewContainer');
    const previewStats = document.getElementById('previewStats');
    const previewHeaders = document.getElementById('previewHeaders');
    const previewRows = document.getElementById('previewRows');
    const infoFooter = document.getElementById('uploadInfoFooter');

    // Trigger click on file input
    dropzone.addEventListener('click', () => fileInput.click());

    // Drag-and-drop styling events
    ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropzone.classList.add('dragover');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropzone.classList.remove('dragover');
        }, false);
    });

    // Handle dropped file
    dropzone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length) {
            handleFileUpload(files[0]);
        }
    });

    // Handle selected file
    fileInput.addEventListener('change', () => {
        if (fileInput.files.length) {
            handleFileUpload(fileInput.files[0]);
        }
    });

    function handleFileUpload(file) {
        if (!file.name.endsWith('.csv')) {
            alert('Only CSV files are supported!');
            return;
        }

        // Setup Form Data
        const formData = new FormData();
        formData.append('file', file);

        // Show Progress Bar
        progressContainer.classList.remove('hidden');
        dropzone.classList.add('hidden');
        infoFooter.classList.add('hidden');
        
        fileDetailsCard.classList.add('hidden');
        previewContainer.classList.add('hidden');

        // XML HTTP Request for tracking upload percentage
        const xhr = new XMLHttpRequest();
        xhr.open('POST', '/upload', true);

        xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable) {
                const percent = Math.round((e.loaded / e.total) * 100);
                progressBar.style.width = percent + '%';
                progressPercent.textContent = percent + '%';
                if (percent === 100) {
                    statusText.textContent = "Processing CSV data on server...";
                }
            }
        });

        xhr.onreadystatechange = () => {
            if (xhr.readyState === XMLHttpRequest.DONE) {
                if (xhr.status === 200) {
                    const response = JSON.parse(xhr.responseText);
                    renderPreview(response);
                } else {
                    let errMsg = "Upload failed. Please try again.";
                    try {
                        const errRes = JSON.parse(xhr.responseText);
                        errMsg = errRes.error || errMsg;
                    } catch (e) {}
                    
                    alert(errMsg);
                    progressBar.style.width = '0%';
                    progressPercent.textContent = '0%';
                    progressContainer.classList.add('hidden');
                    dropzone.classList.remove('hidden');
                    infoFooter.classList.remove('hidden');
                }
            }
        };

        xhr.send(formData);
    }

    function renderPreview(data) {
        // Hide progress
        progressContainer.classList.add('hidden');
        
        // Show file details
        detailFilename.textContent = data.filename;
        detailRows.textContent = `${data.rows.toLocaleString()} rows`;
        detailCols.textContent = `${data.columns} columns`;
        detailSize.textContent = `${data.filesize_kb} KB`;
        detailTime.textContent = 'Uploaded just now';
        fileDetailsCard.classList.remove('hidden');
        
        // Show preview section
        previewStats.textContent = `Showing 10 of ${data.rows.toLocaleString()} rows`;
        
        // Clear old previews
        previewHeaders.innerHTML = '';
        previewRows.innerHTML = '';

        // Add header '#', then columns
        const hashTh = document.createElement('th');
        hashTh.className = 'px-4 py-3.5';
        hashTh.textContent = '#';
        previewHeaders.appendChild(hashTh);

        data.preview.headers.forEach(header => {
            const th = document.createElement('th');
            th.className = 'px-4 py-3.5';
            th.textContent = header;
            previewHeaders.appendChild(th);
        });

        // Add first 10 rows
        data.preview.rows.forEach((row, idx) => {
            const tr = document.createElement('tr');
            tr.className = idx % 2 === 0 ? 'bg-white hover:bg-slate-50/50' : 'bg-slate-50/30 hover:bg-slate-50/50';
            
            const indexTd = document.createElement('td');
            indexTd.className = 'px-4 py-3 font-semibold text-slate-400 border-r border-slate-50/50';
            indexTd.textContent = idx + 1;
            tr.appendChild(indexTd);
            
            row.forEach(cell => {
                const td = document.createElement('td');
                td.className = 'px-4 py-3 whitespace-nowrap truncate max-w-xs';
                td.textContent = cell;
                tr.appendChild(td);
            });
            
            previewRows.appendChild(tr);
        });

        previewContainer.classList.remove('hidden');
    }
});
