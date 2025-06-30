/**
 * Upload Page - Main document upload interface
 */

import React from 'react';
import { Container, Typography, Box } from '@mui/material';
import { DocumentUpload } from '../../components/upload/DocumentUpload';
import { UploadResponse, StatusResponse } from '../../services/apiService';

export const UploadPage: React.FC = () => {
  const handleUploadComplete = (response: UploadResponse) => {
    console.log('Upload completed:', response);
    // Could navigate to status page or show success message
  };

  const handleStatusUpdate = (status: StatusResponse) => {
    console.log('Status update:', status);
    // Could update global state or show notifications
  };

  return (
    <Container maxWidth="lg">
      <Box sx={{ py: 4 }}>
        <Typography variant="h3" component="h1" gutterBottom align="center">
          AutoSpec.AI Document Processing
        </Typography>
        
        <Typography variant="h6" color="text.secondary" align="center" sx={{ mb: 4 }}>
          Transform your documents into structured system requirements using AI
        </Typography>

        <DocumentUpload 
          onUploadComplete={handleUploadComplete}
          onStatusUpdate={handleStatusUpdate}
        />
      </Box>
    </Container>
  );
};

export default UploadPage;