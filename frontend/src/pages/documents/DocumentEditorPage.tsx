import React, { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Paper,
  Typography,
  Button,
  IconButton,
  Divider,
  Chip,
  Tooltip,
  Alert,
  Snackbar,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
} from '@mui/material';
import {
  Save as SaveIcon,
  Share as ShareIcon,
  History as HistoryIcon,
  Comment as CommentIcon,
  Group as CollaboratorsIcon,
  Download as DownloadIcon,
  Preview as PreviewIcon,
  Edit as EditIcon,
  CheckCircle as ApproveIcon,
  Cancel as RejectIcon,
} from '@mui/icons-material';
import { useSelector, useDispatch } from 'react-redux';
import { RootState } from '../../store/store';
import {
  fetchDocument,
  updateDocument,
  createDocumentVersion,
  fetchDocumentComments,
  createComment,
} from '../../store/slices/documentsSlice';
import { useWebSocket } from '../../contexts/WebSocketContext';
import { DocumentEditor } from '../../components/documents/DocumentEditor';
import { CollaboratorsList } from '../../components/collaboration/CollaboratorsList';
import { CommentsPanel } from '../../components/collaboration/CommentsPanel';
import { VersionHistory } from '../../components/documents/VersionHistory';
import { DocumentPreview } from '../../components/documents/DocumentPreview';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';

