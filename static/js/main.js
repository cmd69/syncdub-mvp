/**
 * SyncDub MVP - Main JavaScript functionality
 */

// Global utilities
window.SyncDub = {
    // Show toast notification
    showToast: function(message, type = 'info', title = 'Notificación') {
        const toast = document.getElementById('notification-toast');
        const toastIcon = document.getElementById('toast-icon');
        const toastTitle = document.getElementById('toast-title');
        const toastBody = document.getElementById('toast-body');
        
        // Set icon and colors based on type
        const iconMap = {
            'success': 'fas fa-check-circle text-success',
            'error': 'fas fa-exclamation-circle text-danger',
            'warning': 'fas fa-exclamation-triangle text-warning',
            'info': 'fas fa-info-circle text-primary'
        };
        
        toastIcon.className = iconMap[type] || iconMap['info'];
        toastTitle.textContent = title;
        toastBody.textContent = message;
        
        // Show toast
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
    },
    
    // Format file size
    formatFileSize: function(bytes) {
        if (bytes === 0) return '0 B';
        
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    },
    
    // Validate video file
    isValidVideoFile: function(filename) {
        const validExtensions = ['mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv', 'webm'];
        const extension = filename.split('.').pop().toLowerCase();
        return validExtensions.includes(extension);
    },
    
    // API request helper
    apiRequest: async function(url, options = {}) {
        try {
            const response = await fetch(url, {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    }
};

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', function() {
    console.log('SyncDub MVP initialized');
    
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
});

