/**
 * Test Data Helpers
 * Utilities for creating test users, documents, and data
 */

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

// Test user creation
async function createTestUser(email = null, password = 'testpassword123') {
  const randomId = crypto.randomUUID();
  const testEmail = email || `testuser-${randomId}@example.com`;
  
  const user = {
    id: `user-${randomId}`,
    email: testEmail,
    password: password,
    firstName: 'Test',
    lastName: 'User',
    role: 'user',
    preferences: {
      theme: 'light',
      notifications: true,
      language: 'en'
    },
    createdAt: new Date().toISOString()
  };
  
  // In a real implementation, this would create the user in the database
  // For testing, we'll mock the user creation
  if (process.env.NODE_ENV === 'test') {
    // Store user in test database or mock service
    console.log(`Created test user: ${testEmail}`);
  }
  
  return user;
}

// Test document generation
function generateTestDocument(filename, fileType, sizeInBytes = 1024) {
  const fileExtension = path.extname(filename).toLowerCase();
  const mimeTypes = {
    '.pdf': 'application/pdf',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.doc': 'application/msword',
    '.txt': 'text/plain',
    '.md': 'text/markdown',
    '.rtf': 'application/rtf'
  };
  
  const mimeType = mimeTypes[fileExtension] || fileType;
  
  // Generate mock file content based on type
  let content;
  if (fileType === 'pdf' || fileExtension === '.pdf') {
    content = generatePDFContent(filename, sizeInBytes);
  } else if (fileType === 'docx' || fileExtension === '.docx') {
    content = generateDocxContent(filename, sizeInBytes);
  } else {
    content = generateTextContent(filename, sizeInBytes);
  }
  
  return {
    name: filename,
    type: mimeType,
    size: sizeInBytes,
    buffer: Buffer.from(content),
    lastModified: Date.now(),
    content: content
  };
}

// Generate PDF-like content
function generatePDFContent(filename, size) {
  const baseContent = `
%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
/Resources <<
/Font <<
/F1 5 0 R
>>
>>
>>
endobj

4 0 obj
<<
/Length 100
>>
stream
BT
/F1 12 Tf
100 700 Td
(Test Document: ${filename}) Tj
0 -20 Td
(This is a test document for AutoSpec.AI) Tj
0 -20 Td
(System Requirements:) Tj
0 -20 Td
(REQ-001: The system shall process PDF documents) Tj
0 -20 Td
(REQ-002: The system shall extract requirements automatically) Tj
0 -20 Td
(REQ-003: The system shall support collaborative editing) Tj
ET
endstream
endobj

5 0 obj
<<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>
endobj

xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000265 00000 n 
0000000565 00000 n 
trailer
<<
/Size 6
/Root 1 0 R
>>
startxref
625
%%EOF
`;
  
  // Pad content to reach desired size
  const padding = Math.max(0, size - baseContent.length);
  return baseContent + ' '.repeat(padding);
}

// Generate DOCX-like content
function generateDocxContent(filename, size) {
  const baseContent = `
PK\x03\x04Test Document: ${filename}

This is a test document for AutoSpec.AI system.

System Requirements:

REQ-001: The system shall process DOCX documents
The system must be capable of reading and processing Microsoft Word documents in DOCX format.

REQ-002: The system shall extract requirements automatically
The system shall use AI to automatically identify and extract requirements from documents.

REQ-003: The system shall support collaborative editing
Multiple users should be able to edit documents simultaneously with real-time synchronization.

Functional Requirements:
- Document upload and storage
- AI-powered requirement extraction
- Real-time collaboration
- Version control
- Export capabilities

Non-Functional Requirements:
- Performance: Response time < 2 seconds
- Scalability: Support 1000+ concurrent users
- Security: End-to-end encryption
- Availability: 99.9% uptime
`;
  
  const padding = Math.max(0, size - baseContent.length);
  return baseContent + '\n'.repeat(Math.floor(padding / 2));
}

// Generate text content
function generateTextContent(filename, size) {
  const baseContent = `Test Document: ${filename}

This is a test document for AutoSpec.AI system.

System Requirements:

REQ-001: The system shall process text documents
REQ-002: The system shall extract requirements automatically
REQ-003: The system shall support collaborative editing
REQ-004: The system shall maintain version history
REQ-005: The system shall provide export functionality

Detailed Requirements:

1. Document Processing
   - Support multiple file formats (PDF, DOCX, TXT)
   - Extract text content accurately
   - Preserve document structure

2. AI Analysis
   - Identify requirement patterns
   - Classify requirements by type
   - Generate structured output

3. Collaboration Features
   - Real-time editing
   - Comments and annotations
   - User presence indicators
   - Conflict resolution

4. Version Control
   - Track document changes
   - Compare versions
   - Restore previous versions
   - Audit trail

5. Export and Integration
   - Multiple export formats
   - API integration
   - Webhook notifications
   - Third-party connectors
`;
  
  const padding = Math.max(0, size - baseContent.length);
  return baseContent + '\n' + 'Additional content. '.repeat(Math.floor(padding / 20));
}

