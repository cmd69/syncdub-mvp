/**
 * SyncDub MVP - Upload Page JavaScript
 */

class UploadManager {
    constructor() {
        this.currentTaskId = null;
        this.progressInterval = null;
        this.originalCurrentPath = '';
        this.dubbedCurrentPath = '';
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.setupFileInputs();
        this.setupSourceToggling();
        this.loadVolumeFiles();
    }
    
    setupEventListeners() {
        // Form submission
        const form = document.getElementById('uploadForm');
        if (form) {
            form.addEventListener('submit', (e) => this.handleFormSubmit(e));
        }
        
        // Source radio buttons
        document.querySelectorAll('input[name="original_source"]').forEach(radio => {
            radio.addEventListener('change', () => this.toggleOriginalSource());
        });
        
        document.querySelectorAll('input[name="dubbed_source"]').forEach(radio => {
            radio.addEventListener('change', () => this.toggleDubbedSource());
        });
        
        // Custom filename validation
        const customFilename = document.getElementById('customFilename');
        if (customFilename) {
            customFilename.addEventListener('input', () => this.validateCustomFilename());
        }
    }
    
    setupFileInputs() {
        // Original video input
        const originalInput = document.getElementById('originalVideo');
        if (originalInput) {
            originalInput.addEventListener('change', (e) => this.handleFileSelect(e, 'original'));
            this.setupDragAndDrop(originalInput.closest('.upload-area'), originalInput);
        }
        
        // Dubbed video input
        const dubbedInput = document.getElementById('dubbedVideo');
        if (dubbedInput) {
            dubbedInput.addEventListener('change', (e) => this.handleFileSelect(e, 'dubbed'));
            this.setupDragAndDrop(dubbedInput.closest('.upload-area'), dubbedInput);
        }
    }
    
