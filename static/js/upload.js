/**
 * SyncDub MVP - JavaScript CORREGIDO
 * URLs corregidas para coincidir con la API actual
 */

class SyncDubUploader {
    constructor() {
        this.currentPath = '';
        this.selectedOriginal = null;
        this.selectedDubbed = null;
        this.nfsEnabled = false;
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.checkNFSStatus();
        // Mostrar modo NFS por defecto al cargar
        this.switchMode('server');
    }

    setupEventListeners() {
        // Selector de modo
        document.querySelectorAll('input[name="uploadMode"]').forEach(radio => {
            radio.addEventListener('change', (e) => {
                this.switchMode(e.target.value);
            });
        });

        // Botones de navegación
        document.getElementById('btnBack')?.addEventListener('click', () => {
            this.navigateUp();
        });

        document.getElementById('btnRefresh')?.addEventListener('click', () => {
            this.loadDirectory(this.currentPath);
        });

        // Botón de procesamiento del servidor
        document.getElementById('btnProcessServer')?.addEventListener('click', () => {
            this.processServerFiles();
        });

        // Form de upload local
        document.getElementById('uploadForm')?.addEventListener('submit', (e) => {
            e.preventDefault();
            const params = new URLSearchParams(window.location.search);
            const mode = params.get('mode') || 'sync';
            this.processUnifiedUpload(mode);
        });
    }

    switchMode(mode) {
        const localMode = document.getElementById('localMode');
        const serverMode = document.getElementById('serverMode');

        if (mode === 'local') {
            localMode.style.display = 'block';
            serverMode.style.display = 'none';
        } else {
            localMode.style.display = 'none';
            serverMode.style.display = 'block';
            if (this.nfsEnabled) {
                this.loadDirectory('');
            }
        }
    }

    async checkNFSStatus() {
        try {
            console.log('🔍 Verificando estado NFS...');
            // ✅ URL CORREGIDA: /api/nfs-config (con prefijo /api)
            const response = await fetch('/api/nfs-config');
            
            if (response.ok) {
                const data = await response.json();
                console.log('✅ Respuesta NFS:', data);
                
                this.nfsEnabled = data.enabled && data.accessible;
                this.updateNFSStatus(data);
            } else {
                console.error('❌ Error en /api/nfs-config:', response.status);
                this.showNFSError(`Error del servidor: ${response.status}`);
            }
        } catch (error) {
            console.error('❌ Error verificando NFS:', error);
            this.showNFSError(`Error de conexión: ${error.message}`);
        }
    }

    updateNFSStatus(data) {
        const statusBadge = document.getElementById('nfsStatus');
        const serverInfo = document.getElementById('serverInfo');
        const navigationArea = document.getElementById('navigationArea');
        const selectionArea = document.getElementById('selectionArea');

        if (this.nfsEnabled) {
            statusBadge.textContent = 'Disponible';
            statusBadge.className = 'badge bg-success ms-2';
            
            document.getElementById('serverPath').textContent = data.path;
            document.getElementById('serverVideos').textContent = data.total_videos || 'Calculando...';
            
            serverInfo.style.display = 'block';
            navigationArea.style.display = 'block';
            selectionArea.style.display = 'block';
        } else {
            statusBadge.textContent = 'No disponible';
            statusBadge.className = 'badge bg-danger ms-2';
            this.showNFSError(data.error || 'Servidor NFS no accesible');
        }
    }

    showNFSError(message) {
        const errorDiv = document.getElementById('serverError');
        const errorMessage = document.getElementById('serverErrorMessage');
        
        errorMessage.textContent = message;
        errorDiv.style.display = 'block';
        
        document.getElementById('navigationArea').style.display = 'none';
        document.getElementById('selectionArea').style.display = 'none';
    }

    async loadDirectory(path = '') {
        try {
            console.log(`🔍 Cargando directorio: "${path}"`);
            
            const fileList = document.getElementById('fileList');
            fileList.innerHTML = `
                <div class="text-center">
                    <div class="spinner-border" role="status">
                        <span class="visually-hidden">Cargando...</span>
                    </div>
                    <p class="mt-2">Cargando archivos...</p>
                </div>
            `;

            // ✅ URL CORREGIDA: /api/nfs-browse (con prefijo /api)
            const url = `/api/nfs-browse${path ? `?path=${encodeURIComponent(path)}` : ''}`;
            const response = await fetch(url);

            if (response.ok) {
                const data = await response.json();
                console.log('✅ Directorio cargado:', data);
                
                this.currentPath = data.current_path;
                this.updateBreadcrumb(data.breadcrumb);
                this.renderFileList(data.items);
                this.updateBackButton();
            } else {
                console.error('❌ Error cargando directorio:', response.status);
                fileList.innerHTML = `
                    <div class="alert alert-danger">
                        Error cargando directorio: ${response.status}
                    </div>
                `;
            }
        } catch (error) {
            console.error('❌ Error en loadDirectory:', error);
            document.getElementById('fileList').innerHTML = `
                <div class="alert alert-danger">
                    Error de conexión: ${error.message}
                </div>
            `;
        }
    }

