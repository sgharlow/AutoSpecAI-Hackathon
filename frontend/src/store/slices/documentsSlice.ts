import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { documentsAPI } from '../../services/api/documentsAPI';

export interface Document {
  id: string;
  title: string;
  type: 'pdf' | 'docx' | 'txt' | 'rtf';
  status: 'uploading' | 'processing' | 'completed' | 'failed' | 'draft';
  content?: string;
  originalFileName: string;
  fileSize: number;
  uploadedBy: string;
  uploadedAt: string;
  processedAt?: string;
  organizationId: string;
  tags: string[];
  metadata: {
    version: number;
    lastModified: string;
    lastModifiedBy: string;
    collaborators: string[];
    processingTime?: number;
    wordCount?: number;
    pageCount?: number;
    language?: string;
  };
  permissions: {
    canEdit: boolean;
    canShare: boolean;
    canDelete: boolean;
    canComment: boolean;
  };
  aiAnalysis?: {
    requirements: any[];
    summary: string;
    complexity: 'low' | 'medium' | 'high';
    completeness: number;
    suggestions: string[];
  };
}

export interface DocumentVersion {
  versionNumber: number;
  userId: string;
  timestamp: string;
  contentHash: string;
  changeDescription: string;
  size: number;
  isAutoSave?: boolean;
}

export interface Comment {
  commentId: string;
  threadId: string;
  userId: string;
  content: string;
  timestamp: string;
  status: 'active' | 'resolved' | 'deleted';
  type: 'comment' | 'reply';
  annotationData?: {
    selectionStart: number;
    selectionEnd: number;
    selectedText: string;
    position: { line: number; column: number };
  };
}

interface DocumentsState {
  documents: Document[];
  currentDocument: Document | null;
  documentVersions: DocumentVersion[];
  documentComments: Record<string, Comment[]>;
  isLoading: boolean;
  isUploading: boolean;
  isProcessing: boolean;
  error: string | null;
  uploadProgress: number;
  searchQuery: string;
  filters: {
    type: string[];
    status: string[];
    tags: string[];
    dateRange: {
      start: string | null;
      end: string | null;
    };
  };
  sortBy: 'title' | 'uploadedAt' | 'lastModified' | 'status';
  sortOrder: 'asc' | 'desc';
  pagination: {
    page: number;
    limit: number;
    total: number;
  };
}

const initialState: DocumentsState = {
  documents: [],
  currentDocument: null,
  documentVersions: [],
  documentComments: {},
  isLoading: false,
  isUploading: false,
  isProcessing: false,
  error: null,
  uploadProgress: 0,
  searchQuery: '',
  filters: {
    type: [],
    status: [],
    tags: [],
    dateRange: {
      start: null,
      end: null,
    },
  },
  sortBy: 'uploadedAt',
  sortOrder: 'desc',
  pagination: {
    page: 1,
    limit: 20,
    total: 0,
  },
};

// Async thunks
export const fetchDocuments = createAsyncThunk(
  'documents/fetchDocuments',
  async (params: {
    page?: number;
    limit?: number;
    search?: string;
    filters?: any;
    sortBy?: string;
    sortOrder?: string;
  } = {}, { rejectWithValue }) => {
    try {
      const response = await documentsAPI.getDocuments(params);
      return response;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to fetch documents');
    }
  }
);

export const fetchDocument = createAsyncThunk(
  'documents/fetchDocument',
  async (documentId: string, { rejectWithValue }) => {
    try {
      const response = await documentsAPI.getDocument(documentId);
      return response;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to fetch document');
    }
  }
);

export const uploadDocument = createAsyncThunk(
  'documents/uploadDocument',
  async (data: { file: File; metadata?: any }, { rejectWithValue, dispatch }) => {
    try {
      const response = await documentsAPI.uploadDocument(data.file, data.metadata, (progress) => {
        dispatch(setUploadProgress(progress));
      });
      return response;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Upload failed');
    }
  }
);

export const processDocument = createAsyncThunk(
  'documents/processDocument',
  async (documentId: string, { rejectWithValue }) => {
    try {
      const response = await documentsAPI.processDocument(documentId);
      return response;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Processing failed');
    }
  }
);

