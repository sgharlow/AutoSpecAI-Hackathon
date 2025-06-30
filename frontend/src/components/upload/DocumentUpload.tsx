/**
 * Document Upload Component
 * Integrates with production AutoSpecAI API
 */

import React, { useState, useCallback } from 'react';
import {
  Box,
  Button,
  Typography,
  Paper,
  LinearProgress,
  Alert,
  Chip,
  Grid,
  TextField,
  FormControlLabel,
  Checkbox,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';
import {
  CloudUpload as UploadIcon,
  Description as DocumentIcon,
  ExpandMore as ExpandMoreIcon,
} from '@mui/icons-material';
import { useDropzone } from 'react-dropzone';
import { apiService, UploadResponse, StatusResponse } from '../../services/apiService';

interface DocumentUploadProps {
  onUploadComplete?: (response: UploadResponse) => void;
  onStatusUpdate?: (status: StatusResponse) => void;
}

export const DocumentUpload: React.FC<DocumentUploadProps> = ({
  onUploadComplete,
  onStatusUpdate,
}) => {
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadResponse, setUploadResponse] = useState<UploadResponse | null>(null);
  const [currentStatus, setCurrentStatus] = useState<StatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [userEmail, setUserEmail] = useState('');
  const [preferences, setPreferences] = useState({
    quality: 'high' as 'standard' | 'high' | 'premium',
    includeHTML: true,
    includeJSON: true,
    includeMarkdown: true,
    includePDF: false,
  });

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return;

    const file = acceptedFiles[0];
    setError(null);
    setUploading(true);
    setUploadProgress(0);

    try {
      // Validate file
      const maxSize = 10 * 1024 * 1024; // 10MB
      if (file.size > maxSize) {
        throw new Error('File size exceeds 10MB limit');
      }

      const allowedTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/msword', 'text/plain'];
      if (!allowedTypes.includes(file.type) && !file.name.match(/\.(pdf|docx|doc|txt)$/i)) {
        throw new Error('Unsupported file type. Please upload PDF, DOCX, DOC, or TXT files.');
      }

      // Simulate upload progress
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + 10;
        });
      }, 200);

      // Upload file
      const response = await apiService.uploadFile(file, userEmail || undefined);
      
      clearInterval(progressInterval);
      setUploadProgress(100);
      setUploadResponse(response);
      
      if (onUploadComplete) {
        onUploadComplete(response);
      }

      // Start polling for status updates
      if (response.request_id) {
        pollForUpdates(response.request_id);
      }

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Upload failed';
      setError(errorMessage);
    } finally {
      setUploading(false);
    }
  }, [userEmail, onUploadComplete]);

  const pollForUpdates = async (requestId: string) => {
    try {
      await apiService.pollStatus(
        requestId,
        (status) => {
          setCurrentStatus(status);
          if (onStatusUpdate) {
            onStatusUpdate(status);
          }
        },
        60, // max attempts
        5000 // 5 second interval
      );
    } catch (err) {
      console.error('Status polling failed:', err);
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/msword': ['.doc'],
      'text/plain': ['.txt'],
    },
    multiple: false,
    disabled: uploading,
  });

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'delivered': return 'success';
      case 'failed': return 'error';
      case 'processing': return 'warning';
      default: return 'info';
    }
  };

  return (
    <Box sx={{ maxWidth: 800, mx: 'auto', p: 3 }}>
      <Typography variant="h4" gutterBottom align="center">
        Upload Document for AI Analysis
      </Typography>
      
      <Typography variant="body1" color="text.secondary" align="center" sx={{ mb: 4 }}>
        Upload PDF, DOCX, DOC, or TXT files to generate AI-powered system requirements
      </Typography>

      {/* Upload Area */}
      <Paper
        {...getRootProps()}
        sx={{
          p: 4,
          textAlign: 'center',
          cursor: uploading ? 'default' : 'pointer',
          border: '2px dashed',
          borderColor: isDragActive ? 'primary.main' : 'grey.300',
          bgcolor: isDragActive ? 'action.hover' : 'background.paper',
          transition: 'all 0.2s ease',
          '&:hover': {
            borderColor: uploading ? 'grey.300' : 'primary.main',
            bgcolor: uploading ? 'background.paper' : 'action.hover',
          },
          mb: 3,
        }}
      >
        <input {...getInputProps()} />
        <UploadIcon sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
        
        {uploading ? (
          <Box>
            <Typography variant="h6" gutterBottom>
              Uploading...
            </Typography>
            <LinearProgress variant="determinate" value={uploadProgress} sx={{ mt: 2 }} />
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              {uploadProgress}%
            </Typography>
          </Box>
        ) : (
          <Box>
            <Typography variant="h6" gutterBottom>
              {isDragActive ? 'Drop the file here' : 'Drag & drop a document or click to browse'}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Supports PDF, DOCX, DOC, TXT (max 10MB)
            </Typography>
            <Button variant="contained" sx={{ mt: 2 }}>
              Select File
            </Button>
          </Box>
        )}
      </Paper>

      {/* Email Input */}
      <TextField
        fullWidth
        label="Email Address (optional)"
        type="email"
        value={userEmail}
        onChange={(e) => setUserEmail(e.target.value)}
        helperText="Receive notifications and results via email"
        sx={{ mb: 3 }}
      />

      {/* Advanced Options */}
      <Accordion sx={{ mb: 3 }}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography>Advanced Options</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <Typography variant="subtitle2" gutterBottom>
                Output Formats
              </Typography>
              <FormControlLabel
                control={
                  <Checkbox
                    checked={preferences.includeHTML}
                    onChange={(e) => setPreferences(prev => ({ ...prev, includeHTML: e.target.checked }))}
                  />
                }
                label="Interactive HTML"
              />
              <FormControlLabel
                control={
                  <Checkbox
                    checked={preferences.includeJSON}
                    onChange={(e) => setPreferences(prev => ({ ...prev, includeJSON: e.target.checked }))}
                  />
                }
                label="Structured JSON"
              />
              <FormControlLabel
                control={
                  <Checkbox
                    checked={preferences.includeMarkdown}
                    onChange={(e) => setPreferences(prev => ({ ...prev, includeMarkdown: e.target.checked }))}
                  />
                }
                label="Markdown"
              />
              <FormControlLabel
                control={
                  <Checkbox
                    checked={preferences.includePDF}
                    onChange={(e) => setPreferences(prev => ({ ...prev, includePDF: e.target.checked }))}
                  />
                }
                label="Professional PDF"
              />
            </Grid>
          </Grid>
        </AccordionDetails>
      </Accordion>

      {/* Error Display */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {/* Upload Success */}
      {uploadResponse && (
        <Alert severity="success" sx={{ mb: 3 }}>
          <Typography variant="subtitle2" gutterBottom>
            Upload Successful!
          </Typography>
          <Typography variant="body2">
            Request ID: <code>{uploadResponse.request_id}</code>
          </Typography>
          <Typography variant="body2">
            Estimated processing time: {uploadResponse.estimated_processing_time}
          </Typography>
        </Alert>
      )}

      {/* Processing Status */}
      {currentStatus && (
        <Paper sx={{ p: 3, mt: 3 }}>
          <Typography variant="h6" gutterBottom>
            Processing Status
          </Typography>
          
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
            <DocumentIcon />
            <Typography variant="body1">
              {currentStatus.filename}
            </Typography>
            <Chip 
              label={currentStatus.status} 
              color={getStatusColor(currentStatus.status) as any}
              size="small"
            />
          </Box>

          <Box sx={{ mb: 2 }}>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              Progress: {currentStatus.progress_percentage}%
            </Typography>
            <LinearProgress 
              variant="determinate" 
              value={currentStatus.progress_percentage} 
            />
          </Box>

          <Typography variant="body2" color="text.secondary">
            Stage: {currentStatus.processing_stage}
          </Typography>

          {currentStatus.error_message && (
            <Alert severity="error" sx={{ mt: 2 }}>
              {currentStatus.error_message}
            </Alert>
          )}

          {currentStatus.status === 'delivered' && (
            <Alert severity="success" sx={{ mt: 2 }}>
              Processing complete! Results have been delivered.
            </Alert>
          )}
        </Paper>
      )}
    </Box>
  );
};

export default DocumentUpload;