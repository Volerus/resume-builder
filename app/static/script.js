// Character counter
const jobDescription = document.getElementById('jobDescription');
const charCount = document.getElementById('charCount');

jobDescription.addEventListener('input', () => {
    charCount.textContent = jobDescription.value.length;
});

const prePromptInput = document.getElementById('prePrompt');
const postPromptInput = document.getElementById('postPrompt');
const additionalContextInput = document.getElementById('additionalContext');

// Default Prompts
const DEFAULT_PRE_PROMPT = "Act as a JSON Data Processor and ATS Optimization Specialist\nI am going to provide you with a **Resume in JSON format** and a **Target Job Description**.\nYour task is to update the values inside the `work`, `professional_summary`, and `skills` arrays within the JSON to better match the Job Description.";

const DEFAULT_POST_PROMPT = "**Strict Technical Constraints:**\n1.  **Output Format:** You must return **ONLY** valid, raw JSON. Do not include markdown formatting (like ```json), conversational filler, or explanations. Just the JSON object.\n2.  **Structure Integrity:** Do not change keys, variable names, or the overall structure of the JSON object.\n3.  **Minimal Edits:** You are allowed to change or insert a maximum of **3-4 specific keywords** to match the Job Description if necessary.\n4.  **Preserve Context:** Do not rewrite the sentences. Keep the original sentence structure and meaning, only swapping in technical terms or hard skills where they fit naturally.\n5. **Pick and Choose:** Based on the Job Description, pick and choose the most relevant 5 `highlights`  per `company`. When possible combine multiple highlights into just 5 highlights concising";

// Populate defaults
prePromptInput.value = DEFAULT_PRE_PROMPT;
postPromptInput.value = DEFAULT_POST_PROMPT;

// Load saved prompts
async function loadPrompts() {
    try {
        const response = await fetch('/get-prompts');
        if (response.ok) {
            const data = await response.json();
            if (data.pre_prompt) prePromptInput.value = data.pre_prompt;
            if (data.post_prompt) postPromptInput.value = data.post_prompt;
        }
    } catch (error) {
        console.error('Error loading prompts:', error);
    }
}
loadPrompts();

// Save defaults
document.getElementById('saveDefaultsBtn').addEventListener('click', async () => {
    const btn = document.getElementById('saveDefaultsBtn');
    const originalText = btn.textContent;

    try {
        btn.textContent = 'Saving...';
        btn.disabled = true;

        const response = await fetch('/save-prompts', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                pre_prompt: prePromptInput.value,
                post_prompt: postPromptInput.value
            })
        });

        if (response.ok) {
            btn.textContent = 'Saved!';
            setTimeout(() => {
                btn.textContent = originalText;
                btn.disabled = false;
            }, 2000);
        } else {
            throw new Error('Failed to save');
        }
    } catch (error) {
        console.error('Error saving prompts:', error);
        btn.textContent = 'Error';
        setTimeout(() => {
            btn.textContent = originalText;
            btn.disabled = false;
        }, 2000);
    }
});

// Form submission
const form = document.getElementById('resumeForm');
const submitBtn = document.getElementById('submitBtn');
const resultContainer = document.getElementById('result');
const errorContainer = document.getElementById('error');
const errorMessage = document.getElementById('errorMessage');
const downloadBtn = document.getElementById('downloadBtn');
const diffEditor = document.getElementById('diffEditor');
const generatePdfBtn = document.getElementById('generatePdfBtn');
const historyList = document.getElementById('historyList');
const refreshHistoryBtn = document.getElementById('refreshHistoryBtn');
const pdfModal = document.getElementById('pdfModal');
const pdfViewer = document.getElementById('pdfViewer');

// Store data for PDF generation
let currentCompanyName = '';
let originalResumeData = null;
let improvedResumeData = null;