export const updateDocument = createAsyncThunk(
  'documents/updateDocument',
  async (data: { documentId: string; updates: Partial<Document> }, { rejectWithValue }) => {
    try {
      const response = await documentsAPI.updateDocument(data.documentId, data.updates);
      return response;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Update failed');
    }
  }
);

export const deleteDocument = createAsyncThunk(
  'documents/deleteDocument',
  async (documentId: string, { rejectWithValue }) => {
    try {
      await documentsAPI.deleteDocument(documentId);
      return documentId;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Delete failed');
    }
  }
);

export const shareDocument = createAsyncThunk(
  'documents/shareDocument',
  async (data: { documentId: string; shareWith: string[]; permissions: string[] }, { rejectWithValue }) => {
    try {
      const response = await documentsAPI.shareDocument(data.documentId, data.shareWith, data.permissions);
      return response;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Share failed');
    }
  }
);

export const fetchDocumentVersions = createAsyncThunk(
  'documents/fetchVersions',
  async (documentId: string, { rejectWithValue }) => {
    try {
      const response = await documentsAPI.getDocumentVersions(documentId);
      return response;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to fetch versions');
    }
  }
);

export const createDocumentVersion = createAsyncThunk(
  'documents/createVersion',
  async (data: { documentId: string; content: string; changeDescription?: string }, { rejectWithValue }) => {
    try {
      const response = await documentsAPI.createVersion(data.documentId, data.content, data.changeDescription);
      return response;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to create version');
    }
  }
);

export const restoreDocumentVersion = createAsyncThunk(
  'documents/restoreVersion',
  async (data: { documentId: string; versionNumber: number }, { rejectWithValue }) => {
    try {
      const response = await documentsAPI.restoreVersion(data.documentId, data.versionNumber);
      return response;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to restore version');
    }
  }
);

export const fetchDocumentComments = createAsyncThunk(
  'documents/fetchComments',
  async (documentId: string, { rejectWithValue }) => {
    try {
      const response = await documentsAPI.getDocumentComments(documentId);
      return { documentId, comments: response.threads };
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to fetch comments');
    }
  }
);

export const createComment = createAsyncThunk(
  'documents/createComment',
  async (data: {
    documentId: string;
    content: string;
    annotationData?: any;
    threadId?: string;
  }, { rejectWithValue }) => {
    try {
      const response = await documentsAPI.createComment(data);
      return { documentId: data.documentId, comment: response };
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to create comment');
    }
  }
);

export const resolveComment = createAsyncThunk(
  'documents/resolveComment',
  async (data: { documentId: string; commentId: string }, { rejectWithValue }) => {
    try {
      await documentsAPI.resolveComment(data.documentId, data.commentId);
      return data;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to resolve comment');
    }
  }
);

