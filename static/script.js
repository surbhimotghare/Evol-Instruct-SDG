// Global variables
let currentResults = null;
let currentTab = 'simple';
let uploadedDocs = [];
let progressEventSource = null;

// DOM elements
const fileInput = document.getElementById('fileInput');
const filePreview = document.getElementById('filePreview');
const targetQuestions = document.getElementById('targetQuestions');
const generateBtn = document.getElementById('generateBtn');
const demoBtn = document.getElementById('demoBtn');
const loadingSection = document.getElementById('loadingSection');
const resultsSection = document.getElementById('resultsSection');
const errorSection = document.getElementById('errorSection');
const questionsContainer = document.getElementById('questionsContainer');
const questionCount = document.getElementById('questionCount');
const processingTime = document.getElementById('processingTime');

// --- OpenAI API Key Logic ---
const apiKeyInput = document.getElementById('openaiApiKey');
const apiKeyForm = document.getElementById('apiKeyForm');
const toggleApiKeyBtn = document.getElementById('toggleApiKey');
const saveApiKeyBtn = document.getElementById('saveApiKeyBtn');
const clearApiKeyBtn = document.getElementById('clearApiKeyBtn');
const apiKeyStatus = document.getElementById('apiKeyStatus');

// API configuration
const API_BASE_URL = window.location.origin; // Will work for both local and deployed

// Load external libraries for file parsing
function loadExternalLibraries() {
    // Load PDF.js for PDF parsing
    const pdfScript = document.createElement('script');
    pdfScript.src = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js';
    pdfScript.onload = () => {
        // Configure PDF.js worker
        if (typeof pdfjsLib !== 'undefined') {
            pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
        }
    };
    document.head.appendChild(pdfScript);

    // Load Papa Parse for CSV parsing
    const papaScript = document.createElement('script');
    papaScript.src = 'https://cdnjs.cloudflare.com/ajax/libs/PapaParse/5.4.1/papaparse.min.js';
    document.head.appendChild(papaScript);
}

// Load libraries when page loads
document.addEventListener('DOMContentLoaded', loadExternalLibraries);

const MAX_FILES = 10;

fileInput.addEventListener('change', handleFileSelect);

function handleFileSelect(e) {
    const files = Array.from(e.target.files);
    if (files.length > MAX_FILES) {
        showFileLimitWarning();
        fileInput.value = '';
        return;
    }
    uploadedDocs = [];
    filePreview.innerHTML = '';

    if (files.length === 0) {
        filePreview.innerHTML = '<span style="color:#718096;">No files selected.</span>';
        return;
    }

    // Show processing message
    filePreview.innerHTML = '<div style="text-align: center; color: #0077b5; padding: 2rem;"><i class="fas fa-spinner fa-spin"></i> Processing files...</div>';

    Promise.all(files.map((file, idx) => processFile(file, idx)))
        .then(() => {
            renderFileList();
            if (uploadedDocs.filter(Boolean).length === 0) {
                filePreview.innerHTML = '<div style="color:#e53e3e; text-align: center;">No supported files could be processed. Please upload .txt, .pdf, or .csv files.</div>';
            }
        });
}

function showFileLimitWarning() {
    filePreview.innerHTML = `<div style="color:#e53e3e; text-align:center; padding:1.5rem; font-weight:600;">You can upload a maximum of ${MAX_FILES} files at a time.</div>`;
}

async function processFile(file, idx) {
    const ext = file.name.split('.').pop().toLowerCase();
    // Only process metadata, not content
    let extractedText = '';
    try {
        if (ext === 'txt') {
            extractedText = await readTextFile(file);
        } else if (ext === 'pdf') {
            extractedText = await readPdfFile(file);
        } else if (ext === 'csv') {
            extractedText = await readCsvFile(file);
        } else {
            throw new Error(`Unsupported file type: .${ext}`);
        }
        if (extractedText && extractedText.trim()) {
            uploadedDocs[idx] = {
                page_content: extractedText.slice(0, 4000),
                metadata: {
                    source: file.name,
                    size: file.size,
                    type: file.type,
                    extension: ext
                }
            };
        } else {
            throw new Error('No text content found in file');
        }
    } catch (error) {
        console.error(`Error processing ${file.name}:`, error);
        uploadedDocs[idx] = null;
    }
}