// Step 1: Improve resume and show diff editor
form.addEventListener('submit', async (e) => {
    e.preventDefault();

    // Reset states
    diffEditor.classList.add('hidden');
    resultContainer.classList.add('hidden');
    errorContainer.classList.add('hidden');
    submitBtn.classList.add('loading');
    submitBtn.disabled = true;

    const description = jobDescription.value.trim();
    const prePrompt = prePromptInput.value.trim();
    const postPrompt = postPromptInput.value.trim();
    const additionalContext = additionalContextInput.value.trim();

    if (!description) {
        showError('Please enter a job description');
        return;
    }

    try {
        const response = await fetch('/improve-resume', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                description,
                pre_prompt: prePrompt,
                post_prompt: postPrompt,
                additional_context: additionalContext
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `Server error: ${response.status}`);
        }

        const data = await response.json();

        // Store data for later use
        currentCompanyName = data.company_name;
        originalResumeData = data.original;
        improvedResumeData = data.improved;

        // Populate work experience and skills sections
        populateProfessionalSummary(data.original.professional_summary, data.improved.professional_summary);
        populateWorkExperience(data.original.work, data.improved.work);
        populateSkills(data.original.skills, data.improved.skills);

        // Show diff editor
        submitBtn.classList.remove('loading');
        submitBtn.disabled = false;
        diffEditor.classList.remove('hidden');

        // Scroll to diff editor
        diffEditor.scrollIntoView({ behavior: 'smooth', block: 'start' });

    } catch (error) {
        console.error('Error:', error);
        showError(error.message || 'Failed to generate improved resume. Please try again.');
    }
});

// Functions to populate resume sections
// Diff Helper
let dmp;

function createDiffHtml(text1, text2, side) {
    if (!dmp) {
        dmp = new diff_match_patch();
    }
    const diffs = dmp.diff_main(text1 || '', text2 || '');
    dmp.diff_cleanupSemantic(diffs);

    let html = '';
    diffs.forEach(diff => {
        const [op, text] = diff;
        // op: -1 (delete), 0 (equal), 1 (insert)

        if (side === 'original') {
            if (op === 0) {
                html += `<span>${text}</span>`;
            } else if (op === -1) {
                html += `<del>${text}</del>`;
            }
        } else { // improved
            if (op === 0) {
                html += `<span>${text}</span>`;
            } else if (op === 1) {
                html += `<ins>${text}</ins>`;
            }
        }
    });
    return html;
}
function populateProfessionalSummary(originalSummary, improvedSummary) {
    const container = document.getElementById('professionalSummary');
    container.innerHTML = '';

    originalSummary = originalSummary || '';
    improvedSummary = improvedSummary || '';

    const row = document.createElement('div');
    row.className = 'diff-row';

    // Original Column
    const originalCol = document.createElement('div');
    originalCol.className = 'diff-column original';
    originalCol.innerHTML = `
        <div class="diff-header">Original</div>
        <div class="summary-card">
            <div class="summary-text readonly">
                ${createDiffHtml(originalSummary, improvedSummary, 'original')}
            </div>
        </div>
    `;

    // Improved Column
    const improvedCol = document.createElement('div');
    improvedCol.className = 'diff-column improved';

    const diffHtml = createDiffHtml(originalSummary, improvedSummary, 'improved');

    improvedCol.innerHTML = `
        <div class="diff-header">Improved (Editable)</div>
        <div class="summary-card">
            <div class="highlight-wrapper">
                <div class="summary-text diff-view" onclick="toggleEdit(this)">${diffHtml}</div>
                <textarea class="summary-text edit-view hidden" 
                          rows="6" onblur="toggleView(this, '${originalSummary.replace(/'/g, "\\'")}')">${improvedSummary}</textarea>
            </div>
        </div>
    `;

    row.appendChild(originalCol);
    row.appendChild(improvedCol);
    container.appendChild(row);
}