export const DocumentEditorPage: React.FC = () => {
  const { documentId } = useParams<{ documentId: string }>();
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const { connectToDocument, disconnectFromDocument, updatePresence, isConnected } = useWebSocket();
  
  const { currentDocument, isLoading, error } = useSelector((state: RootState) => state.documents);
  const { activeCollaborators } = useSelector((state: RootState) => state.collaboration);
  const { user } = useSelector((state: RootState) => state.auth);
  
  const [isEditing, setIsEditing] = useState(false);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [showComments, setShowComments] = useState(false);
  const [showVersionHistory, setShowVersionHistory] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [saveDescription, setSaveDescription] = useState('');
  const [snackbarMessage, setSnackbarMessage] = useState('');
  const [showSnackbar, setShowSnackbar] = useState(false);
  
  const editorRef = useRef<any>(null);
  const autoSaveIntervalRef = useRef<NodeJS.Timeout>();

  useEffect(() => {
    if (documentId) {
      dispatch(fetchDocument(documentId));
      dispatch(fetchDocumentComments(documentId));
      
      if (isConnected) {
        connectToDocument(documentId);
      }
    }

    return () => {
      disconnectFromDocument();
      if (autoSaveIntervalRef.current) {
        clearInterval(autoSaveIntervalRef.current);
      }
    };
  }, [documentId, dispatch, connectToDocument, disconnectFromDocument, isConnected]);

  useEffect(() => {
    // Setup auto-save
    if (isEditing && hasUnsavedChanges) {
      autoSaveIntervalRef.current = setInterval(() => {
        handleAutoSave();
      }, 30000); // Auto-save every 30 seconds
    }

    return () => {
      if (autoSaveIntervalRef.current) {
        clearInterval(autoSaveIntervalRef.current);
      }
    };
  }, [isEditing, hasUnsavedChanges]);

  const handleContentChange = (content: string) => {
    setHasUnsavedChanges(true);
    
    // Update presence with cursor position
    if (editorRef.current) {
      const cursorPosition = editorRef.current.getPosition();
      updatePresence({
        status: 'editing',
        cursorPosition,
        lastActivity: new Date().toISOString(),
      });
    }
  };

  const handleAutoSave = async () => {
    if (!currentDocument || !hasUnsavedChanges) return;
    
    try {
      const content = editorRef.current?.getValue() || '';
      await dispatch(createDocumentVersion({
        documentId: currentDocument.id,
        content,
        changeDescription: 'Auto-save',
      }));
      
      setHasUnsavedChanges(false);
      console.log('Auto-saved successfully');
    } catch (error) {
      console.error('Auto-save failed:', error);
    }
  };

  const handleSave = async () => {
    if (!currentDocument) return;
    
    try {
      const content = editorRef.current?.getValue() || '';
      await dispatch(createDocumentVersion({
        documentId: currentDocument.id,
        content,
        changeDescription: saveDescription || 'Manual save',
      }));
      
      setHasUnsavedChanges(false);
      setShowSaveDialog(false);
      setSaveDescription('');
      setSnackbarMessage('Document saved successfully');
      setShowSnackbar(true);
    } catch (error) {
      console.error('Save failed:', error);
      setSnackbarMessage('Failed to save document');
      setShowSnackbar(true);
    }
  };

  const handleShare = () => {
    // Implement share functionality
    console.log('Share document');
  };

  const handleDownload = () => {
    if (!currentDocument) return;
    
    const content = currentDocument.content || '';
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${currentDocument.title}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleStartWorkflow = () => {
    // Implement workflow start
    console.log('Start approval workflow');
  };

  const toggleEditMode = () => {
    setIsEditing(!isEditing);
    
    if (!isEditing) {
      updatePresence({
        status: 'editing',
        lastActivity: new Date().toISOString(),
      });
    } else {
      updatePresence({
        status: 'viewing',
        lastActivity: new Date().toISOString(),
      });
    }
  };

  if (isLoading) {
    return <LoadingSpinner message="Loading document..." />;
  }

  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
        <Button onClick={() => navigate('/documents')}>
          Back to Documents
        </Button>
      </Box>
    );
  }

  if (!currentDocument) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="warning" sx={{ mb: 2 }}>
          Document not found
        </Alert>
        <Button onClick={() => navigate('/documents')}>
          Back to Documents
        </Button>
      </Box>
    );
  }

  const canEdit = currentDocument.permissions.canEdit;
  const canComment = currentDocument.permissions.canComment;

  return (
    <Box sx={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Paper elevation={1} sx={{ p: 2, mb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Typography variant="h5" component="h1">
              {currentDocument.title}
            </Typography>
            
            <Chip
              label={currentDocument.status}
              color={
                currentDocument.status === 'completed' ? 'success' :
                currentDocument.status === 'processing' ? 'warning' :
                currentDocument.status === 'failed' ? 'error' : 'default'
              }
              size="small"
            />
            
            {hasUnsavedChanges && (
              <Chip
                label="Unsaved Changes"
                color="warning"
                size="small"
                variant="outlined"
              />
            )}
            
            {!isConnected && (
              <Chip
                label="Offline"
                color="error"
                size="small"
                variant="outlined"
              />
            )}
          </Box>

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            {/* Collaborators */}
            <Tooltip title="Active Collaborators">
              <IconButton onClick={() => setShowComments(true)}>
                <CollaboratorsIcon />
                {activeCollaborators.length > 0 && (
                  <Typography variant="caption" sx={{ ml: 0.5 }}>
                    {activeCollaborators.length}
                  </Typography>
                )}
              </IconButton>
            </Tooltip>

            {/* Comments */}
            {canComment && (
              <Tooltip title="Comments">
                <IconButton onClick={() => setShowComments(!showComments)}>
                  <CommentIcon />
                </IconButton>
              </Tooltip>
            )}

            {/* Version History */}
            <Tooltip title="Version History">
              <IconButton onClick={() => setShowVersionHistory(true)}>
                <HistoryIcon />
              </IconButton>
            </Tooltip>

            {/* Preview */}
            <Tooltip title="Preview">
              <IconButton onClick={() => setShowPreview(true)}>
                <PreviewIcon />
              </IconButton>
            </Tooltip>

            {/* Save */}
            {canEdit && (
              <Tooltip title="Save">
                <IconButton
                  onClick={() => setShowSaveDialog(true)}
                  disabled={!hasUnsavedChanges}
                  color={hasUnsavedChanges ? 'primary' : 'default'}
                >
                  <SaveIcon />
                </IconButton>
              </Tooltip>
            )}

            {/* Edit Toggle */}
            {canEdit && (
              <Tooltip title={isEditing ? 'Exit Edit Mode' : 'Edit Document'}>
                <IconButton
                  onClick={toggleEditMode}
                  color={isEditing ? 'primary' : 'default'}
                >
                  <EditIcon />
                </IconButton>
              </Tooltip>
            )}

            <Divider orientation="vertical" flexItem sx={{ mx: 1 }} />

            {/* Share */}
            <Tooltip title="Share">
              <IconButton onClick={handleShare}>
                <ShareIcon />
              </IconButton>
            </Tooltip>

            {/* Download */}
            <Tooltip title="Download">
              <IconButton onClick={handleDownload}>
                <DownloadIcon />
              </IconButton>
            </Tooltip>

            {/* Workflow Actions */}
            {currentDocument.status === 'completed' && (
              <>
                <Button
                  startIcon={<ApproveIcon />}
                  onClick={handleStartWorkflow}
                  variant="outlined"
                  color="success"
                  size="small"
                >
                  Start Approval
                </Button>
              </>
            )}
          </Box>
        </Box>
      </Paper>

      {/* Main Content */}
      <Box sx={{ display: 'flex', flex: 1, gap: 2 }}>
        {/* Document Editor */}
        <Paper elevation={1} sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          <DocumentEditor
            ref={editorRef}
            document={currentDocument}
            isEditing={isEditing}
            onContentChange={handleContentChange}
            readOnly={!canEdit || !isEditing}
          />
        </Paper>

        {/* Comments Panel */}
        {showComments && (
          <Paper elevation={1} sx={{ width: 300, display: 'flex', flexDirection: 'column' }}>
            <CommentsPanel
              documentId={currentDocument.id}
              canComment={canComment}
              onClose={() => setShowComments(false)}
            />
          </Paper>
        )}
      </Box>

      {/* Collaborators List */}
      <CollaboratorsList
        documentId={currentDocument.id}
        collaborators={activeCollaborators}
      />

      {/* Save Dialog */}
      <Dialog open={showSaveDialog} onClose={() => setShowSaveDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Save Document</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Change Description (Optional)"
            fullWidth
            variant="outlined"
            value={saveDescription}
            onChange={(e) => setSaveDescription(e.target.value)}
            placeholder="Describe the changes you made..."
            multiline
            rows={3}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowSaveDialog(false)}>Cancel</Button>
          <Button onClick={handleSave} variant="contained">Save</Button>
        </DialogActions>
      </Dialog>

      {/* Version History Dialog */}
      <VersionHistory
        open={showVersionHistory}
        onClose={() => setShowVersionHistory(false)}
        documentId={currentDocument.id}
      />

      {/* Preview Dialog */}
      <DocumentPreview
        open={showPreview}
        onClose={() => setShowPreview(false)}
        document={currentDocument}
      />

      {/* Snackbar for notifications */}
      <Snackbar
        open={showSnackbar}
        autoHideDuration={4000}
        onClose={() => setShowSnackbar(false)}
        message={snackbarMessage}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      />
    </Box>
  );
};