const documentsSlice = createSlice({
  name: 'documents',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    setUploadProgress: (state, action: PayloadAction<number>) => {
      state.uploadProgress = action.payload;
    },
    setSearchQuery: (state, action: PayloadAction<string>) => {
      state.searchQuery = action.payload;
    },
    setFilters: (state, action: PayloadAction<Partial<DocumentsState['filters']>>) => {
      state.filters = { ...state.filters, ...action.payload };
    },
    setSorting: (state, action: PayloadAction<{ sortBy: string; sortOrder: 'asc' | 'desc' }>) => {
      state.sortBy = action.payload.sortBy as any;
      state.sortOrder = action.payload.sortOrder;
    },
    setPagination: (state, action: PayloadAction<{ page: number; limit: number }>) => {
      state.pagination.page = action.payload.page;
      state.pagination.limit = action.payload.limit;
    },
    clearCurrentDocument: (state) => {
      state.currentDocument = null;
      state.documentVersions = [];
    },
    updateCurrentDocumentContent: (state, action: PayloadAction<string>) => {
      if (state.currentDocument) {
        state.currentDocument.content = action.payload;
        state.currentDocument.metadata.lastModified = new Date().toISOString();
      }
    },
    addComment: (state, action: PayloadAction<{ documentId: string; comment: Comment }>) => {
      const { documentId, comment } = action.payload;
      if (!state.documentComments[documentId]) {
        state.documentComments[documentId] = [];
      }
      state.documentComments[documentId].push(comment);
    },
    updateComment: (state, action: PayloadAction<{ documentId: string; commentId: string; updates: Partial<Comment> }>) => {
      const { documentId, commentId, updates } = action.payload;
      const comments = state.documentComments[documentId];
      if (comments) {
        const commentIndex = comments.findIndex(c => c.commentId === commentId);
        if (commentIndex !== -1) {
          comments[commentIndex] = { ...comments[commentIndex], ...updates };
        }
      }
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch documents
      .addCase(fetchDocuments.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchDocuments.fulfilled, (state, action) => {
        state.isLoading = false;
        state.documents = action.payload.documents;
        state.pagination.total = action.payload.total;
      })
      .addCase(fetchDocuments.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })
      
      // Fetch single document
      .addCase(fetchDocument.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchDocument.fulfilled, (state, action) => {
        state.isLoading = false;
        state.currentDocument = action.payload;
      })
      .addCase(fetchDocument.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })
      
      // Upload document
      .addCase(uploadDocument.pending, (state) => {
        state.isUploading = true;
        state.error = null;
        state.uploadProgress = 0;
      })
      .addCase(uploadDocument.fulfilled, (state, action) => {
        state.isUploading = false;
        state.uploadProgress = 100;
        state.documents.unshift(action.payload);
      })
      .addCase(uploadDocument.rejected, (state, action) => {
        state.isUploading = false;
        state.uploadProgress = 0;
        state.error = action.payload as string;
      })
      
      // Process document
      .addCase(processDocument.pending, (state) => {
        state.isProcessing = true;
        state.error = null;
      })
      .addCase(processDocument.fulfilled, (state, action) => {
        state.isProcessing = false;
        const index = state.documents.findIndex(doc => doc.id === action.payload.id);
        if (index !== -1) {
          state.documents[index] = action.payload;
        }
        if (state.currentDocument?.id === action.payload.id) {
          state.currentDocument = action.payload;
        }
      })
      .addCase(processDocument.rejected, (state, action) => {
        state.isProcessing = false;
        state.error = action.payload as string;
      })
      
      // Update document
      .addCase(updateDocument.fulfilled, (state, action) => {
        const index = state.documents.findIndex(doc => doc.id === action.payload.id);
        if (index !== -1) {
          state.documents[index] = action.payload;
        }
        if (state.currentDocument?.id === action.payload.id) {
          state.currentDocument = action.payload;
        }
      })
      .addCase(updateDocument.rejected, (state, action) => {
        state.error = action.payload as string;
      })
      
      // Delete document
      .addCase(deleteDocument.fulfilled, (state, action) => {
        state.documents = state.documents.filter(doc => doc.id !== action.payload);
        if (state.currentDocument?.id === action.payload) {
          state.currentDocument = null;
        }
      })
      .addCase(deleteDocument.rejected, (state, action) => {
        state.error = action.payload as string;
      })
      
      // Document versions
      .addCase(fetchDocumentVersions.fulfilled, (state, action) => {
        state.documentVersions = action.payload.versions;
      })
      .addCase(createDocumentVersion.fulfilled, (state, action) => {
        state.documentVersions.unshift(action.payload);
      })
      .addCase(restoreDocumentVersion.fulfilled, (state, action) => {
        state.documentVersions.unshift(action.payload);
        if (state.currentDocument) {
          state.currentDocument.metadata.version = action.payload.versionNumber;
          state.currentDocument.metadata.lastModified = action.payload.timestamp;
        }
      })
      
      // Document comments
      .addCase(fetchDocumentComments.fulfilled, (state, action) => {
        const { documentId, comments } = action.payload;
        state.documentComments[documentId] = comments.flat();
      })
      .addCase(createComment.fulfilled, (state, action) => {
        const { documentId, comment } = action.payload;
        if (!state.documentComments[documentId]) {
          state.documentComments[documentId] = [];
        }
        state.documentComments[documentId].push(comment);
      })
      .addCase(resolveComment.fulfilled, (state, action) => {
        const { documentId, commentId } = action.payload;
        const comments = state.documentComments[documentId];
        if (comments) {
          const commentIndex = comments.findIndex(c => c.commentId === commentId);
          if (commentIndex !== -1) {
            comments[commentIndex].status = 'resolved';
          }
        }
      });
  },
});

export const {
  clearError,
  setUploadProgress,
  setSearchQuery,
  setFilters,
  setSorting,
  setPagination,
  clearCurrentDocument,
  updateCurrentDocumentContent,
  addComment,
  updateComment,
} = documentsSlice.actions;

export { documentsSlice };