function populateWorkExperience(originalWork, improvedWork) {
    const container = document.getElementById('workExperience');
    container.innerHTML = '';

    improvedWork.forEach((job, index) => {
        const originalJob = originalWork[index] || { highlights: [] };

        const row = document.createElement('div');
        row.className = 'diff-row';

        // Original Column (Read-only)
        const originalCol = document.createElement('div');
        originalCol.className = 'diff-column original';
        originalCol.innerHTML = `
            <div class="diff-header">Original</div>
            <div class="work-card">
                <div class="work-header">
                    <div class="work-company">${originalJob.company || ''}</div>
                    <div class="work-position">${originalJob.position || ''}</div>
                </div>
                <div class="work-meta">
                    <div class="work-dates">${originalJob.startDate || ''} - ${originalJob.endDate || ''}</div>
                    <div class="work-location">${originalJob.location || ''}</div>
                </div>
                <div class="work-highlights">
                    <label>Highlights:</label>
                    ${originalJob.highlights.map((h, i) => `
                        <div class="highlight-text readonly">
                            ${createDiffHtml(h, job.highlights[i] || '', 'original')}
                        </div>
                    `).join('')}
                </div>
            </div>
        `;

        // Improved Column (Editable)
        const improvedCol = document.createElement('div');
        improvedCol.className = 'diff-column improved';

        // Generate highlights HTML
        const highlightsHtml = job.highlights.map((h, hIndex) => {
            const originalH = originalJob.highlights[hIndex] || '';
            const diffHtml = createDiffHtml(originalH, h, 'improved');

            return `
                <div class="highlight-wrapper" data-index="${index}" data-highlight="${hIndex}">
                    <div class="highlight-text diff-view" onclick="toggleEdit(this)">${diffHtml}</div>
                    <textarea class="highlight-text edit-view hidden" 
                              data-job="${index}" data-highlight="${hIndex}"
                              rows="2" onblur="toggleView(this, '${originalH.replace(/'/g, "\\'")}')">${h}</textarea>
                </div>
            `;
        }).join('');

        improvedCol.innerHTML = `
            <div class="diff-header">Improved (Editable)</div>
            <div class="work-card">
                <div class="work-header">
                    <input type="text" class="work-company" data-index="${index}" 
                           value="${job.company}" placeholder="Company">
                    <input type="text" class="work-position" data-index="${index}" 
                           value="${job.position}" placeholder="Position">
                </div>
                <div class="work-meta">
                    <input type="text" class="work-dates" data-index="${index}" 
                           value="${job.startDate} - ${job.endDate}" placeholder="Dates">
                    <input type="text" class="work-location" data-index="${index}" 
                           value="${job.location || ''}" placeholder="Location">
                </div>
                <div class="work-highlights">
                    <label>Highlights (Click to edit):</label>
                    ${highlightsHtml}
                </div>
            </div>
        `;

        row.appendChild(originalCol);
        row.appendChild(improvedCol);
        container.appendChild(row);
    });
}

function populateSkills(originalSkills, improvedSkills) {
    const container = document.getElementById('skillsSection');
    container.innerHTML = '';

    improvedSkills.forEach((skillCategory, index) => {
        const originalCategory = originalSkills[index] || { keywords: [] };
        const originalKeywords = originalCategory.keywords.join(', ');
        const improvedKeywords = skillCategory.keywords.join(', ');

        const row = document.createElement('div');
        row.className = 'diff-row skills-diff-row';

        // Original
        const originalCol = document.createElement('div');
        originalCol.className = 'diff-column original';
        originalCol.innerHTML = `
            <div class="diff-header">Original</div>
            <div class="skill-card">
                <div class="skill-name">${originalCategory.name || ''}</div>
                <div class="skill-keywords readonly">
                    ${createDiffHtml(originalKeywords, improvedKeywords, 'original')}
                </div>
            </div>
        `;

        // Improved
        const improvedCol = document.createElement('div');
        improvedCol.className = 'diff-column improved';
        improvedCol.innerHTML = `
            <div class="diff-header">Improved</div>
            <div class="skill-card">
                <input type="text" class="skill-name" data-index="${index}" 
                       value="${skillCategory.name}" placeholder="Category Name">
                
                <div class="highlight-wrapper">
                    <div class="skill-keywords diff-view" onclick="toggleEdit(this)">
                        ${createDiffHtml(originalKeywords, improvedKeywords, 'improved')}
                    </div>
                    <textarea class="skill-keywords edit-view hidden" data-index="${index}" 
                              rows="2" placeholder="Keywords"
                              onblur="toggleView(this, '${originalKeywords.replace(/'/g, "\\'")}')">${improvedKeywords}</textarea>
                </div>
            </div>
        `;

        row.appendChild(originalCol);
        row.appendChild(improvedCol);
        container.appendChild(row);
    });
}