function renderFileList() {
    filePreview.innerHTML = '';
    const validDocs = uploadedDocs.filter(Boolean);
    if (validDocs.length === 0) {
        filePreview.innerHTML = '<span style="color:#718096;">No files selected.</span>';
        return;
    }
    const list = document.createElement('ul');
    list.className = 'uploaded-doc-list';
    validDocs.forEach((doc, idx) => {
        const li = document.createElement('li');
        li.className = 'uploaded-doc-item';
        const icon = getFileIcon(doc.metadata.extension);
        li.innerHTML = `
            <span class="uploaded-doc-icon">${icon}</span>
            <span class="uploaded-doc-name">${doc.metadata.source}</span>
            <span class="uploaded-doc-size">(${(doc.metadata.size/1024).toFixed(1)} KB)</span>
            <button class="remove-doc-btn" title="Remove" data-idx="${idx}"><i class="fas fa-times"></i></button>
        `;
        list.appendChild(li);
    });
    filePreview.appendChild(list);
    // Add event listeners for remove buttons
    filePreview.querySelectorAll('.remove-doc-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            const idx = parseInt(e.currentTarget.getAttribute('data-idx'));
            removeDoc(idx);
        });
    });
}

function getFileIcon(ext) {
    if (ext === 'pdf') return '<i class="fas fa-file-pdf" style="color:#e53e3e;"></i>';
    if (ext === 'csv') return '<i class="fas fa-file-csv" style="color:#22c55e;"></i>';
    return '<i class="fas fa-file-alt" style="color:#0077b5;"></i>';
}

function removeDoc(idx) {
    uploadedDocs.splice(idx, 1);
    renderFileList();
    // Also clear the file input if no docs left
    if (uploadedDocs.filter(Boolean).length === 0) {
        fileInput.value = '';
    }
}

// Read text file
function readTextFile(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => resolve(e.target.result);
        reader.onerror = () => reject(new Error('Failed to read text file'));
        reader.readAsText(file);
    });
}

// Read PDF file using PDF.js
function readPdfFile(file) {
    return new Promise((resolve, reject) => {
        if (typeof pdfjsLib === 'undefined') {
            reject(new Error('PDF.js library not loaded yet. Please try again in a moment.'));
            return;
        }

        const reader = new FileReader();
        reader.onload = async function(e) {
            try {
                const typedArray = new Uint8Array(e.target.result);
                const pdf = await pdfjsLib.getDocument(typedArray).promise;
                let fullText = '';
                
                // Extract text from each page
                for (let i = 1; i <= Math.min(pdf.numPages, 10); i++) { // Limit to first 10 pages
                    const page = await pdf.getPage(i);
                    const textContent = await page.getTextContent();
                    const pageText = textContent.items.map(item => item.str).join(' ');
                    fullText += `Page ${i}:\n${pageText}\n\n`;
                }
                
                if (fullText.trim()) {
                    resolve(fullText.trim());
                } else {
                    reject(new Error('No text content found in PDF'));
                }
            } catch (error) {
                reject(new Error(`PDF parsing failed: ${error.message}`));
            }
        };
        reader.onerror = () => reject(new Error('Failed to read PDF file'));
        reader.readAsArrayBuffer(file);
    });
}

// Read CSV file using Papa Parse
function readCsvFile(file) {
    return new Promise((resolve, reject) => {
        if (typeof Papa === 'undefined') {
            reject(new Error('Papa Parse library not loaded yet. Please try again in a moment.'));
            return;
        }

        Papa.parse(file, {
            header: true,
            skipEmptyLines: true,
            complete: function(results) {
                try {
                    if (results.errors && results.errors.length > 0) {
                        console.warn('CSV parsing warnings:', results.errors);
                    }

                    if (!results.data || results.data.length === 0) {
                        reject(new Error('No data found in CSV file'));
                        return;
                    }

                    // Convert CSV data to readable text format
                    let textContent = `CSV Data from ${file.name}:\n\n`;
                    
                    // Add headers
                    const headers = Object.keys(results.data[0]);
                    textContent += `Columns: ${headers.join(', ')}\n\n`;
                    
                    // Add sample of data (first 50 rows)
                    const sampleData = results.data.slice(0, 50);
                    sampleData.forEach((row, index) => {
                        textContent += `Row ${index + 1}:\n`;
                        headers.forEach(header => {
                            if (row[header]) {
                                textContent += `${header}: ${row[header]}\n`;
                            }
                        });
                        textContent += '\n';
                    });

                    // Add summary info
                    textContent += `\nSummary: ${results.data.length} total rows, ${headers.length} columns`;
                    
                    if (results.data.length > 50) {
                        textContent += `\n(Showing first 50 rows for processing)`;
                    }

                    resolve(textContent);
                } catch (error) {
                    reject(new Error(`CSV processing failed: ${error.message}`));
                }
            },
            error: function(error) {
                reject(new Error(`CSV parsing failed: ${error.message}`));
            }
        });
    });
}