// Generate test collaboration data
function generateCollaborationData() {
  return {
    session: {
      id: crypto.randomUUID(),
      documentId: 'test-doc-' + crypto.randomUUID(),
      participants: [
        {
          userId: 'user-1',
          email: 'user1@example.com',
          cursor: { line: 1, column: 1 },
          selection: { start: { line: 1, column: 1 }, end: { line: 1, column: 5 } }
        },
        {
          userId: 'user-2',
          email: 'user2@example.com',
          cursor: { line: 5, column: 10 },
          selection: null
        }
      ],
      lastActivity: new Date().toISOString()
    },
    comments: [
      {
        id: crypto.randomUUID(),
        author: 'user1@example.com',
        content: 'This requirement needs more detail',
        selection: { start: { line: 10, column: 1 }, end: { line: 10, column: 25 } },
        timestamp: new Date().toISOString(),
        resolved: false,
        replies: [
          {
            id: crypto.randomUUID(),
            author: 'user2@example.com',
            content: 'I agree, will add more information',
            timestamp: new Date(Date.now() + 60000).toISOString()
          }
        ]
      }
    ]
  };
}

// Generate test workflow data
function generateWorkflowData() {
  return {
    id: crypto.randomUUID(),
    name: 'Document Approval Workflow',
    type: 'approval',
    status: 'active',
    documentId: 'test-doc-' + crypto.randomUUID(),
    initiator: 'user1@example.com',
    approvers: [
      {
        email: 'approver1@example.com',
        status: 'pending',
        assignedAt: new Date().toISOString()
      },
      {
        email: 'approver2@example.com',
        status: 'pending',
        assignedAt: new Date().toISOString()
      }
    ],
    deadline: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(), // 7 days from now
    description: 'Please review and approve this document',
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString()
  };
}

// Generate test analytics data
function generateAnalyticsData() {
  return {
    documents: {
      total: 150,
      processed: 142,
      failed: 8,
      averageProcessingTime: 45000, // milliseconds
      byType: {
        pdf: 85,
        docx: 45,
        txt: 20
      }
    },
    requirements: {
      total: 1250,
      functional: 750,
      nonFunctional: 500,
      averagePerDocument: 8.3
    },
    users: {
      total: 25,
      active: 18,
      newThisMonth: 5
    },
    collaboration: {
      activeSessions: 12,
      totalComments: 445,
      averageCommentsPerDocument: 2.97
    }
  };
}

// Mock API responses
const mockAPIResponses = {
  login: {
    success: {
      token: 'mock-jwt-token-' + crypto.randomUUID(),
      user: {
        id: 'user-123',
        email: 'test@example.com',
        firstName: 'Test',
        lastName: 'User',
        role: 'user'
      }
    },
    error: {
      message: 'Invalid credentials',
      code: 'AUTH_ERROR'
    }
  },
  documentUpload: {
    success: {
      id: 'doc-' + crypto.randomUUID(),
      filename: 'test-document.pdf',
      status: 'processing',
      uploadedAt: new Date().toISOString()
    },
    error: {
      message: 'File type not supported',
      code: 'INVALID_FILE_TYPE'
    }
  },
  documentProcessing: {
    success: {
      id: 'doc-123',
      status: 'completed',
      requirements: [
        { id: 'REQ-001', text: 'The system shall process documents', type: 'functional' },
        { id: 'REQ-002', text: 'The system shall extract requirements', type: 'functional' },
        { id: 'REQ-003', text: 'Response time shall be < 2 seconds', type: 'non-functional' }
      ],
      processedAt: new Date().toISOString(),
      processingTime: 30000
    },
    error: {
      message: 'Document processing failed',
      code: 'PROCESSING_ERROR'
    }
  }
};

// Test data cleanup
function cleanupTestData() {
  // In a real implementation, this would clean up test data from the database
  console.log('Cleaning up test data...');
}

module.exports = {
  createTestUser,
  generateTestDocument,
  generateCollaborationData,
  generateWorkflowData,
  generateAnalyticsData,
  mockAPIResponses,
  cleanupTestData
};