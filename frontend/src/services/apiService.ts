/**
 * API Service for AutoSpecAI Frontend
 * Handles all API communication with the production backend
 */

import { API_CONFIG, API_ENDPOINTS, buildApiUrl, getDefaultHeaders } from '../config/api';

// Types
export interface UploadRequest {
  file_content: string; // base64 encoded
  filename: string;
  sender_email?: string;
  preferences?: {
    quality?: 'standard' | 'high' | 'premium';
    formats?: string[];
  };
}

export interface S3UploadInitiateRequest {
  filename: string;
  file_size: number;
  content_type: string;
  metadata?: {
    sender_email?: string;
    preferences?: {
      quality?: 'standard' | 'high' | 'premium';
      formats?: string[];
    };
  };
}

export interface S3UploadInitiateResponse {
  request_id: string;
  upload_url: string;
  upload_method: string;
  upload_headers: Record<string, string>;
  expires_in: number;
  max_file_size: number;
  instructions: {
    method: string;
    url: string;
    headers: Record<string, string>;
    note: string;
  };
  next_step: string;
}

export interface S3UploadCompleteRequest {
  request_id: string;
}

export interface S3UploadCompleteResponse {
  request_id: string;
  status: string;
  message: string;
  filename: string;
  declared_size: number;
  actual_size: number;
  size_match: boolean;
  estimated_processing_time: string;
}

export interface UploadResponse {
  request_id: string;
  status: string;
  message: string;
  filename: string;
  estimated_processing_time: string;
}

export interface StatusResponse {
  request_id: string;
  filename?: string;
  status: string;
  processing_stage: string;
  created_at: string;
  updated_at?: string;
  file_type: string;
  file_size: number;
  progress_percentage: number;
  error_message?: string;
  download_links?: any;
}

export interface HistoryResponse {
  requests: Array<{
    request_id: string;
    filename: string;
    status: string;
    created_at: string;
    file_type: string;
    file_size: number;
  }>;
  count: number;
  total_count: number;
  next_token?: string;
}

export interface HealthResponse {
  status: string;
  timestamp: string;
  version: string;
  services: {
    api_gateway: string;
    lambda: string;
    dynamodb: string;
    s3: string;
  };
}

// API Service Class
class ApiService {
  private baseURL: string;
  private defaultHeaders: Record<string, string>;

  constructor() {
    this.baseURL = API_CONFIG.BASE_URL;
    this.defaultHeaders = getDefaultHeaders();
  }

  // Generic request method
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = buildApiUrl(endpoint);
    