// Event listeners
document.addEventListener('DOMContentLoaded', function() {
    generateBtn.addEventListener('click', handleGenerate);
    demoBtn.addEventListener('click', handleDemo);
    // Tab switching
    const tabButtons = document.querySelectorAll('.tab-btn');
    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => switchTab(btn.dataset.tab));
    });
});

// --- OpenAI API Key Logic ---
function getStoredApiKey() {
    return localStorage.getItem('openai_api_key') || '';
}
function setStoredApiKey(key) {
    if (key) {
        localStorage.setItem('openai_api_key', key);
    } else {
        localStorage.removeItem('openai_api_key');
    }
}
function updateApiKeyStatus(msg, isError = false) {
    apiKeyStatus.textContent = msg;
    apiKeyStatus.className = 'api-key-status' + (isError ? ' error' : '');
}
function updateApiKeyInputState() {
    const key = getStoredApiKey();
    if (key) {
        apiKeyInput.value = key;
        apiKeyInput.type = 'password';
        updateApiKeyStatus('Key saved locally ✓');
        saveApiKeyBtn.textContent = 'Update';
        clearApiKeyBtn.style.display = '';
    } else {
        apiKeyInput.value = '';
        updateApiKeyStatus('No key saved', true);
        saveApiKeyBtn.textContent = 'Save';
        clearApiKeyBtn.style.display = 'none';
    }
}
// Show/hide key
let apiKeyVisible = false;
toggleApiKeyBtn.addEventListener('click', function() {
    apiKeyVisible = !apiKeyVisible;
    apiKeyInput.type = apiKeyVisible ? 'text' : 'password';
    toggleApiKeyBtn.innerHTML = apiKeyVisible ? '<i class="fas fa-eye-slash"></i>' : '<i class="fas fa-eye"></i>';
});
// Save key
apiKeyForm.addEventListener('submit', function(e) {
    e.preventDefault();
    const key = apiKeyInput.value.trim();
    if (!key.startsWith('sk-')) {
        updateApiKeyStatus('Invalid key format', true);
        return;
    }
    setStoredApiKey(key);
    updateApiKeyStatus('Key saved locally ✓');
    updateApiKeyInputState();
});
// Clear key
clearApiKeyBtn.addEventListener('click', function() {
    setStoredApiKey('');
    updateApiKeyInputState();
});
// On load
updateApiKeyInputState();

// Handle generate button click
async function handleGenerate() {
    // Use all successfully processed files
    const docs = uploadedDocs.filter(Boolean);
    if (docs.length === 0) {
        showError('Please upload at least one supported file (.txt, .pdf, .csv). Make sure the files contain readable text content.');
        return;
    }
    const targetCount = parseInt(targetQuestions.value);
    if (targetCount < 3 || targetCount > 15) {
        showError('Target questions must be between 3 and 15.');
        return;
    }
    const requestData = {
        documents: docs,
        target_questions: targetCount
    };
    await callAPIWithProgress('/generate', requestData);
}

// Handle demo button click
async function handleDemo() {
    await callAPIWithProgress('/generate-demo', null);
}

// Make API call with real-time progress updates
async function callAPIWithProgress(endpoint, requestData) {
    try {
        showLoadingWithProgress();
        
        // Start progress stream first
        startProgressStream();
        
        const url = `${API_BASE_URL}${endpoint}`;
        const options = {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        };
        // Add OpenAI key header if present
        const userKey = getStoredApiKey();
        if (userKey) {
            options.headers['x-openai-api-key'] = userKey;
        }
        if (requestData) {
            options.body = JSON.stringify(requestData);
        }
        
        const response = await fetch(url, options);
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
        }
        const data = await response.json();
        
        // Stop progress stream
        stopProgressStream();
        
        showResults(data);
    } catch (error) {
        console.error('API Error:', error);
        stopProgressStream();
        showError(`Failed to generate questions: ${error.message}`);
    }
}

// Start Server-Sent Events for progress updates
function startProgressStream() {
    if (progressEventSource) {
        stopProgressStream();
    }
    
    progressEventSource = new EventSource(`${API_BASE_URL}/progress-stream`);
    
    progressEventSource.onmessage = function(event) {
        try {
            const progressData = JSON.parse(event.data);
            updateProgressDisplay(progressData);
        } catch (error) {
            console.error('Error parsing progress data:', error);
        }
    };
    
    progressEventSource.onerror = function(event) {
        console.error('Progress stream error:', event);
        // Don't close automatically, let it try to reconnect
    };
}

