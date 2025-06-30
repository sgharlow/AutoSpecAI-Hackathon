/**
 * AutoSpec.AI Web Application
 * Main JavaScript application for document processing interface
 */

class AutoSpecApp {
    constructor() {
        this.config = window.autoSpecConfig || {};
        this.apiConfig = this.config.API_CONFIG || {};
        this.endpoints = this.config.ENDPOINTS || {};
        this.appConfig = this.config.APP_CONFIG || {};
        
        this.init();
    }

    init() {
        this.bindEvents();
        this.setupFileUpload();
        console.log('AutoSpec.AI Web App initialized');
    }

    bindEvents() {
        // File upload events
        document.getElementById('browse-btn')?.addEventListener('click', () => {
            document.getElementById('file-input').click();
        });

        document.getElementById('file-input')?.addEventListener('change', (e) => {
            this.handleFileSelect(e.target.files);
        });

        // Status check event
        document.getElementById('check-status-btn')?.addEventListener('click', () => {
            this.checkStatus();
        });

        // History refresh event
        document.getElementById('refresh-history-btn')?.addEventListener('click', () => {
            this.loadHistory();
        });

        // Health check event
        document.getElementById('health-check-btn')?.addEventListener('click', () => {
            this.checkHealth();
        });

        // Drag and drop events
        const uploadZone = document.getElementById('upload-zone');
        if (uploadZone) {
            uploadZone.addEventListener('dragover', (e) => {
                e.preventDefault();
                uploadZone.classList.add('border-success');
            });

            uploadZone.addEventListener('dragleave', () => {
                uploadZone.classList.remove('border-success');
            });

            uploadZone.addEventListener('drop', (e) => {
                e.preventDefault();
                uploadZone.classList.remove('border-success');
                this.handleFileSelect(e.dataTransfer.files);
            });
        }
    }

    setupFileUpload() {
        // Configure file input
        const fileInput = document.getElementById('file-input');
        if (fileInput) {
            fileInput.setAttribute('accept', '.pdf,.docx,.txt');
        }
    }

