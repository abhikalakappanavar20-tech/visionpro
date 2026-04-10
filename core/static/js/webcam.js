/**
 * Webcam Scanner - VeriVision
 * Handles camera access, photo capture, video recording, and upload
 */

// Global variables
let videoStream = null;
let mediaRecorder = null;
let recordedChunks = [];
let capturedBlob = null;
let captureType = 'photo'; // 'photo' or 'video'
let recordingTimer = null;
let recordingSeconds = 0;
const MAX_RECORDING_DURATION = 30; // seconds

// DOM elements
const videoElement = document.getElementById('webcamVideo');
const canvasElement = document.getElementById('captureCanvas');
const previewImage = document.getElementById('previewImage');
const previewVideo = document.getElementById('previewVideo');
const countdownOverlay = document.getElementById('countdownOverlay');
const recordingIndicator = document.getElementById('recordingIndicator');
const recordingTime = document.getElementById('recordingTime');
const loadingOverlay = document.getElementById('loadingOverlay');
const statusMessage = document.getElementById('statusMessage');
const statusText = document.getElementById('statusText');

// Buttons
const startCameraBtn = document.getElementById('startCameraBtn');
const capturePhotoBtn = document.getElementById('capturePhotoBtn');
const countdownBtn = document.getElementById('countdownBtn');
const startRecordingBtn = document.getElementById('startRecordingBtn');
const stopRecordingBtn = document.getElementById('stopRecordingBtn');
const analyzeBtn = document.getElementById('analyzeBtn');
const retakeBtn = document.getElementById('retakeBtn');

/**
 * Set capture mode (photo or video)
 */
