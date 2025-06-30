/**
 * SyncDub MVP - Upload functionality
 */

class SyncDubUploader {
    constructor() {
        this.currentTaskId = null;
        this.originalFile = null;
        this.dubbedFile = null;
        this.originalPath = '';
        this.dubbedPath = '';
        this.mediaAvailable = false;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.checkMediaAvailability();
        this.updateSubmitButton();
    }

    setupEventListeners() {
        // Source selection toggles
        document.querySelectorAll('input[name="original_source"]').forEach(radio => {
            radio.addEventListener('change', () => this.toggleOriginalSource());
        });
        
        document.querySelectorAll('input[name="dubbed_source"]').forEach(radio => {
            radio.addEventListener('change', () => this.toggleDubbedSource());
        });

        // File inputs
        const originalInput = document.getElementById('originalVideo');
        const dubbedInput = document.getElementById('dubbedVideo');
        
        if (originalInput) {
            originalInput.addEventListener('change', (e) => this.handleFileSelect(e, 'original'));
        }
        
        if (dubbedInput) {
            dubbedInput.addEventListener('change', (e) => this.handleFileSelect(e, 'dubbed'));
        }

        // Upload areas
        this.setupDropZone('originalUploadArea', 'originalVideo');
        this.setupDropZone('dubbedUploadArea', 'dubbedVideo');

        // Form submission
        const form = document.getElementById('uploadForm');
        if (form) {
            form.addEventListener('submit', (e) => this.handleSubmit(e));
        }

        // Navigation links
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('navigate-link')) {
                e.preventDefault();
                const path = e.target.dataset.path;
                const type = e.target.closest('.volume-area').id.includes('original') ? 'original' : 'dubbed';
                this.navigateToPath(path, type);
            }
            
            if (e.target.classList.contains('media-item') && !e.target.classList.contains('directory')) {
                const type = e.target.closest('.volume-area').id.includes('original') ? 'original' : 'dubbed';
                this.selectMediaFile(e.target, type);
            }
            