    updateBreadcrumb(breadcrumb) {
        const breadcrumbEl = document.getElementById('breadcrumb');
        breadcrumbEl.innerHTML = '';

        breadcrumb.forEach((item, index) => {
            const li = document.createElement('li');
            li.className = 'breadcrumb-item';
            
            if (index === breadcrumb.length - 1) {
                li.className += ' active';
                li.textContent = item.name;
            } else {
                const a = document.createElement('a');
                a.href = '#';
                a.textContent = item.name;
                a.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.loadDirectory(item.path);
                });
                li.appendChild(a);
            }
            
            breadcrumbEl.appendChild(li);
        });
    }

    updateBackButton() {
        const btnBack = document.getElementById('btnBack');
        btnBack.disabled = this.currentPath === '';
    }

    renderFileList(items) {
        const fileList = document.getElementById('fileList');
        
        if (items.length === 0) {
            fileList.innerHTML = `
                <div class="text-center text-muted">
                    <i class="fas fa-folder-open fa-3x mb-3"></i>
                    <p>No hay archivos en este directorio</p>
                </div>
            `;
            return;
        }

        const html = items.map(item => {
            const icon = item.is_directory ? 'fas fa-folder' : 'fas fa-film';
            const iconColor = item.is_directory ? 'text-warning' : 'text-primary';
            
            let info = '';
            if (item.is_directory) {
                info = `${item.total_items || 0} elementos`;
                if (item.videos > 0) {
                    info += `, ${item.videos} videos`;
                }
            } else {
                info = item.size_formatted || '';
            }

            return `
                <div class="file-item d-flex align-items-center p-2 border-bottom" 
                     data-path="${item.path}" 
                     data-is-directory="${item.is_directory}"
                     data-is-video="${item.is_video}">
                    <i class="${icon} ${iconColor} me-3"></i>
                    <div class="flex-grow-1">
                        <div class="fw-bold">${item.name}</div>
                        <small class="text-muted">${info}</small>
                    </div>
                    <div class="file-actions">
                        ${item.is_directory ? 
                            '<button class="btn btn-sm btn-outline-primary btn-enter">Entrar</button>' :
                            item.is_video ? 
                                '<button class="btn btn-sm btn-primary btn-select-original me-1">Original</button><button class="btn btn-sm btn-success btn-select-dubbed">Doblado</button>' :
                                ''
                        }
                    </div>
                </div>
            `;
        }).join('');

        fileList.innerHTML = html;

        // Agregar event listeners
        fileList.querySelectorAll('.btn-enter').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const item = e.target.closest('.file-item');
                const path = item.dataset.path;
                this.loadDirectory(path);
            });
        });

        fileList.querySelectorAll('.btn-select-original').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const item = e.target.closest('.file-item');
                this.selectFile('original', item);
            });
        });

        fileList.querySelectorAll('.btn-select-dubbed').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const item = e.target.closest('.file-item');
                this.selectFile('dubbed', item);
            });
        });

        // Doble clic para entrar en directorios
        fileList.querySelectorAll('.file-item[data-is-directory="true"]').forEach(item => {
            item.addEventListener('dblclick', () => {
                const path = item.dataset.path;
                this.loadDirectory(path);
            });
        });
    }

    selectFile(type, itemElement) {
        const path = itemElement.dataset.path;
        const name = itemElement.querySelector('.fw-bold').textContent;

        if (type === 'original') {
            this.selectedOriginal = { path, name };
            document.getElementById('selectedOriginal').innerHTML = `
                <i class="fas fa-film text-primary"></i> ${name}
                <button class="btn btn-sm btn-outline-danger ms-2" onclick="syncDubUploader.clearSelection('original')">
                    <i class="fas fa-times"></i>
                </button>
            `;
        } else {
            this.selectedDubbed = { path, name };
            document.getElementById('selectedDubbed').innerHTML = `
                <i class="fas fa-film text-success"></i> ${name}
                <button class="btn btn-sm btn-outline-danger ms-2" onclick="syncDubUploader.clearSelection('dubbed')">
                    <i class="fas fa-times"></i>
                </button>
            `;
        }

        this.updateProcessButton();
        this.showToast(`Archivo seleccionado como ${type}: ${name}`, 'success');
    }

    clearSelection(type) {
        if (type === 'original') {
            this.selectedOriginal = null;
            document.getElementById('selectedOriginal').innerHTML = `
                <i class="fas fa-film"></i> Ningún archivo seleccionado
            `;
        } else {
            this.selectedDubbed = null;
            document.getElementById('selectedDubbed').innerHTML = `
                <i class="fas fa-film"></i> Ningún archivo seleccionado
            `;
        }

        this.updateProcessButton();
    }

    updateProcessButton() {
        const btnProcess = document.getElementById('btnProcessServer');
        btnProcess.disabled = !this.selectedOriginal || !this.selectedDubbed;
    }

    navigateUp() {
        if (this.currentPath === '') return;
        
        const pathParts = this.currentPath.split('/');
        pathParts.pop();
        const parentPath = pathParts.join('/');
        
        this.loadDirectory(parentPath);
    }

    async processServerFiles() {
        if (!this.selectedOriginal || !this.selectedDubbed) {
            this.showToast('Selecciona ambos archivos (original y doblado)', 'error');
            return;
        }

        const outputName = document.getElementById('serverOutputName').value.trim();

        try {
            this.showProgress('Iniciando procesamiento desde servidor...');

            // ✅ CORREGIDO: Usar /api/nfs-upload en lugar de /api/upload
            const response = await fetch('/api/nfs-upload', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    original_path: this.selectedOriginal.path,
                    dubbed_path: this.selectedDubbed.path,
                    custom_name: outputName
                })
            });

            if (response.ok) {
                const data = await response.json();
                this.monitorTask(data.task_id);
            } else {
                const error = await response.json();
                this.showError(`Error del servidor: ${error.error || response.status}`);
            }
        } catch (error) {
            this.showError(`Error de conexión: ${error.message}`);
        }
    }

    async processLocalFiles() {
        const form = document.getElementById('uploadForm');
        const formData = new FormData(form);

        try {
            this.showProgress('Subiendo archivos...');

            // ✅ Para archivos locales, usar /api/upload (endpoint original)
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                const data = await response.json();
                this.monitorTask(data.task_id);
            } else {
                const error = await response.json();
                this.showError(`Error del servidor: ${error.error || response.status}`);
            }
        } catch (error) {
            this.showError(`Error de conexión: ${error.message}`);
        }
    }

    async processH265File() {
        const form = document.getElementById('uploadForm');
        const formData = new FormData(form);
        try {
            this.showProgress('Subiendo archivo para conversión a H265...');
            // Endpoint placeholder para conversión H265
            const response = await fetch('/api/convert-h265', {
                method: 'POST',
                body: formData
            });
            if (response.ok) {
                const data = await response.json();
                this.monitorTask(data.task_id); // Reutiliza monitorTask
            } else {
                const error = await response.json();
                this.showError(`Error del servidor: ${error.error || response.status}`);
            }
        } catch (error) {
            this.showError(`Error de conexión: ${error.message}`);
        }
    }

    async processUnifiedUpload(mode) {
        const form = document.getElementById('uploadForm');
        const formData = new FormData();
        // Solo incluir los campos visibles/activos según el modo
        const originalInput = document.getElementById('originalVideo');
        const dubbedInput = document.getElementById('dubbedVideo');
        const outputNameInput = document.getElementById('outputName');
        if (originalInput && originalInput.files.length > 0) {
            formData.append('original_video', originalInput.files[0]);
        }
        if (mode !== 'convert' && dubbedInput && dubbedInput.files.length > 0) {
            formData.append('dubbed_video', dubbedInput.files[0]);
        }
        if (outputNameInput && outputNameInput.value.trim() !== '') {
            formData.append('output_name', outputNameInput.value.trim());
        }
        try {
            this.showProgress('Subiendo archivo(s)...');
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });
            if (response.ok) {
                const data = await response.json();
                this.monitorTask(data.task_id);
            } else {
                const error = await response.json();
                this.showError(`Error del servidor: ${error.error || response.status}`);
            }
        } catch (error) {
            this.showError(`Error de conexión: ${error.message}`);
        }
    }

    async monitorTask(taskId) {
        const checkStatus = async () => {
            try {
                const response = await fetch(`/api/status/${taskId}`);
                const data = await response.json();

                if (data.status === 'completed') {
                    this.showResult(`/api/download/${taskId}`);
                } else if (data.status === 'failed') {
                    this.showError(data.error || 'Error en el procesamiento');
                } else {
                    this.updateProgress(data.progress || 0, data.message || 'Procesando...');
                    setTimeout(checkStatus, 2000);
                }
            } catch (error) {
                this.showError(`Error monitoreando tarea: ${error.message}`);
            }
        };

        checkStatus();
    }

    showProgress(message) {
        document.getElementById('progressArea').style.display = 'block';
        document.getElementById('resultArea').style.display = 'none';
        this.updateProgress(0, message);
    }

    updateProgress(percent, message) {
        const progressBar = document.getElementById('progressBar');
        const progressText = document.getElementById('progressText');
        
        progressBar.style.width = `${percent}%`;
        progressText.textContent = message;
    }

    showResult(downloadUrl) {
        document.getElementById('progressArea').style.display = 'none';
        document.getElementById('resultArea').style.display = 'block';
        document.getElementById('downloadLink').href = downloadUrl;
        
        this.showToast('¡Procesamiento completado!', 'success');
    }

    showError(message) {
        document.getElementById('progressArea').style.display = 'none';
        this.showToast(message, 'error');
    }

    showToast(message, type = 'info') {
        // Crear toast simple
        const toast = document.createElement('div');
        toast.className = `alert alert-${type === 'error' ? 'danger' : type === 'success' ? 'success' : 'info'} position-fixed`;
        toast.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        toast.innerHTML = `
            ${message}
            <button type="button" class="btn-close" onclick="this.parentElement.remove()"></button>
        `;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            if (toast.parentElement) {
                toast.remove();
            }
        }, 5000);
    }
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    window.syncDubUploader = new SyncDubUploader();
});