function setMode(mode) {
    captureType = mode;

    // Update UI
    document.querySelectorAll('.mode-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`[data-mode="${mode}"]`).classList.add('active');

    // Show/hide controls
    if (mode === 'photo') {
        document.getElementById('photoControls').style.display = 'block';
        document.getElementById('videoControls').style.display = 'none';
    } else {
        document.getElementById('photoControls').style.display = 'none';
        document.getElementById('videoControls').style.display = 'block';
    }

    // Reset state
    retakeCapture();
}

/**
 * Start camera
 */
async function startCamera() {
    try {
        showStatus('Requesting camera access...');

        // Request camera access
        const constraints = {
            video: {
                width: { ideal: 1920 },
                height: { ideal: 1080 },
                facingMode: 'user'
            },
            audio: false
        };

        videoStream = await navigator.mediaDevices.getUserMedia(constraints);
        videoElement.srcObject = videoStream;

        // Show capture controls
        if (captureType === 'photo') {
            startCameraBtn.style.display = 'none';
            capturePhotoBtn.style.display = 'inline-block';
            countdownBtn.style.display = 'inline-block';
        } else {
            document.getElementById('startCameraVideoBtn').style.display = 'none';
            startRecordingBtn.style.display = 'inline-block';
        }

        showStatus('Camera active! Ready to capture.', 'success');
        setTimeout(hideStatus, 3000);

    } catch (error) {
        console.error('Camera error:', error);
        showStatus('Camera access denied or not available. Please allow camera access and try again.', 'error');
    }
}

/**
 * Capture photo from video stream
 */
function capturePhoto() {
    if (!videoStream) {
        showStatus('Please start the camera first.', 'error');
        return;
    }

    // Flash effect
    createFlashEffect();

    // Set canvas size to match video
    canvasElement.width = videoElement.videoWidth;
    canvasElement.height = videoElement.videoHeight;

    // Draw current video frame to canvas
    const ctx = canvasElement.getContext('2d');

    // Mirror the image (since video is mirrored)
    ctx.translate(canvasElement.width, 0);
    ctx.scale(-1, 1);
    ctx.drawImage(videoElement, 0, 0);

    // Convert to blob
    canvasElement.toBlob(blob => {
        capturedBlob = blob;

        // Show preview
        previewImage.src = URL.createObjectURL(blob);
        document.getElementById('imagePreview').style.display = 'block';
        document.getElementById('videoPreview').style.display = 'none';

        // Show preview section and analyze button
        document.getElementById('previewSection').classList.add('active');
        analyzeBtn.style.display = 'inline-block';
        retakeBtn.style.display = 'inline-block';

        // Hide capture buttons
        capturePhotoBtn.style.display = 'none';
        countdownBtn.style.display = 'none';

        // Show info
        const fileSize = (blob.size / 1024).toFixed(2);
        document.getElementById('previewInfo').textContent =
            `Photo captured - ${fileSize} KB - ${videoElement.videoWidth}x${videoElement.videoHeight}`;

        showStatus('Photo captured! Click "Analyze" to process.', 'success');
    }, 'image/jpeg', 0.95);
}

/**
 * Capture photo with countdown timer
 */
function captureWithCountdown() {
    if (!videoStream) {
        showStatus('Please start the camera first.', 'error');
        return;
    }

    let countdown = 3;
    countdownOverlay.style.display = 'flex';
    countdownOverlay.textContent = countdown;

    const timer = setInterval(() => {
        countdown--;
        if (countdown > 0) {
            countdownOverlay.textContent = countdown;
        } else {
            clearInterval(timer);
            countdownOverlay.style.display = 'none';
            capturePhoto();
        }
    }, 1000);
}

/**
 * Start video recording
 */
function startRecording() {
    if (!videoStream) {
        showStatus('Please start the camera first.', 'error');
        return;
    }

    try {
        recordedChunks = [];

        // Check supported MIME types
        let mimeType = 'video/webm;codecs=vp9';
        if (!MediaRecorder.isTypeSupported(mimeType)) {
            mimeType = 'video/webm'; // Fallback
        }

        // Create MediaRecorder
        mediaRecorder = new MediaRecorder(videoStream, {
            mimeType: mimeType,
            videoBitsPerSecond: 2500000 // 2.5 Mbps
        });

        // Handle data available
        mediaRecorder.ondataavailable = event => {
            if (event.data.size > 0) {
                recordedChunks.push(event.data);
            }
        };

        // Handle recording stop
        mediaRecorder.onstop = () => {
            const blob = new Blob(recordedChunks, { type: mimeType });
            capturedBlob = blob;

            // Show preview
            previewVideo.src = URL.createObjectURL(blob);
            document.getElementById('imagePreview').style.display = 'none';
            document.getElementById('videoPreview').style.display = 'block';

            // Show preview section and analyze button
            document.getElementById('previewSection').classList.add('active');
            analyzeBtn.style.display = 'inline-block';
            retakeBtn.style.display = 'inline-block';

            // Hide recording controls
            startRecordingBtn.style.display = 'none';
            stopRecordingBtn.style.display = 'none';

            // Show info
            const fileSize = (blob.size / 1024 / 1024).toFixed(2);
            document.getElementById('previewInfo').textContent =
                `Video recorded - ${fileSize} MB - ${recordingSeconds}s`;

            // Reset timer
            if (recordingTimer) {
                clearInterval(recordingTimer);
                recordingTimer = null;
            }
            recordingSeconds = 0;

            showStatus('Recording stopped! Click "Analyze" to process.', 'success');
        };

        // Start recording
        mediaRecorder.start(100); // Collect data every 100ms

        // Update UI
        startRecordingBtn.style.display = 'none';
        stopRecordingBtn.style.display = 'inline-block';
        recordingIndicator.style.display = 'flex';

        // Start timer
        recordingSeconds = 0;
        updateRecordingTimer();
        recordingTimer = setInterval(() => {
            recordingSeconds++;
            updateRecordingTimer();

            // Auto-stop at max duration
            if (recordingSeconds >= MAX_RECORDING_DURATION) {
                stopRecording();
            }
        }, 1000);

        showStatus('Recording started... Click "Stop" when done.', 'success');

    } catch (error) {
        console.error('Recording error:', error);
        showStatus('Failed to start recording. Your browser may not support video recording.', 'error');
    }
}

/**
 * Stop video recording
 */
function stopRecording() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
    }
}