    const config: RequestInit = {
      ...options,
      headers: {
        ...this.defaultHeaders,
        ...options.headers,
      },
      timeout: API_CONFIG.TIMEOUT,
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          errorData.error?.message || 
          `HTTP ${response.status}: ${response.statusText}`
        );
      }

      return await response.json();
    } catch (error) {
      console.error('API Request failed:', error);
      throw error;
    }
  }

  // Health check
  async checkHealth(): Promise<HealthResponse> {
    return this.request<HealthResponse>(API_ENDPOINTS.HEALTH);
  }

  // Upload document (legacy JSON method)
  async uploadDocument(data: UploadRequest): Promise<UploadResponse> {
    return this.request<UploadResponse>(API_ENDPOINTS.UPLOAD, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Initiate S3 direct upload
  async initiateS3Upload(data: S3UploadInitiateRequest): Promise<S3UploadInitiateResponse> {
    return this.request<S3UploadInitiateResponse>(API_ENDPOINTS.UPLOAD_INITIATE, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Upload file directly to S3 using pre-signed URL
  async uploadToS3(uploadUrl: string, file: File, contentType: string): Promise<void> {
    const response = await fetch(uploadUrl, {
      method: 'PUT',
      body: file,
      headers: {
        'Content-Type': contentType,
        'Content-Length': file.size.toString(),
      },
    });

    if (!response.ok) {
      throw new Error(`S3 upload failed: ${response.status} ${response.statusText}`);
    }
  }

  // Complete S3 upload and trigger processing
  async completeS3Upload(data: S3UploadCompleteRequest): Promise<S3UploadCompleteResponse> {
    return this.request<S3UploadCompleteResponse>(API_ENDPOINTS.UPLOAD_COMPLETE, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Get processing status
  async getStatus(requestId: string): Promise<StatusResponse> {
    return this.request<StatusResponse>(`${API_ENDPOINTS.STATUS}/${requestId}`);
  }

  // Get request history
  async getHistory(limit: number = 10, nextToken?: string): Promise<HistoryResponse> {
    const params = new URLSearchParams({
      limit: limit.toString(),
      ...(nextToken && { next_token: nextToken }),
    });

    return this.request<HistoryResponse>(
      `${API_ENDPOINTS.HISTORY}?${params.toString()}`
    );
  }

  // Get supported formats
  async getFormats(): Promise<any> {
    return this.request<any>(API_ENDPOINTS.FORMATS);
  }

  // Get API documentation
  async getDocs(): Promise<any> {
    return this.request<any>(API_ENDPOINTS.DOCS);
  }

  // Enhanced file upload helper with automatic method selection
  async uploadFile(
    file: File, 
    userEmail?: string,
    onProgress?: (progress: { stage: string; percentage: number }) => void
  ): Promise<UploadResponse | S3UploadCompleteResponse> {
    const LARGE_FILE_THRESHOLD = 5 * 1024 * 1024; // 5MB
    const MAX_JSON_SIZE = 8 * 1024 * 1024; // 8MB
    
    // Determine upload method based on file size
    const useS3Upload = file.size > LARGE_FILE_THRESHOLD;
    
    if (onProgress) {
      onProgress({ stage: 'analyzing', percentage: 0 });
    }
    
    if (useS3Upload) {
      return this.uploadViaS3(file, userEmail, onProgress);
    } else {
      return this.uploadViaJSON(file, userEmail, onProgress);
    }
  }

  // JSON upload method (for smaller files)
  private async uploadViaJSON(
    file: File, 
    userEmail?: string,
    onProgress?: (progress: { stage: string; percentage: number }) => void
  ): Promise<UploadResponse> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      
      if (onProgress) {
        onProgress({ stage: 'encoding', percentage: 10 });
      }
      
      reader.onload = async () => {
        try {
          if (onProgress) {
            onProgress({ stage: 'uploading', percentage: 50 });
          }
          
          const base64Content = reader.result as string;
          // Remove data:xxx;base64, prefix if present
          const base64Data = base64Content.split(',')[1] || base64Content;
          
          const uploadData: UploadRequest = {
            file_content: base64Data,
            filename: file.name,
            sender_email: userEmail,
            preferences: {
              quality: 'high',
              formats: ['html', 'json', 'markdown']
            }
          };

          const response = await this.uploadDocument(uploadData);
          
          if (onProgress) {
            onProgress({ stage: 'completed', percentage: 100 });
          }
          
          resolve(response);
        } catch (error) {
          reject(error);
        }
      };

      reader.onerror = () => {
        reject(new Error('Failed to read file'));
      };

      reader.readAsDataURL(file);
    });
  }

  // S3 direct upload method (for larger files)
  private async uploadViaS3(
    file: File,
    userEmail?: string,
    onProgress?: (progress: { stage: string; percentage: number }) => void
  ): Promise<S3UploadCompleteResponse> {
    try {
      // Step 1: Initiate upload
      if (onProgress) {
        onProgress({ stage: 'initiating', percentage: 10 });
      }
      
      const initiateData: S3UploadInitiateRequest = {
        filename: file.name,
        file_size: file.size,
        content_type: file.type || 'application/octet-stream',
        metadata: {
          sender_email: userEmail,
          preferences: {
            quality: 'high',
            formats: ['html', 'json', 'markdown']
          }
        }
      };

      const initiateResponse = await this.initiateS3Upload(initiateData);
      
      // Step 2: Upload to S3
      if (onProgress) {
        onProgress({ stage: 'uploading', percentage: 30 });
      }
      
      await this.uploadToS3(
        initiateResponse.upload_url,
        file,
        initiateResponse.upload_headers['Content-Type']
      );
      
      // Step 3: Complete upload
      if (onProgress) {
        onProgress({ stage: 'completing', percentage: 80 });
      }
      
      const completeResponse = await this.completeS3Upload({
        request_id: initiateResponse.request_id
      });
      
      if (onProgress) {
        onProgress({ stage: 'completed', percentage: 100 });
      }
      
      return completeResponse;
      
    } catch (error) {
      console.error('S3 upload failed:', error);
      throw error;
    }
  }

  // Legacy method for backward compatibility
  async uploadFileJSON(file: File, userEmail?: string): Promise<UploadResponse> {
    return this.uploadViaJSON(file, userEmail) as Promise<UploadResponse>;
  }

  // Polling helper for status updates
  async pollStatus(
    requestId: string,
    onUpdate: (status: StatusResponse) => void,
    maxAttempts: number = 60,
    interval: number = 5000
  ): Promise<StatusResponse> {
    let attempts = 0;

    return new Promise((resolve, reject) => {
      const poll = async () => {
        try {
          const status = await this.getStatus(requestId);
          onUpdate(status);

          // Check if processing is complete
          if (status.status === 'delivered' || status.status === 'failed') {
            resolve(status);
            return;
          }

          attempts++;
          if (attempts >= maxAttempts) {
            reject(new Error('Polling timeout exceeded'));
            return;
          }

          setTimeout(poll, interval);
        } catch (error) {
          reject(error);
        }
      };

      poll();
    });
  }

  // Set custom API key
  setApiKey(apiKey: string): void {
    this.defaultHeaders['X-API-Key'] = apiKey;
  }

  // Get current API key
  getApiKey(): string {
    return this.defaultHeaders['X-API-Key'];
  }
}

// Export singleton instance
export const apiService = new ApiService();
export default apiService;