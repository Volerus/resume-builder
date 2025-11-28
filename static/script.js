// Character counter
const jobDescription = document.getElementById('jobDescription');
const charCount = document.getElementById('charCount');

jobDescription.addEventListener('input', () => {
    charCount.textContent = jobDescription.value.length;
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
            body: JSON.stringify({ description })
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