// Stop progress stream
function stopProgressStream() {
    if (progressEventSource) {
        progressEventSource.close();
        progressEventSource = null;
    }
}

// Update progress display with real-time data
function updateProgressDisplay(progressData) {
    const progressContainer = document.querySelector('.loading-content');
    if (!progressContainer) return;
    
    const { type, phase, message, details = {} } = progressData;
    
    // Update main progress message
    const mainMessage = progressContainer.querySelector('h3');
    const subMessage = progressContainer.querySelector('p');
    
    if (mainMessage && message) {
        mainMessage.innerHTML = message;
    }
    
    // Create or update progress steps
    let stepsContainer = progressContainer.querySelector('.progress-steps');
    if (!stepsContainer) {
        stepsContainer = document.createElement('div');
        stepsContainer.className = 'progress-steps';
        stepsContainer.style.cssText = `
            margin-top: 2rem;
            text-align: left;
            max-height: 300px;
            overflow-y: auto;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            padding: 1rem;
        `;
        progressContainer.appendChild(stepsContainer);
    }
    
    // Add step to container
    if (type === 'phase_start' || type === 'step' || type === 'success' || type === 'error' || type === 'warning') {
        const stepElement = document.createElement('div');
        stepElement.className = `progress-step ${type}`;
        stepElement.style.cssText = `
            display: flex;
            align-items: center;
            margin: 0.5rem 0;
            padding: 0.5rem;
            border-radius: 5px;
            font-size: 0.9rem;
            animation: slideInLeft 0.3s ease-out;
            background: ${getStepColor(type)};
        `;
        
        stepElement.innerHTML = `
            <span style="margin-right: 0.5rem; font-weight: bold;">${getStepIcon(type)}</span>
            <span>${message}</span>
            ${details.question_preview ? `<small style="margin-left: 1rem; opacity: 0.8;">${details.question_preview}</small>` : ''}
        `;
        
        stepsContainer.appendChild(stepElement);
        
        // Auto-scroll to bottom
        stepsContainer.scrollTop = stepsContainer.scrollHeight;
        
        // Limit number of visible steps (keep last 20)
        const steps = stepsContainer.querySelectorAll('.progress-step');
        if (steps.length > 20) {
            steps[0].remove();
        }
    }
    
    // Update sub-message with details
    if (subMessage && details) {
        let detailText = '';
        if (details.total_documents) {
            detailText += `Processing ${details.total_documents} documents`;
        }
        if (details.target_questions) {
            detailText += detailText ? ` • Target: ${details.target_questions} questions` : `Target: ${details.target_questions} questions`;
        }
        if (details.total_questions) {
            detailText += detailText ? ` • Generated: ${details.total_questions}` : `Generated: ${details.total_questions}`;
        }
        
        if (detailText) {
            subMessage.innerHTML = detailText;
        }
    }
    
    // Handle completion
    if (type === 'complete') {
        setTimeout(() => {
            stopProgressStream();
        }, 1000);
    }
    
    // Handle error
    if (type === 'error') {
        setTimeout(() => {
            stopProgressStream();
            showError(message.replace('❌ ', ''));
        }, 1000);
    }
}

// Get step color based on type
function getStepColor(type) {
    const colors = {
        'phase_start': 'rgba(0, 119, 181, 0.2)',
        'step': 'rgba(100, 116, 139, 0.1)',
        'success': 'rgba(34, 197, 94, 0.2)',
        'error': 'rgba(239, 68, 68, 0.2)',
        'warning': 'rgba(245, 158, 11, 0.2)',
        'phase_complete': 'rgba(139, 69, 255, 0.2)'
    };
    return colors[type] || 'rgba(100, 116, 139, 0.1)';
}

// Get step icon based on type
function getStepIcon(type) {
    const icons = {
        'phase_start': '🚀',
        'step': '⚙️',
        'success': '✅',
        'error': '❌',
        'warning': '⚠️',
        'phase_complete': '🎯'
    };
    return icons[type] || '•';
}

// Show loading state with progress capability
function showLoadingWithProgress() {
    hideAllSections();
    loadingSection.classList.remove('hidden');
    generateBtn.disabled = true;
    demoBtn.disabled = true;
    
    // Reset loading content to initial state
    const loadingContent = loadingSection.querySelector('.loading-content');
    const stepsContainer = loadingContent.querySelector('.progress-steps');
    if (stepsContainer) {
        stepsContainer.remove();
    }
    
    // Reset main messages
    const mainMessage = loadingContent.querySelector('h3');
    const subMessage = loadingContent.querySelector('p');
    if (mainMessage) mainMessage.innerHTML = 'Initializing Evol-Instruct Pipeline...';
    if (subMessage) subMessage.innerHTML = 'Preparing to analyze your documents and generate sophisticated questions';
}

