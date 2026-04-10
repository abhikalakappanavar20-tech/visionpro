/**
 * VeriVision - Scan Page JavaScript
 * File upload and scanning functionality
 */

document.addEventListener('DOMContentLoaded', function() {
    initializeScanPage();
});

function initializeScanPage() {
    // Scan type selector
    const scanTypeBtns = document.querySelectorAll('.scan-type-btn');
    const fileSection = document.getElementById('fileSection');
    const urlSection = document.getElementById('urlSection');

    scanTypeBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const type = this.getAttribute('data-type');

            // Update active button
            scanTypeBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');

            // Show/hide sections
            if (type === 'file') {
                fileSection.style.display = 'block';
                urlSection.style.display = 'none';
            } else {
                fileSection.style.display = 'none';
                urlSection.style.display = 'block';
            }
        });
    });

    // File upload handling
    const uploadZone = document.getElementById('uploadZone');
    const fileInput = document.querySelector('input[type="file"]');
    const selectedFile = document.getElementById('selectedFile');
    const fileName = document.getElementById('fileName');
    const fileSize = document.getElementById('fileSize');
    const removeFileBtn = document.getElementById('removeFile');

    if (uploadZone && fileInput) {
        // Click to upload
        uploadZone.addEventListener('click', function(e) {
            if (e.target === uploadZone || uploadZone.contains(e.target)) {
                fileInput.click();
            }
        });

        // Drag and drop
        uploadZone.addEventListener('dragover', function(e) {
            e.preventDefault();
            uploadZone.classList.add('dragover');
        });

        uploadZone.addEventListener('dragleave', function(e) {
            e.preventDefault();
            uploadZone.classList.remove('dragover');
        });

        uploadZone.addEventListener('drop', function(e) {
            e.preventDefault();
            uploadZone.classList.remove('dragover');

            const files = e.dataTransfer.files;
            if (files.length > 0) {
                handleFileSelect(files[0]);
            }
        });

        // File input change
        fileInput.addEventListener('change', function() {
            if (this.files.length > 0) {
                handleFileSelect(this.files[0]);
            }
        });

        // Remove file
        if (removeFileBtn) {
            removeFileBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                clearFileSelection();
            });
        }
    }

    function handleFileSelect(file) {
        // Validate file type
        const acceptedTypes = [
            '.jpg', '.jpeg', '.png', '.gif', '.webp',
            '.mp4', '.avi', '.mov', '.mkv',
            '.wav', '.mp3', '.m4a', '.flac'
        ];

        const fileExt = '.' + file.name.split('.').pop().toLowerCase();

        if (!acceptedTypes.includes(fileExt)) {
            showToast('Invalid file type. Please upload an image, video, or audio file.', 'error');
            clearFileSelection();
            return;
        }

        // Validate file size (5GB limit)
        if (file.size > 5 *1024 * 1024 * 1024) {
            showToast('File size exceeds 5GB limit.', 'error');
            clearFileSelection();
            return;
        }

        // Show file info
        if (fileName && fileSize) {
            fileName.textContent = file.name;
            fileSize.textContent = formatBytes(file.size);
        }

        if (selectedFile && uploadZone) {
            selectedFile.style.display = 'flex';
            uploadZone.style.display = 'none';
        }
    }

    function clearFileSelection() {
        if (fileInput) {
            fileInput.value = '';
        }
        if (selectedFile) {
            selectedFile.style.display = 'none';
        }
        if (uploadZone) {
            uploadZone.style.display = 'block';
        }
    }

    // Form submission
    const uploadForm = document.getElementById('uploadForm');
    if (uploadForm) {
        uploadForm.addEventListener('submit', function(e) {
            const fileInput = this.querySelector('input[type="file"]');
            const submitBtn = document.getElementById('submitBtn');

            if (!fileInput.files.length) {
                e.preventDefault();
                showToast('Please select a file to upload.', 'error');
                return;
            }

            // Show loading state
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Analyzing...';

                // Simulate analysis stages
                simulateAnalysis();
            }
        });
    }

    // URL form handling
    const urlForm = document.querySelector('.url-form');
    if (urlForm) {
        urlForm.addEventListener('submit', function() {
            const submitBtn = this.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Analyzing...';
            }
        });
    }
}

/**
 * Simulate analysis stages for visual feedback
 */
function simulateAnalysis() {
    const stages = [
        'Extracting metadata...',
        'Analyzing facial landmarks...',
        'Checking frequency domain artifacts...',
        'Detecting compression inconsistencies...',
        'Running forensic database check...',
        'Generating explainable heatmap...',
        'Calculating trust metrics...',
        'Finalizing analysis...'
    ];

    let currentStage = 0;

    // You could display these stages in a modal or progress bar
    const interval = setInterval(() => {
        if (currentStage < stages.length) {
            console.log(stages[currentStage]); // For debugging
            currentStage++;
        } else {
            clearInterval(interval);
        }
    }, 500);
}

/**
 * Format bytes to human readable format
 */
function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';

    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];

    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

/**
 * Show toast notification
 */
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'times-circle' : 'info-circle'}"></i>
        <span>${message}</span>
    `;

    toast.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: var(--card-bg);
        border-left: 4px solid ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#06b6d4'};
        padding: 1rem 1.5rem;
        border-radius: 0.5rem;
        box-shadow: 0 10px 15px rgba(0, 0, 0, 0.5);
        display: flex;
        align-items: center;
        gap: 0.75rem;
        z-index: 10000;
        animation: slideIn 0.3s ease;
    `;

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Add slideIn animation
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
`;
document.head.appendChild(style);