// Toggle functions for click-to-edit
window.toggleEdit = function (element) {
    element.classList.add('hidden');
    const textarea = element.nextElementSibling;
    textarea.classList.remove('hidden');
    textarea.focus();
};

window.toggleView = function (textarea, originalText) {
    const diffView = textarea.previousElementSibling;
    const newText = textarea.value;

    // Re-compute diff
    diffView.innerHTML = createDiffHtml(originalText, newText, 'improved');

    textarea.classList.add('hidden');
    diffView.classList.remove('hidden');
};

function collectResumeData() {
    // Collect work experience
    const work = [];
    document.querySelectorAll('.diff-column.improved .work-card').forEach((card, index) => {
        const company = card.querySelector('.work-company').value;
        const position = card.querySelector('.work-position').value;
        const dates = card.querySelector('.work-dates').value.split(' - ');
        const location = card.querySelector('.work-location').value;

        const highlights = [];
        card.querySelectorAll('textarea.highlight-text').forEach(textarea => {
            highlights.push(textarea.value);
        });

        work.push({
            company,
            position,
            startDate: dates[0] ? dates[0].trim() : '',
            endDate: dates[1] ? dates[1].trim() : '',
            location,
            highlights,
            website: improvedResumeData.work[index]?.website || ''
        });
    });

    // Collect skills
    const skills = [];
    document.querySelectorAll('.diff-column.improved .skill-card').forEach((card, index) => {
        const name = card.querySelector('.skill-name').value;
        const keywordsText = card.querySelector('textarea.skill-keywords').value;
        const keywords = [keywordsText]; // Keep as array with single string

        skills.push({
            name,
            keywords,
            level: improvedResumeData.skills[index]?.level || ''
        });
    });

    return {
        work,
        skills,
        professional_summary: document.querySelector('.diff-column.improved .summary-text.edit-view').value
    };
}



// Step 2: Generate PDF from edited resume
generatePdfBtn.addEventListener('click', async () => {
    // Reset states
    errorContainer.classList.add('hidden');
    generatePdfBtn.classList.add('loading');
    generatePdfBtn.disabled = true;

    try {
        // Collect edited resume data from the form fields
        const editedResume = collectResumeData();

        // Send to backend to generate PDF
        const response = await fetch('/generate-pdf', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                resume: editedResume,
                company_name: currentCompanyName
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `Server error: ${response.status}`);
        }

        // Get the PDF blob
        const blob = await response.blob();

        // Create download URL
        const url = window.URL.createObjectURL(blob);
        downloadBtn.href = url;
        downloadBtn.download = `${currentCompanyName}-resume-${Date.now()}.pdf`;

        // Update step indicator
        document.querySelectorAll('.step')[1].classList.remove('active');
        document.querySelectorAll('.step')[1].classList.add('completed');
        document.querySelectorAll('.step')[2].classList.add('active');

        // Show success
        generatePdfBtn.classList.remove('loading');
        generatePdfBtn.disabled = false;
        diffEditor.classList.add('hidden');
        resultContainer.classList.remove('hidden');

        // Smooth scroll to result
        resultContainer.scrollIntoView({ behavior: 'smooth', block: 'center' });

    } catch (error) {
        console.error('Error:', error);
        generatePdfBtn.classList.remove('loading');
        generatePdfBtn.disabled = false;
        showError(error.message || 'Failed to generate PDF. Please try again.');
    }
});

