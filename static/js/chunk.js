document.addEventListener('DOMContentLoaded', () => {
    const radioButtons = document.getElementsByName('chunk_preset');
    const customRadio = document.getElementById('customRadio');
    const customSizeInput = document.getElementById('customSizeInput');
    const generateBtn = document.getElementById('generateBtn');
    
    const placeholder = document.getElementById('chunksPlaceholder');
    const loader = document.getElementById('chunksLoader');
    const resultsCard = document.getElementById('chunksResults');
    
    const chunkCountText = document.getElementById('chunkCountText');
    const chunksList = document.getElementById('chunksList');

    // Toggle custom size input based on selection
    radioButtons.forEach(radio => {
        radio.addEventListener('change', () => {
            if (customRadio.checked) {
                customSizeInput.removeAttribute('disabled');
                customSizeInput.focus();
            } else {
                customSizeInput.setAttribute('disabled', 'true');
                customSizeInput.value = '';
            }
        });
    });

    generateBtn.addEventListener('click', () => {
        let chunkSize = null;
        
        if (customRadio.checked) {
            const val = customSizeInput.value.strip ? customSizeInput.value.strip() : customSizeInput.value;
            if (!val || isNaN(val) || parseInt(val) <= 0) {
                alert('Please enter a valid positive integer for custom chunk size.');
                customSizeInput.focus();
                return;
            }
            chunkSize = parseInt(val);
        } else {
            // Find checked radio
            const checkedRadio = Array.from(radioButtons).find(r => r.checked);
            chunkSize = parseInt(checkedRadio.value);
        }

        // Show loading, hide others
        placeholder.classList.add('hidden');
        resultsCard.classList.add('hidden');
        loader.classList.remove('hidden');

        fetch('/chunk/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ chunk_size: chunkSize })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            populateResults(data);
        })
        .catch(err => {
            console.error('Chunking Error:', err);
            alert('Failed to split dataset. Ensure you have completed the cleaning step first.');
            loader.classList.add('hidden');
            placeholder.classList.remove('hidden');
        });
    });

    function populateResults(data) {
        // Set count
        chunkCountText.textContent = data.chunk_count.toLocaleString();
        
        // Clear list and add sequential items
        chunksList.innerHTML = '';
        
        data.chunk_files.forEach((file, idx) => {
            const li = document.createElement('li');
            li.className = 'px-4 py-3 flex items-center justify-between hover:bg-slate-50/50';
            
            const fileInfo = document.createElement('div');
            fileInfo.className = 'flex items-center space-x-3';
            
            // CSV Icon
            const iconSpan = document.createElement('div');
            iconSpan.className = 'w-6 h-6 rounded bg-slate-50 flex items-center justify-center text-slate-400';
            iconSpan.innerHTML = `
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                </svg>
            `;
            fileInfo.appendChild(iconSpan);
            
            const nameSpan = document.createElement('span');
            nameSpan.className = 'font-mono text-slate-600';
            nameSpan.textContent = file;
            fileInfo.appendChild(nameSpan);
            
            li.appendChild(fileInfo);
            
            const badgeSpan = document.createElement('span');
            badgeSpan.className = 'text-xs bg-slate-100 text-slate-400 px-1.5 py-0.5 rounded uppercase font-bold';
            badgeSpan.textContent = `Part ${idx + 1}`;
            li.appendChild(badgeSpan);
            
            chunksList.appendChild(li);
        });

        // Hide loader, show results
        loader.classList.add('hidden');
        resultsCard.classList.remove('hidden');
    }
});