/**
 * Update recording timer display
 */
function updateRecordingTimer() {
    recordingTime.textContent = `Recording: ${recordingSeconds}s / ${MAX_RECORDING_DURATION}s`;
}

/**
 * Analyze captured content
 */
async function analyzeCapture() {
    if (!capturedBlob) {
        showStatus('No capture to analyze. Please capture a photo or video first.', 'error');
        return;
    }

    // Show loading overlay
    loadingOverlay.classList.add('active');

    try {
        // Create form data
        const formData = new FormData();

        // Determine file type and create file
        let file;
        if (captureType === 'photo') {
            file = new File([capturedBlob], 'webcam-capture.jpg', { type: 'image/jpeg' });
        } else {
            file = new File([capturedBlob], 'webcam-recording.webm', { type: 'video/webm' });
        }

        formData.append('file', file);
        formData.append('source', 'webcam');

        // Send to server
        const response = await fetch('/scan/', {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': getCsrfToken()
            }
        });

        if (!response.ok) {
            throw new Error('Analysis failed');
        }

        // Get the scan ID from response
        const html = await response.text();

        // Parse HTML to find scan ID
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');

        // Look for redirect or scan ID in the response
        const scanIdMatch = html.match(/result\/(\d+)\//);
        if (scanIdMatch) {
            const scanId = scanIdMatch[1];
            window.location.href = `/result/${scanId}/`;
        } else {
            // If no scan ID found, display the response directly
            document.documentElement.innerHTML = html;
        }

    } catch (error) {
        console.error('Analysis error:', error);
        loadingOverlay.classList.remove('active');
        showStatus('Analysis failed: ' + error.message, 'error');
    }
}

/**
 * Retake capture (reset to capture mode)
 */
function retakeCapture() {
    // Clear captured blob
    capturedBlob = null;

    // Hide preview section
    document.getElementById('previewSection').classList.remove('active');

    // Reset video/image preview
    previewImage.src = '';
    previewVideo.src = '';

    // Show capture buttons again
    if (captureType === 'photo') {
        capturePhotoBtn.style.display = 'inline-block';
        countdownBtn.style.display = 'inline-block';
    } else {
        startRecordingBtn.style.display = 'inline-block';
    }

    // Hide analyze and retake buttons
    analyzeBtn.style.display = 'none';
    retakeBtn.style.display = 'none';

    hideStatus();
}

/**
 * Create flash effect
 */
function createFlashEffect() {
    const flash = document.createElement('div');
    flash.className = 'flash-effect';
    document.body.appendChild(flash);

    setTimeout(() => {
        flash.remove();
    }, 100);
}

/**
 * Show status message
 */
function showStatus(message, type = 'info') {
    statusText.textContent = message;
    statusMessage.style.display = 'block';

    // Set color based on type
    if (type === 'error') {
        statusMessage.style.borderColor = '#ff3b30';
        statusMessage.style.color = '#ff3b30';
    } else if (type === 'success') {
        statusMessage.style.borderColor = '#34c759';
        statusMessage.style.color = '#34c759';
    } else {
        statusMessage.style.borderColor = 'rgba(0, 212, 255, 0.3)';
        statusMessage.style.color = '#00d4ff';
    }
}

/**
 * Hide status message
 */
function hideStatus() {
    statusMessage.style.display = 'none';
}

/**
 * Cleanup when page unloads
 */
window.addEventListener('beforeunload', () => {
    // Stop media tracks
    if (videoStream) {
        videoStream.getTracks().forEach(track => track.stop());
    }

    // Stop recording
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
    }

    // Clear timer
    if (recordingTimer) {
        clearInterval(recordingTimer);
    }
});

/**
 * Mobile navigation toggle
 */
document.getElementById('navToggle')?.addEventListener('click', function() {
    document.querySelector('.nav-menu').classList.toggle('active');
});

/**
 * Initialize
 */
document.addEventListener('DOMContentLoaded', () => {
    console.log('Webcam scanner initialized');
    showStatus('Click "Start Camera" to begin', 'info');
});