function showError(message) {
    submitBtn.classList.remove('loading');
    submitBtn.disabled = false;
    errorMessage.textContent = message;
    errorContainer.classList.remove('hidden');
    errorContainer.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function resetForm() {
    form.reset();
    charCount.textContent = '0';
    resultContainer.classList.add('hidden');
    errorContainer.classList.add('hidden');
    diffEditor.classList.add('hidden');
    submitBtn.classList.remove('loading');
    submitBtn.disabled = false;
    generatePdfBtn.classList.remove('loading');
    generatePdfBtn.disabled = false;

    // Reset step indicators
    document.querySelectorAll('.step').forEach((step, index) => {
        step.classList.remove('active', 'completed');
        if (index === 0) {
            // First step is always ready
        }
    });

    // Clear stored data
    currentCompanyName = '';
    originalResumeData = null;
    improvedResumeData = null;

    // Scroll to form
    form.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// Add smooth scroll behavior for better UX
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({ behavior: 'smooth' });
        }
    });
});

// Add entrance animations on load
window.addEventListener('load', () => {
    document.body.style.opacity = '0';
    setTimeout(() => {
        document.body.style.transition = 'opacity 0.5s ease';
        document.body.style.opacity = '1';
    }, 100);

});

// History Functions
async function fetchHistory() {
    try {
        historyList.innerHTML = '<div class="loading-history">Loading history...</div>';
        const response = await fetch('/history');
        if (!response.ok) throw new Error('Failed to fetch history');

        const history = await response.json();
        renderHistory(history);
    } catch (error) {
        console.error('Error fetching history:', error);
        historyList.innerHTML = '<div class="error-message">Failed to load history</div>';
    }
}

function renderHistory(history) {
    if (history.length === 0) {
        historyList.innerHTML = '<div class="empty-history">No generated resumes yet.</div>';
        return;
    }

    // Sort by timestamp descending
    history.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

    historyList.innerHTML = history.map(item => `
        <div class="history-item">
            <div class="history-info">
                <div class="history-company">${item.company_name}</div>
                <div class="history-date">${new Date(item.timestamp).toLocaleString()}</div>
            </div>
            <div class="history-actions">
                <button class="icon-btn" onclick="viewPdf('${item.id}')" title="View PDF">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        <path d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                </button>
                <a href="/download/${item.id}/pdf" class="icon-btn" title="Download PDF" download>
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                </a>
                <a href="/download/${item.id}/json" class="icon-btn" title="View JSON" target="_blank">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                </a>
            </div>
        </div>
    `).join('');
}

// PDF Viewer Functions
window.viewPdf = function (id) {
    pdfViewer.src = `/download/${id}/pdf`;
    pdfModal.classList.remove('hidden');
    document.body.style.overflow = 'hidden'; // Prevent background scrolling
};

window.closePdfModal = function () {
    pdfModal.classList.add('hidden');
    pdfViewer.src = '';
    document.body.style.overflow = ''; // Restore scrolling
};

// Close modal on outside click
pdfModal.addEventListener('click', (e) => {
    if (e.target === pdfModal) {
        closePdfModal();
    }
});

// Event Listeners
refreshHistoryBtn.addEventListener('click', fetchHistory);

// Initial load
fetchHistory();
fetchActiveProfile();

async function fetchActiveProfile() {
    try {
        const response = await fetch('/profiles');
        const data = await response.json();
        document.getElementById('activeProfileName').textContent = data.active;
    } catch (error) {
        console.error('Error fetching active profile:', error);
        document.getElementById('activeProfileName').textContent = 'Error';
    }
}