            if (e.target.classList.contains('directory')) {
                const path = e.target.dataset.path;
                const type = e.target.closest('.volume-area').id.includes('original') ? 'original' : 'dubbed';
                this.navigateToPath(path, type);
            }
        });
    }

    setupDropZone(areaId, inputId) {
        const area = document.getElementById(areaId);
        const input = document.getElementById(inputId);
        
        if (!area || !input) return;

        area.addEventListener('click', () => input.click());

        area.addEventListener('dragover', (e) => {
            e.preventDefault();
            area.classList.add('dragover');
        });

        area.addEventListener('dragleave', () => {
            area.classList.remove('dragover');
        });

        area.addEventListener('drop', (e) => {
            e.preventDefault();
            area.classList.remove('dragover');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                input.files = files;
                const event = new Event('change', { bubbles: true });
                input.dispatchEvent(event);
            }
        });
    }

    async checkMediaAvailability() {
        try {
            const response = await fetch('/api/media/status');
            const data = await response.json();
            
            this.mediaAvailable = data.accessible;
            this.updateMediaStatus(data);
            
        } catch (error) {
            console.error('Error checking media availability:', error);
            this.mediaAvailable = false;
            this.updateMediaStatus({
                accessible: false,
                message: 'Error al conectar con el servidor'
            });
        }
    }

    updateMediaStatus(data) {
        const originalStatus = document.getElementById('originalMediaStatus');
        const dubbedStatus = document.getElementById('dubbedMediaStatus');
        
        const statusHtml = data.accessible 
            ? `<i class="fas fa-check-circle text-success me-2"></i>Volumen disponible: ${data.message || 'Listo para usar'}`
            : `<i class="fas fa-exclamation-triangle text-warning me-2"></i>No hay volumen del servidor montado`;
        
        if (originalStatus) originalStatus.innerHTML = statusHtml;
        if (dubbedStatus) dubbedStatus.innerHTML = statusHtml;
        
        // Enable/disable volume radio buttons
        const volumeRadios = document.querySelectorAll('input[value="volume"]');
        volumeRadios.forEach(radio => {
            radio.disabled = !data.accessible;
            if (!data.accessible && radio.checked) {
                const uploadRadio = radio.closest('.source-selection').querySelector('input[value="upload"]');
                if (uploadRadio) uploadRadio.checked = true;
            }
        });
    }

    toggleOriginalSource() {
        const uploadSelected = document.getElementById('originalUpload').checked;
        const uploadArea = document.getElementById('originalUploadArea');
        const volumeArea = document.getElementById('originalVolumeArea');
        
        if (uploadSelected) {
            uploadArea.classList.remove('d-none');
            volumeArea.classList.add('d-none');
            this.originalPath = '';
        } else {
            uploadArea.classList.add('d-none');
            volumeArea.classList.remove('d-none');
            this.originalFile = null;
            this.loadMediaBrowser('original');
        }
        
        this.updateFileInfo('original');
        this.updateSubmitButton();
    }

    toggleDubbedSource() {
        const uploadSelected = document.getElementById('dubbedUpload').checked;
        const uploadArea = document.getElementById('dubbedUploadArea');
        const volumeArea = document.getElementById('dubbedVolumeArea');
        
        if (uploadSelected) {
            uploadArea.classList.remove('d-none');
            volumeArea.classList.add('d-none');
            this.dubbedPath = '';
        } else {
            uploadArea.classList.add('d-none');
            volumeArea.classList.remove('d-none');
            this.dubbedFile = null;
            this.loadMediaBrowser('dubbed');
        }
        
        this.updateFileInfo('dubbed');
        this.updateSubmitButton();
    }

    async loadMediaBrowser(type, path = '') {
        const browserId = `${type}MediaBrowser`;
        const breadcrumbId = `${type}Breadcrumb`;
        const browser = document.getElementById(browserId);
        const breadcrumb = document.getElementById(breadcrumbId);
        
        if (!browser) return;

        try {
            browser.innerHTML = '<div class="text-center p-3"><i class="fas fa-spinner fa-spin"></i> Cargando...</div>';
            
            const response = await fetch(`/api/media/list?path=${encodeURIComponent(path)}`);
            const data = await response.json();
            
            if (response.ok) {
                this.renderMediaBrowser(data, type);
                this.updateBreadcrumb(data.current_path, type);
                browser.classList.remove('d-none');
                if (breadcrumb) breadcrumb.classList.remove('d-none');
            } else {
                browser.innerHTML = `<div class="alert alert-warning">Error: ${data.error || 'No se pudo cargar el contenido'}</div>`;
            }
            
        } catch (error) {
            console.error('Error loading media browser:', error);
            browser.innerHTML = '<div class="alert alert-danger">Error al conectar con el servidor</div>';
        }
    }

    renderMediaBrowser(data, type) {
        const browserId = `${type}MediaBrowser`;
        const browser = document.getElementById(browserId);
        
        if (!browser) return;

        let html = '';
        
        // Parent directory link
        if (data.parent_path !== null) {
            html += `
                <div class="media-item directory" data-path="${data.parent_path}">
                    <i class="fas fa-level-up-alt me-2"></i>
                    <strong>.. (Directorio padre)</strong>
                </div>
            `;
        }
        
        // Directories
        data.directories.forEach(dir => {
            html += `
                <div class="media-item directory" data-path="${dir.path}">
                    <i class="fas fa-folder me-2 text-warning"></i>
                    <strong>${dir.name}</strong>
                </div>
            `;
        });
        
        // Videos
        data.videos.forEach(video => {
            html += `
                <div class="media-item" data-path="${video.path}" data-name="${video.name}" data-size="${video.size}">
                    <i class="fas fa-file-video me-2 text-primary"></i>
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <div class="fw-medium">${video.name}</div>
                            <small class="text-muted">${video.size_formatted}</small>
                        </div>
                        <i class="fas fa-chevron-right text-muted"></i>
                    </div>
                </div>
            `;
        });
        
        if (html === '') {
            html = '<div class="text-center text-muted p-3">No hay archivos de video en este directorio</div>';
        }
        
        browser.innerHTML = html;
    }

    updateBreadcrumb(currentPath, type) {
        const breadcrumbId = `${type}Breadcrumb`;
        const breadcrumb = document.getElementById(breadcrumbId);
        
        if (!breadcrumb) return;

        const ol = breadcrumb.querySelector('.breadcrumb');
        if (!ol) return;

        let html = `
            <li class="breadcrumb-item">
                <a href="#" data-path="" class="navigate-link">
                    <i class="fas fa-home"></i> Inicio
                </a>
            </li>
        `;
        
        if (currentPath) {
            const parts = currentPath.split('/').filter(part => part);
            let buildPath = '';
            
            parts.forEach((part, index) => {
                buildPath += (buildPath ? '/' : '') + part;
                const isLast = index === parts.length - 1;
                
                if (isLast) {
                    html += `<li class="breadcrumb-item active">${part}</li>`;
                } else {
                    html += `
                        <li class="breadcrumb-item">
                            <a href="#" data-path="${buildPath}" class="navigate-link">${part}</a>
                        </li>
                    `;
                }
            });
        }
        
        ol.innerHTML = html;
    }

    navigateToPath(path, type) {
        this.loadMediaBrowser(type, path);
    }

    selectMediaFile(element, type) {
        // Remove previous selection
        const browser = element.closest('.media-browser');
        browser.querySelectorAll('.media-item').forEach(item => {
            item.classList.remove('selected');
        });
        
        // Add selection to clicked item
        element.classList.add('selected');
        
        // Store the path
        const path = element.dataset.path;
        const name = element.dataset.name;
        const size = parseInt(element.dataset.size);
        
        if (type === 'original') {
            this.originalPath = path;
            this.originalFile = { name, size };
        } else {
            this.dubbedPath = path;
            this.dubbedFile = { name, size };
        }
        
        this.updateFileInfo(type);
        this.updateSubmitButton();
        
        SyncDub.showToast(`Archivo seleccionado: ${name}`, 'success');
    }

    handleFileSelect(event, type) {
        const file = event.target.files[0];
        
        if (!file) {
            if (type === 'original') {
                this.originalFile = null;
            } else {
                this.dubbedFile = null;
            }
            this.updateFileInfo(type);
            this.updateSubmitButton();
            return;
        }
        
        // Validate file type
        if (!SyncDub.isValidVideoFile(file.name)) {
            SyncDub.showToast('Por favor selecciona un archivo de video válido', 'error');
            event.target.value = '';
            return;
        }

        // Validate file size (8GB limit)
        if (file.size > 8 * 1024 * 1024 * 1024) {
            SyncDub.showToast('El archivo es demasiado grande. Máximo 8GB permitido', 'error');
            event.target.value = '';
            return;
        }
        
        if (type === 'original') {
            this.originalFile = file;
            this.originalPath = '';
        } else {
            this.dubbedFile = file;
            this.dubbedPath = '';
        }
        
        this.updateFileInfo(type);
        this.updateSubmitButton();
        
        SyncDub.showToast(`Archivo cargado: ${file.name}`, 'success');
    }

    updateFileInfo(type) {
        const infoId = `${type}FileInfo`;
        const areaId = `${type}UploadArea`;
        const info = document.getElementById(infoId);
        const area = document.getElementById(areaId);
        
        if (!info || !area) return;

        const file = type === 'original' ? this.originalFile : this.dubbedFile;
        const path = type === 'original' ? this.originalPath : this.dubbedPath;
        
        if (file || path) {
            const name = file ? file.name : path.split('/').pop();
            const size = file ? file.size : 0;
            
            info.querySelector('.file-name').textContent = name;
            info.querySelector('.file-size').textContent = file ? SyncDub.formatFileSize(size) : 'Archivo del servidor';
            info.classList.remove('d-none');
            area.classList.add('has-file');
        } else {
            info.classList.add('d-none');
            area.classList.remove('has-file');
        }
    }

    updateSubmitButton() {
        const submitBtn = document.getElementById('submitBtn');
        if (!submitBtn) return;

        const hasOriginal = this.originalFile || this.originalPath;
        const hasDubbed = this.dubbedFile || this.dubbedPath;
        
        submitBtn.disabled = !(hasOriginal && hasDubbed);
    }

    async handleSubmit(event) {
        event.preventDefault();
        
        const formData = new FormData();
        
        // Add custom filename
        const customFilename = document.getElementById('customFilename').value.trim();
        if (customFilename) {
            formData.append('custom_filename', customFilename);
        }
        
        // Add original source
        const originalSource = document.querySelector('input[name="original_source"]:checked').value;
        formData.append('original_source', originalSource);
        
        if (originalSource === 'upload' && this.originalFile) {
            formData.append('original_video', this.originalFile);
        } else if (originalSource === 'volume' && this.originalPath) {
            formData.append('original_path', this.originalPath);
        }
        
        // Add dubbed source
        const dubbedSource = document.querySelector('input[name="dubbed_source"]:checked').value;
        formData.append('dubbed_source', dubbedSource);
        
        if (dubbedSource === 'upload' && this.dubbedFile) {
            formData.append('dubbed_video', this.dubbedFile);
        } else if (dubbedSource === 'volume' && this.dubbedPath) {
            formData.append('dubbed_path', this.dubbedPath);
        }
        
        try {
            this.showProgress();
            
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (response.ok) {
                this.currentTaskId = data.task_id;
                this.monitorProgress();
            } else {
                throw new Error(data.error || 'Error en la subida');
            }
            
        } catch (error) {
            console.error('Upload error:', error);
            this.showError(error.message);
        }
    }

    showProgress() {
        document.getElementById('uploadForm').classList.add('d-none');
        document.getElementById('progressSection').classList.remove('d-none');
        document.getElementById('resultSection').classList.add('d-none');
        document.getElementById('errorSection').classList.add('d-none');
    }

    async monitorProgress() {
        if (!this.currentTaskId) return;
        
        try {
            const response = await fetch(`/api/status/${this.currentTaskId}`);
            const data = await response.json();
            
            if (response.ok) {
                this.updateProgress(data.progress, data.message);
                
                if (data.status === 'completed') {
                    this.showResult();
                } else if (data.status === 'error') {
                    this.showError(data.message);
                } else {
                    // Continue monitoring
                    setTimeout(() => this.monitorProgress(), 2000);
                }
            } else {
                throw new Error(data.error || 'Error al obtener estado');
            }
            
        } catch (error) {
            console.error('Progress monitoring error:', error);
            this.showError('Error al monitorear el progreso');
        }
    }

    updateProgress(progress, message) {
        const progressBar = document.getElementById('progressBar');
        const progressMessage = document.getElementById('progressMessage');
        
        if (progressBar) {
            progressBar.style.width = `${progress}%`;
            progressBar.setAttribute('aria-valuenow', progress);
        }
        
        if (progressMessage) {
            progressMessage.textContent = message;
        }
    }

    showResult() {
        document.getElementById('progressSection').classList.add('d-none');
        document.getElementById('resultSection').classList.remove('d-none');
        
        const downloadBtn = document.getElementById('downloadBtn');
        if (downloadBtn) {
            downloadBtn.onclick = () => this.downloadResult();
        }
    }

    showError(message) {
        document.getElementById('progressSection').classList.add('d-none');
        document.getElementById('errorSection').classList.remove('d-none');
        document.getElementById('errorMessage').textContent = message;
    }

    async downloadResult() {
        if (!this.currentTaskId) return;
        
        try {
            const response = await fetch(`/api/download/${this.currentTaskId}`);
            
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `synced_${this.currentTaskId}.mkv`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                
                SyncDub.showToast('Descarga iniciada', 'success');
            } else {
                throw new Error('Error al descargar el archivo');
            }
            
        } catch (error) {
            console.error('Download error:', error);
            SyncDub.showToast('Error al descargar el archivo', 'error');
        }
    }
}

// Initialize uploader when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new SyncDubUploader();
});

