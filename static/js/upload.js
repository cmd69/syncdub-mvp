/**
 * SyncDub MVP - JavaScript para subida de archivos
 */

document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.getElementById('uploadForm');
    const originalVideo = document.getElementById('originalVideo');
    const dubbedVideo = document.getElementById('dubbedVideo');
    const submitBtn = document.getElementById('submitBtn');
    const progressSection = document.getElementById('progressSection');
    const resultSection = document.getElementById('resultSection');
    const errorSection = document.getElementById('errorSection');
    
    // File upload handlers
    setupFileUpload('originalVideo', 'originalUploadArea');
    setupFileUpload('dubbedVideo', 'dubbedUploadArea');
    
    // Form submission
    uploadForm.addEventListener('submit', handleFormSubmit);
    
    function setupFileUpload(inputId, areaId) {
        const input = document.getElementById(inputId);
        const area = document.getElementById(areaId);
        const placeholder = area.querySelector('.upload-placeholder');
        const fileInfo = area.querySelector('.file-info');
        
        // File selection
        input.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                handleFileSelection(file, area, placeholder, fileInfo);
            }
        });
        
        // Drag and drop
        area.addEventListener('dragover', function(e) {
            e.preventDefault();
            area.classList.add('dragover');
        });
        
        area.addEventListener('dragleave', function(e) {
            e.preventDefault();
            area.classList.remove('dragover');
        });
        
        area.addEventListener('drop', function(e) {
            e.preventDefault();
            area.classList.remove('dragover');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                const file = files[0];
                input.files = files;
                handleFileSelection(file, area, placeholder, fileInfo);
            }
        });
    }
    
    function handleFileSelection(file, area, placeholder, fileInfo) {
        // Validate file
        const validation = validateVideoFile(file);
        if (!validation.valid) {
            showNotification(validation.error, 'danger');
            return;
        }
        
        // Update UI
        placeholder.classList.add('d-none');
        fileInfo.classList.remove('d-none');
        
        fileInfo.querySelector('.filename').textContent = file.name;
        fileInfo.querySelector('.filesize').textContent = `(${formatFileSize(file.size)})`;
        
        area.style.borderColor = '#198754';
        area.style.backgroundColor = '#d1e7dd';
        
        // Check if both files are selected
        checkFormReady();
    }
    
    function checkFormReady() {
        const originalFile = originalVideo.files[0];
        const dubbedFile = dubbedVideo.files[0];
        
        if (originalFile && dubbedFile) {
            submitBtn.disabled = false;
            submitBtn.classList.remove('btn-secondary');
            submitBtn.classList.add('btn-primary');
        }
    }
    
    async function handleFormSubmit(e) {
        e.preventDefault();
        
        const originalFile = originalVideo.files[0];
        const dubbedFile = dubbedVideo.files[0];
        
        if (!originalFile || !dubbedFile) {
            showNotification('Por favor selecciona ambos archivos de video', 'warning');
            return;
        }
        
        // Disable form
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Subiendo...';
        
        // Show progress section
        progressSection.classList.remove('d-none');
        hideOtherSections();
        
        try {
            // Create FormData
            const formData = new FormData();
            formData.append('original_video', originalFile);
            formData.append('dubbed_video', dubbedFile);
            
            // Upload files
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (response.ok) {
                // Start monitoring progress
                monitorProgress(result.task_id);
            } else {
                throw new Error(result.error || 'Error en la subida');
            }
            
        } catch (error) {
            handleUploadError(error);
        }
    }
    
    function monitorProgress(taskId) {
        const progressBar = document.getElementById('progressBar');
        const progressMessage = document.getElementById('progressMessage');
        
        const checkStatus = async () => {
            try {
                const response = await fetch(`/api/status/${taskId}`);
                const status = await response.json();
                
                // Update progress
                updateProgressBar(progressBar, status.progress || 0);
                progressMessage.textContent = status.message || 'Procesando...';
                
                if (status.status === 'completed') {
                    showSuccess(taskId);
                } else if (status.status === 'error') {
                    throw new Error(status.error || 'Error en el procesamiento');
                } else {
                    // Continue monitoring
                    setTimeout(checkStatus, 2000);
                }
                
            } catch (error) {
                handleUploadError(error);
            }
        };
        
        // Start monitoring
        checkStatus();
    }
    
    function showSuccess(taskId) {
        hideOtherSections();
        resultSection.classList.remove('d-none');
        
        const downloadBtn = document.getElementById('downloadBtn');
        downloadBtn.href = `/api/download/${taskId}`;
        
        showNotification('¡Sincronización completada exitosamente!', 'success');
    }
    
    function handleUploadError(error) {
        hideOtherSections();
        errorSection.classList.remove('d-none');
        
        const errorMessage = document.getElementById('errorMessage');
        errorMessage.textContent = error.message || 'Ha ocurrido un error durante el procesamiento';
        
        // Reset form
        resetForm();
        
        showNotification(error.message || 'Error en el procesamiento', 'danger');
    }
    
    function hideOtherSections() {
        progressSection.classList.add('d-none');
        resultSection.classList.add('d-none');
        errorSection.classList.add('d-none');
    }
    
    function resetForm() {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-sync-alt me-2"></i>Iniciar Sincronización';
        submitBtn.classList.remove('btn-secondary');
        submitBtn.classList.add('btn-primary');
    }
});

// Utility function to show upload progress
function showUploadProgress(loaded, total) {
    const percentage = Math.round((loaded / total) * 100);
    const progressBar = document.getElementById('progressBar');
    
    if (progressBar) {
        progressBar.style.width = `${Math.min(percentage, 95)}%`;
        progressBar.textContent = `Subiendo... ${Math.min(percentage, 95)}%`;
    }
}