// Original loading function for fallback
function showLoading() {
    showLoadingWithProgress();
}

// Show results
function showResults(data) {
    hideAllSections();
    resultsSection.classList.remove('hidden');
    currentResults = data;
    questionCount.textContent = data.total_questions;
    processingTime.textContent = data.processing_time.toFixed(1);
    displayQuestions(currentTab);
    generateBtn.disabled = false;
    demoBtn.disabled = false;
}

// Show error
function showError(message) {
    hideAllSections();
    errorSection.classList.remove('hidden');
    document.getElementById('errorMessage').textContent = message;
    generateBtn.disabled = false;
    demoBtn.disabled = false;
    stopProgressStream(); // Make sure to stop progress stream on error
}

// Hide error
function hideError() {
    errorSection.classList.add('hidden');
}

// Hide all sections
function hideAllSections() {
    loadingSection.classList.add('hidden');
    resultsSection.classList.add('hidden');
    errorSection.classList.add('hidden');
}

// Switch tabs
function switchTab(tabName) {
    currentTab = tabName;
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
    if (currentResults) {
        displayQuestions(tabName);
    }
}

// Display questions for a specific tab
function displayQuestions(tabName) {
    if (!currentResults) return;
    const questions = currentResults.evolved_questions.filter(q => q.evolution_type === tabName);
    const answers = currentResults.question_answers;
    const contexts = currentResults.question_contexts;
    questionsContainer.innerHTML = '';
    if (questions.length === 0) {
        questionsContainer.innerHTML = `
            <div class="question-card">
                <p style="text-align: center; color: #718096; font-style: italic;">
                    No ${tabName.replace('_', ' ')} questions generated yet.
                </p>
            </div>
        `;
        return;
    }
    questions.forEach(question => {
        const answer = answers.find(a => a.question_id === question.id);
        const context = contexts.find(c => c.question_id === question.id);
        const questionCard = createQuestionCard(question, answer, context);
        questionsContainer.appendChild(questionCard);
    });
}

// Replace createQuestionCard with a dropdown/collapsible version
function createQuestionCard(question, answer, context) {
    const card = document.createElement('div');
    card.className = 'question-card dropdown-card';
    const evolutionTypeClass = question.evolution_type.replace('_', '-');
    const evolutionTypeText = question.evolution_type.replace('_', ' ');

    card.innerHTML = `
        <div class="dropdown-header">
            <span class="question-id">${question.id}</span>
            <span class="evolution-type ${evolutionTypeClass}">${evolutionTypeText}</span>
            <span class="dropdown-arrow"><i class="fas fa-chevron-down"></i></span>
        </div>
        <div class="question-full-text">${escapeHtml(question.question)}</div>
        <div class="dropdown-details" style="display:none;">
            <div class="detail-section">
                <h4>Generated Answer</h4>
                <p>${answer ? escapeHtml(answer.answer) : 'No answer available.'}</p>
            </div>
            <div class="detail-section">
                <h4>Relevant Contexts</h4>
                ${context && context.contexts.length > 0 ? `
                    <ul class="context-list">
                        ${context.contexts.map(ctx => `<li>${escapeHtml(ctx)}</li>`).join('')}
                    </ul>
                ` : '<p>No contexts available.</p>'}
            </div>
        </div>
    `;

    // Toggle dropdown on click
    card.querySelector('.dropdown-header').addEventListener('click', () => {
        const details = card.querySelector('.dropdown-details');
        const arrow = card.querySelector('.dropdown-arrow i');
        if (details.style.display === 'none') {
            details.style.display = 'block';
            arrow.classList.remove('fa-chevron-down');
            arrow.classList.add('fa-chevron-up');
        } else {
            details.style.display = 'none';
            arrow.classList.remove('fa-chevron-up');
            arrow.classList.add('fa-chevron-down');
        }
    });
    return card;
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Add copy functionality for questions
document.addEventListener('DOMContentLoaded', function() {
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('copy-btn')) {
            const textToCopy = e.target.dataset.text;
            navigator.clipboard.writeText(textToCopy).then(() => {
                const originalText = e.target.innerHTML;
                e.target.innerHTML = '<i class="fas fa-check"></i> Copied!';
                e.target.style.background = '#48bb78';
                setTimeout(() => {
                    e.target.innerHTML = originalText;
                    e.target.style.background = '';
                }, 2000);
            });
        }
    });
}); 