    async makeApiRequest(endpoint, options = {}) {
        const url = this.config.buildApiUrl(endpoint);
        const headers = this.config.getDefaultHeaders();
        
        const defaultOptions = {
            method: 'GET',
            headers,
            timeout: this.apiConfig.TIMEOUT || 30000
        };

        const finalOptions = { ...defaultOptions, ...options };
        
        try {
            const response = await fetch(url, finalOptions);
            
            if (!response.ok) {
                throw new Error(`API request failed: ${response.status} ${response.statusText}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('API request error:', error);
            throw error;
        }
    }

    async handleFileSelect(files) {
        if (!files || files.length === 0) return;
        
        const file = files[0];
        
        // Validate file
        if (!this.validateFile(file)) return;
        
        // Show progress
        this.showUploadProgress();
        
        try {
            const result = await this.uploadFile(file);
            this.showUploadResult(result, 'success');
        } catch (error) {
            this.showUploadResult(error.message, 'error');
        } finally {
            this.hideUploadProgress();
        }
    }

    validateFile(file) {
        const maxSize = this.appConfig.MAX_FILE_SIZE || 10 * 1024 * 1024; // 10MB
        const allowedTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain'];
        
        if (file.size > maxSize) {
            this.showUploadResult('File size exceeds 10MB limit', 'error');
            return false;
        }
        
        if (!allowedTypes.includes(file.type) && !file.name.match(/\.(pdf|docx|txt)$/i)) {
            this.showUploadResult('Invalid file type. Please use PDF, DOCX, or TXT files.', 'error');
            return false;
        }
        
        return true;
    }

    async uploadFile(file) {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch(this.config.buildApiUrl(this.endpoints.UPLOAD), {
            method: 'POST',
            headers: {
                'X-API-Key': this.apiConfig.DEFAULT_API_KEY
            },
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`Upload failed: ${response.status} ${response.statusText}`);
        }
        
        return await response.json();
    }

    async checkStatus() {
        const requestId = document.getElementById('request-id')?.value?.trim();
        
        if (!requestId) {
            this.showStatusResult('Please enter a request ID', 'error');
            return;
        }
        
        try {
            const result = await this.makeApiRequest(`${this.endpoints.STATUS}/${requestId}`);
            this.showStatusResult(result, 'success');
        } catch (error) {
            this.showStatusResult(error.message, 'error');
        }
    }

    async loadHistory() {
        try {
            const result = await this.makeApiRequest(this.endpoints.HISTORY);
            this.showHistoryResult(result);
        } catch (error) {
            this.showHistoryResult(error.message, 'error');
        }
    }

    async checkHealth() {
        try {
            const result = await this.makeApiRequest(this.endpoints.HEALTH);
            this.showHealthResult(result, 'success');
        } catch (error) {
            this.showHealthResult(error.message, 'error');
        }
    }

    showUploadProgress() {
        const progressDiv = document.getElementById('upload-progress');
        if (progressDiv) {
            progressDiv.classList.remove('d-none');
            const progressBar = progressDiv.querySelector('.progress-bar');
            if (progressBar) {
                progressBar.style.width = '100%';
            }
        }
    }

    hideUploadProgress() {
        const progressDiv = document.getElementById('upload-progress');
        if (progressDiv) {
            progressDiv.classList.add('d-none');
        }
    }

    showUploadResult(result, type) {
        const resultDiv = document.getElementById('upload-result');
        if (!resultDiv) return;
        
        let html = '';
        
        if (type === 'success') {
            html = `
                <div class="alert alert-success">
                    <h5><i class="fas fa-check-circle me-2"></i>Upload Successful!</h5>
                    <p><strong>Request ID:</strong> ${result.requestId || result.request_id || 'N/A'}</p>
                    <p><strong>Status:</strong> ${result.status || 'Processing'}</p>
                    ${result.message ? `<p><strong>Message:</strong> ${result.message}</p>` : ''}
                </div>
            `;
        } else {
            html = `
                <div class="alert alert-danger">
                    <h5><i class="fas fa-exclamation-triangle me-2"></i>Upload Failed</h5>
                    <p>${result}</p>
                </div>
            `;
        }
        
        resultDiv.innerHTML = html;
    }

    showStatusResult(result, type) {
        const resultDiv = document.getElementById('status-result');
        if (!resultDiv) return;
        
        let html = '';
        
        if (type === 'success') {
            html = `
                <div class="card">
                    <div class="card-body">
                        <h5 class="card-title">Status Information</h5>
                        <div class="row">
                            <div class="col-md-6">
                                <p><strong>Status:</strong> <span class="badge bg-${this.getStatusBadgeClass(result.status)}">${result.status}</span></p>
                                <p><strong>Created:</strong> ${result.created_at || 'N/A'}</p>
                                <p><strong>Updated:</strong> ${result.updated_at || 'N/A'}</p>
                            </div>
                            <div class="col-md-6">
                                <p><strong>File Name:</strong> ${result.file_name || 'N/A'}</p>
                                <p><strong>File Size:</strong> ${result.file_size || 'N/A'}</p>
                                <p><strong>Processing Stage:</strong> ${result.processing_stage || 'N/A'}</p>
                            </div>
                        </div>
                        ${result.result_url ? `<a href="${result.result_url}" class="btn btn-primary" target="_blank"><i class="fas fa-download me-2"></i>Download Result</a>` : ''}
                    </div>
                </div>
            `;
        } else {
            html = `
                <div class="alert alert-warning">
                    <p><i class="fas fa-exclamation-triangle me-2"></i>${result}</p>
                </div>
            `;
        }
        
        resultDiv.innerHTML = html;
    }

    showHistoryResult(result, type = 'success') {
        const resultDiv = document.getElementById('history-result');
        if (!resultDiv) return;
        
        if (type === 'error') {
            resultDiv.innerHTML = `
                <div class="alert alert-danger">
                    <p><i class="fas fa-exclamation-triangle me-2"></i>${result}</p>
                </div>
            `;
            return;
        }
        
        if (!result.items || result.items.length === 0) {
            resultDiv.innerHTML = `
                <div class="text-center py-4">
                    <i class="fas fa-inbox fa-2x text-muted mb-3"></i>
                    <p class="text-muted">No processing history found</p>
                </div>
            `;
            return;
        }
        
        let html = '<div class="table-responsive"><table class="table table-striped"><thead><tr>';
        html += '<th>Request ID</th><th>File Name</th><th>Status</th><th>Created</th><th>Actions</th>';
        html += '</tr></thead><tbody>';
        
        result.items.forEach(item => {
            html += `
                <tr>
                    <td><code class="small">${item.request_id || item.requestId}</code></td>
                    <td>${item.file_name || item.fileName || 'N/A'}</td>
                    <td><span class="badge bg-${this.getStatusBadgeClass(item.status)}">${item.status}</span></td>
                    <td>${new Date(item.created_at || item.createdAt).toLocaleDateString()}</td>
                    <td>
                        <button class="btn btn-sm btn-outline-info" onclick="app.viewDetails('${item.request_id || item.requestId}')">
                            <i class="fas fa-eye"></i>
                        </button>
                        ${item.result_url ? `<a href="${item.result_url}" class="btn btn-sm btn-outline-success ms-1" target="_blank"><i class="fas fa-download"></i></a>` : ''}
                    </td>
                </tr>
            `;
        });
        
        html += '</tbody></table></div>';
        resultDiv.innerHTML = html;
    }

    showHealthResult(result, type) {
        const resultDiv = document.getElementById('health-result');
        if (!resultDiv) return;
        
        let html = '';
        
        if (type === 'success') {
            const isHealthy = result.status === 'healthy' || result.health === 'OK';
            html = `
                <div class="alert alert-${isHealthy ? 'success' : 'warning'}">
                    <h6><i class="fas fa-${isHealthy ? 'check-circle' : 'exclamation-triangle'} me-2"></i>System Status</h6>
                    <p><strong>Status:</strong> ${result.status || result.health || 'Unknown'}</p>
                    <p><strong>Timestamp:</strong> ${result.timestamp || new Date().toISOString()}</p>
                    ${result.version ? `<p><strong>Version:</strong> ${result.version}</p>` : ''}
                </div>
            `;
        } else {
            html = `
                <div class="alert alert-danger">
                    <p><i class="fas fa-times-circle me-2"></i>Health check failed: ${result}</p>
                </div>
            `;
        }
        
        resultDiv.innerHTML = html;
    }

    getStatusBadgeClass(status) {
        switch (status?.toLowerCase()) {
            case 'completed':
            case 'success':
                return 'success';
            case 'processing':
            case 'in_progress':
                return 'info';
            case 'failed':
            case 'error':
                return 'danger';
            case 'pending':
            case 'queued':
                return 'warning';
            default:
                return 'secondary';
        }
    }

    viewDetails(requestId) {
        document.getElementById('request-id').value = requestId;
        this.checkStatus();
        document.getElementById('status').scrollIntoView({ behavior: 'smooth' });
    }
}

// Initialize the application when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new AutoSpecApp();
});