    setupDragAndDrop(uploadArea, fileInput) {
        if (!uploadArea || !fileInput) return;
        
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
            });
        });
        
        ['dragenter', 'dragover'].forEach(eventName => {
            uploadArea.addEventListener(eventName, () => {
                uploadArea.classList.add('dragover');
            });
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, () => {
                uploadArea.classList.remove('dragover');
            });
        });
        
        uploadArea.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                fileInput.files = files;
                const event = new Event('change', { bubbles: true });
                fileInput.dispatchEvent(event);
            }
        });
    }
    
    setupSourceToggling() {
        this.toggleOriginalSource();
        this.toggleDubbedSource();
    }
    
    toggleOriginalSource() {
        const uploadSelected = document.getElementById('original_upload').checked;
        const uploadArea = document.getElementById('originalUploadArea');
        const volumeArea = document.getElementById('originalVolumeArea');
        
        if (uploadArea) {
            uploadArea.style.display = uploadSelected ? 'block' : 'none';
        }
        if (volumeArea) {
            volumeArea.style.display = uploadSelected ? 'none' : 'block';
        }
        
        this.validateForm();
    }
    
    toggleDubbedSource() {
        const uploadSelected = document.getElementById('dubbed_upload').checked;
        const uploadArea = document.getElementById('dubbedUploadArea');
        const volumeArea = document.getElementById('dubbedVolumeArea');
        
        if (uploadArea) {
            uploadArea.style.display = uploadSelected ? 'block' : 'none';
        }
        if (volumeArea) {
            volumeArea.style.display = uploadSelected ? 'none' : 'block';
        }
        
        this.validateForm();
    }
    
    handleFileSelect(event, type) {
        const file = event.target.files[0];
        const uploadArea = event.target.closest('.upload-area');
        
        if (!file || !uploadArea) return;
        
        // Validate file
        const validation = SyncDub.validateFile(file);
        if (!validation.valid) {
            SyncDub.showToast(validation.error, 'danger');
            event.target.value = '';
            this.clearFileInfo(uploadArea);
            this.validateForm();
            return;
        }
        
        // Show file info
        this.showFileInfo(uploadArea, file);
        this.validateForm();
    }
    
    showFileInfo(uploadArea, file) {
        const placeholder = uploadArea.querySelector('.upload-placeholder');
        const fileInfo = uploadArea.querySelector('.file-info');
        
        if (placeholder) placeholder.classList.add('d-none');
        if (fileInfo) {
            fileInfo.classList.remove('d-none');
            const filename = fileInfo.querySelector('.filename');
            const filesize = fileInfo.querySelector('.filesize');
            
            if (filename) filename.textContent = file.name;
            if (filesize) filesize.textContent = `(${SyncDub.formatFileSize(file.size)})`;
        }
    }
    
    clearFileInfo(uploadArea) {
        const placeholder = uploadArea.querySelector('.upload-placeholder');
        const fileInfo = uploadArea.querySelector('.file-info');
        
        if (placeholder) placeholder.classList.remove('d-none');
        if (fileInfo) fileInfo.classList.add('d-none');
    }
    
    loadVolumeFiles() {
        this.loadVolumeFilesForType('original');
        this.loadVolumeFilesForType('dubbed');
    }
    
    loadVolumeFilesForType(type) {
        const fileList = document.getElementById(`${type}FileList`);
        if (!fileList) return;
        
        const currentPath = type === 'original' ? this.originalCurrentPath : this.dubbedCurrentPath;
        
        fetch(`/api/media/list?path=${encodeURIComponent(currentPath)}`)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    this.showVolumeError(fileList, data.error);
                } else {
                    this.displayVolumeFiles(type, data.items, data.breadcrumbs);
                }
            })
            .catch(error => {
                console.error('Error loading volume files:', error);
                this.showVolumeError(fileList, 'Error cargando archivos del servidor');
            });
    }
    
    displayVolumeFiles(type, items, breadcrumbs) {
        const fileList = document.getElementById(`${type}FileList`);
        const breadcrumb = document.getElementById(`${type}Breadcrumb`);
        
        if (!fileList) return;
        
        // Update breadcrumb
        if (breadcrumb && breadcrumbs) {
            breadcrumb.innerHTML = breadcrumbs.map(crumb => `
                <li class="breadcrumb-item ${crumb.path === (type === 'original' ? this.originalCurrentPath : this.dubbedCurrentPath) ? 'active' : ''}">
                    ${crumb.path === (type === 'original' ? this.originalCurrentPath : this.dubbedCurrentPath) ? 
                        crumb.name : 
                        `<a href="#" data-path="${crumb.path}">${crumb.name}</a>`
                    }
                </li>
            `).join('');
            
            // Add breadcrumb click handlers
            breadcrumb.querySelectorAll('a').forEach(link => {
                link.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.navigateToPath(type, link.dataset.path);
                });
            });
        }
        
        // Display files
        if (items.length === 0) {
            fileList.innerHTML = `
                <div class="text-center text-muted py-3">
                    <i class="fas fa-folder-open me-2"></i>
                    No hay archivos en este directorio
                </div>
            `;
        } else {
            fileList.innerHTML = items.map(item => this.createFileItem(type, item)).join('');
            
            // Add click handlers
            fileList.querySelectorAll('.file-item').forEach(item => {
                item.addEventListener('click', () => this.handleVolumeItemClick(type, item));
            });
        }
    }
    
    createFileItem(type, item) {
        const icon = item.type === 'directory' ? 
            (item.is_parent ? 'fa-level-up-alt' : 'fa-folder') : 
            'fa-file-video';
        const iconColor = item.type === 'directory' ? 'text-warning' : 'text-info';
        
        return `
            <div class="file-item ${item.type}" data-path="${item.path}" data-type="${item.type}" data-name="${item.name}">
                <div class="d-flex align-items-center">
                    <i class="fas ${icon} ${iconColor} me-2"></i>
                    <div class="flex-grow-1">
                        <div class="fw-medium">${item.name}</div>
                        ${item.type === 'file' ? `<small class="text-muted">${item.size_formatted}</small>` : ''}
                    </div>
                    ${item.type === 'directory' ? '<i class="fas fa-chevron-right text-muted"></i>' : ''}
                </div>
            </div>
        `;
    }
    
    handleVolumeItemClick(type, itemElement) {
        const itemType = itemElement.dataset.type;
        const itemPath = itemElement.dataset.path;
        const itemName = itemElement.dataset.name;
        
        if (itemType === 'directory') {
            this.navigateToPath(type, itemPath);
        } else {
            this.selectVolumeFile(type, itemPath, itemName);
        }
    }
    
    navigateToPath(type, path) {
        if (type === 'original') {
            this.originalCurrentPath = path;
        } else {
            this.dubbedCurrentPath = path;
        }
        
        this.loadVolumeFilesForType(type);
    }
    
    selectVolumeFile(type, path, name) {
        // Clear previous selections
        const fileList = document.getElementById(`${type}FileList`);
        if (fileList) {
            fileList.querySelectorAll('.file-item').forEach(item => {
                item.classList.remove('selected');
            });
        }
        
        // Select current item
        const selectedItem = fileList.querySelector(`[data-path="${path}"]`);
        if (selectedItem) {
            selectedItem.classList.add('selected');
        }
        
        // Update hidden input and info
        const hiddenInput = document.getElementById(`${type}VolumeFile`);
        const volumeInfo = document.getElementById(`${type}VolumeInfo`);
        const selectedFileSpan = document.getElementById(`${type}SelectedFile`);
        
        if (hiddenInput) hiddenInput.value = path;
        if (volumeInfo) volumeInfo.classList.remove('d-none');
        if (selectedFileSpan) selectedFileSpan.textContent = `Seleccionado: ${name}`;
        
        this.validateForm();
    }
    
    showVolumeError(fileList, error) {
        fileList.innerHTML = `
            <div class="text-center text-danger py-3">
                <i class="fas fa-exclamation-triangle me-2"></i>
                ${error}
            </div>
        `;
    }
    
    validateCustomFilename() {
        const input = document.getElementById('customFilename');
        if (!input) return;
        
        const value = input.value.trim();
        if (value) {
            // Remove invalid characters
            const cleaned = value.replace(/[^a-zA-Z0-9\-_\s]/g, '');
            if (cleaned !== value) {
                input.value = cleaned;
                SyncDub.showToast('Se han removido caracteres no válidos del nombre', 'warning');
            }
        }
    }
    
    validateForm() {
        const submitBtn = document.getElementById('submitBtn');
        if (!submitBtn) return;
        
        let isValid = true;
        
        // Check original source
        const originalUpload = document.getElementById('original_upload').checked;
        if (originalUpload) {
            const originalFile = document.getElementById('originalVideo').files[0];
            if (!originalFile) isValid = false;
        } else {
            const originalVolumeFile = document.getElementById('originalVolumeFile').value;
            if (!originalVolumeFile) isValid = false;
        }
        
        // Check dubbed source
        const dubbedUpload = document.getElementById('dubbed_upload').checked;
        if (dubbedUpload) {
            const dubbedFile = document.getElementById('dubbedVideo').files[0];
            if (!dubbedFile) isValid = false;
        } else {
            const dubbedVolumeFile = document.getElementById('dubbedVolumeFile').value;
            if (!dubbedVolumeFile) isValid = false;
        }
        
        submitBtn.disabled = !isValid;
    }
    
    async handleFormSubmit(event) {
        event.preventDefault();
        
        const formData = new FormData(event.target);
        
        try {
            this.showProgress();
            
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (response.ok) {
                this.currentTaskId = result.task_id;
                this.startProgressMonitoring();
                SyncDub.showToast('Procesamiento iniciado correctamente', 'success');
            } else {
                throw new Error(result.error || 'Error en el servidor');
            }
            
        } catch (error) {
            console.error('Upload error:', error);
            this.showError(error.message);
            SyncDub.showToast(error.message, 'danger');
        }
    }
    
    showProgress() {
        document.getElementById('progressSection').classList.remove('d-none');
        document.getElementById('resultSection').classList.add('d-none');
        document.getElementById('errorSection').classList.add('d-none');
    }
    
    startProgressMonitoring() {
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
        }
        
        this.progressInterval = setInterval(() => {
            this.checkProgress();
        }, 2000);
        
        // Initial check
        this.checkProgress();
    }
    
    async checkProgress() {
        if (!this.currentTaskId) return;
        
        try {
            const response = await fetch(`/api/status/${this.currentTaskId}`);
            const status = await response.json();
            
            this.updateProgressDisplay(status);
            
            if (status.status === 'completed') {
                this.showResult();
                this.stopProgressMonitoring();
            } else if (status.status === 'error') {
                this.showError(status.error || 'Error desconocido');
                this.stopProgressMonitoring();
            }
            
        } catch (error) {
            console.error('Progress check error:', error);
        }
    }
    
    updateProgressDisplay(status) {
        const progressBar = document.getElementById('progressBar');
        const progressMessage = document.getElementById('progressMessage');
        
        if (progressBar) {
            SyncDub.updateProgress(progressBar, status.progress || 0);
        }
        
        if (progressMessage) {
            progressMessage.textContent = status.message || 'Procesando...';
        }
    }
    
    showResult() {
        document.getElementById('progressSection').classList.add('d-none');
        document.getElementById('resultSection').classList.remove('d-none');
        
        const downloadBtn = document.getElementById('downloadBtn');
        const customNameBadge = document.getElementById('customNameBadge');
        const customFilename = document.getElementById('customFilename').value.trim();
        
        if (downloadBtn) {
            downloadBtn.href = `/api/download/${this.currentTaskId}`;
        }
        
        if (customNameBadge && customFilename) {
            customNameBadge.textContent = `Archivo: ${customFilename}.mkv`;
            customNameBadge.style.display = 'inline';
        } else if (customNameBadge) {
            customNameBadge.style.display = 'none';
        }
        
        SyncDub.showToast('¡Sincronización completada exitosamente!', 'success');
    }
    
    showError(error) {
        document.getElementById('progressSection').classList.add('d-none');
        document.getElementById('errorSection').classList.remove('d-none');
        
        const errorMessage = document.getElementById('errorMessage');
        if (errorMessage) {
            errorMessage.textContent = error;
        }
    }
    
    stopProgressMonitoring() {
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
            this.progressInterval = null;
        }
    }
}

// Initialize upload manager when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    new UploadManager();
});

// Clean up on page unload
window.addEventListener('beforeunload', function() {
    if (window.uploadManager && window.uploadManager.progressInterval) {
        clearInterval(window.uploadManager.progressInterval);
    }
});

