/**
 * Test Data Setup Script
 * Creates and initializes test data for the testing environment
 */

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

// Configuration
const TEST_DATA_CONFIG = {
  users: {
    count: 10,
    roles: ['admin', 'user', 'viewer', 'collaborator']
  },
  documents: {
    count: 25,
    types: ['pdf', 'docx', 'txt'],
    statuses: ['processing', 'completed', 'failed']
  },
  workflows: {
    count: 15,
    types: ['approval', 'review', 'collaboration']
  }
};

async function setupTestData() {
  console.log('Setting up test data...');
  
  try {
    // Create test data directory
    const testDataDir = path.join(process.cwd(), 'test-data');
    if (!fs.existsSync(testDataDir)) {
      fs.mkdirSync(testDataDir, { recursive: true });
    }
    
    // Generate test data
    const testData = {
      users: await generateTestUsers(),
      documents: await generateTestDocuments(),
      workflows: await generateTestWorkflows(),
      analytics: await generateTestAnalytics(),
      notifications: await generateTestNotifications(),
      metadata: {
        createdAt: new Date().toISOString(),
        version: '1.0.0',
        environment: process.env.NODE_ENV || 'test'
      }
    };
    
    // Save test data to files
    await saveTestData(testData, testDataDir);
    
    // Initialize database with test data (if using real database)
    if (process.env.INIT_DATABASE === 'true') {
      await initializeDatabaseWithTestData(testData);
    }
    
    console.log('Test data setup completed successfully');
    console.log(`Generated ${testData.users.length} users, ${testData.documents.length} documents, ${testData.workflows.length} workflows`);
    
    return testData;
    
  } catch (error) {
    console.error('Test data setup failed:', error);
    throw error;
  }
}

async function generateTestUsers() {
  const users = [];
  const { count, roles } = TEST_DATA_CONFIG.users;
  
  for (let i = 0; i < count; i++) {
    const userId = crypto.randomUUID();
    const role = roles[i % roles.length];
    
    const user = {
      id: userId,
      email: `testuser${i + 1}@example.com`,
      firstName: `Test${i + 1}`,
      lastName: 'User',
      role: role,
      password: 'testpassword123', // In real system, this would be hashed
      preferences: {
        theme: i % 2 === 0 ? 'light' : 'dark',
        notifications: true,
        language: 'en',
        timezone: 'UTC'
      },
      profile: {
        avatar: `https://api.dicebear.com/7.x/avataaars/svg?seed=${userId}`,
        bio: `Test user ${i + 1} for AutoSpec.AI testing`,
        department: ['Engineering', 'Product', 'Design', 'QA'][i % 4],
        location: ['New York', 'San Francisco', 'London', 'Toronto'][i % 4]
      },
      permissions: generateUserPermissions(role),
      createdAt: new Date(Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000).toISOString(), // Random date within last 30 days
      lastLoginAt: new Date(Date.now() - Math.random() * 7 * 24 * 60 * 60 * 1000).toISOString(), // Random date within last 7 days
      isActive: Math.random() > 0.1 // 90% active
    };
    
    users.push(user);
  }
  
  // Add a known admin user for testing
  users.push({
    id: 'admin-test-user',
    email: 'admin@autospec.ai',
    firstName: 'Admin',
    lastName: 'User',
    role: 'admin',
    password: 'adminpassword123',
    preferences: {
      theme: 'light',
      notifications: true,
      language: 'en',
      timezone: 'UTC'
    },
    profile: {
      avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=admin',
      bio: 'Administrator account for testing',
      department: 'Engineering',
      location: 'San Francisco'
    },
    permissions: generateUserPermissions('admin'),
    createdAt: new Date('2024-01-01').toISOString(),
    lastLoginAt: new Date().toISOString(),
    isActive: true
  });
  
  return users;
}

function generateUserPermissions(role) {
  const basePermissions = ['read_documents', 'create_comments'];
  
  const rolePermissions = {
    admin: ['*'], // All permissions
    user: [...basePermissions, 'create_documents', 'edit_documents', 'delete_own_documents'],
    collaborator: [...basePermissions, 'edit_documents', 'create_workflows'],
    viewer: basePermissions
  };
  
  return rolePermissions[role] || basePermissions;
}

async function generateTestDocuments() {
  const documents = [];
  const { count, types, statuses } = TEST_DATA_CONFIG.documents;
  
  for (let i = 0; i < count; i++) {
    const documentId = crypto.randomUUID();
    const type = types[i % types.length];
    const status = statuses[i % statuses.length];
    
    const document = {
      id: documentId,
      title: `Test Document ${i + 1}`,
      filename: `test-document-${i + 1}.${type}`,
      type: type,
      size: Math.floor(Math.random() * 5000000) + 100000, // 100KB to 5MB
      status: status,
      content: generateDocumentContent(type, i + 1),
      metadata: {
        uploadedBy: `testuser${(i % 10) + 1}@example.com`,
        uploadedAt: new Date(Date.now() - Math.random() * 60 * 24 * 60 * 60 * 1000).toISOString(), // Random date within last 60 days
        processedAt: status === 'completed' ? new Date(Date.now() - Math.random() * 50 * 24 * 60 * 60 * 1000).toISOString() : null,
        processingTime: status === 'completed' ? Math.floor(Math.random() * 120000) + 5000 : null, // 5-125 seconds
        version: 1,
        tags: generateDocumentTags(i),
        category: ['requirements', 'specifications', 'design', 'testing'][i % 4]
      },
      requirements: status === 'completed' ? generateRequirements(documentId, i + 1) : [],
      collaborators: generateCollaborators(i),
      sharing: {
        isPublic: Math.random() > 0.7, // 30% public
        shareableLink: Math.random() > 0.5 ? `https://app.autospec.ai/share/${crypto.randomUUID()}` : null,
        permissions: {
          allowComments: true,
          allowEditing: Math.random() > 0.6, // 40% allow editing
          allowDownload: true
        }
      },
      analytics: {
        views: Math.floor(Math.random() * 100),
        downloads: Math.floor(Math.random() * 20),
        comments: Math.floor(Math.random() * 10),
        collaborators: Math.floor(Math.random() * 5) + 1
      }
    };
    
    documents.push(document);
  }
  
  return documents;
}

function generateDocumentContent(type, index) {
  const requirements = [
    'The system shall authenticate users using secure methods',
    'The application must process documents within 30 seconds',
    'The interface shall be responsive and mobile-friendly',
    'The system must maintain 99.9% uptime',
    'All data shall be encrypted in transit and at rest'
  ];
  
  const baseContent = `
Document Title: Test Document ${index}

Overview:
This is a test document for AutoSpec.AI system validation.

System Requirements:

${requirements.slice(0, Math.floor(Math.random() * 5) + 1).map((req, i) => `REQ-${String(index * 10 + i + 1).padStart(3, '0')}: ${req}`).join('\n')}

Functional Requirements:
- Document upload and processing
- AI-powered requirement extraction
- Real-time collaboration
- Version control and history
- Export and sharing capabilities

Non-Functional Requirements:
- Performance: Response time < 2 seconds
- Scalability: Support 1000+ concurrent users
- Security: End-to-end encryption
- Availability: 99.9% uptime SLA
- Usability: Intuitive user interface
`;
  
  return baseContent;
}

function generateDocumentTags(index) {
  const allTags = ['requirements', 'specifications', 'design', 'testing', 'api', 'frontend', 'backend', 'mobile', 'security', 'performance'];
  const tagCount = Math.floor(Math.random() * 4) + 1; // 1-4 tags
  const selectedTags = [];
  
  for (let i = 0; i < tagCount; i++) {
    const tag = allTags[(index + i) % allTags.length];
    if (!selectedTags.includes(tag)) {
      selectedTags.push(tag);
    }
  }
  
  return selectedTags;
}

function generateRequirements(documentId, docIndex) {
  const requirements = [];
  const count = Math.floor(Math.random() * 8) + 3; // 3-10 requirements
  
  const types = ['functional', 'non-functional', 'business', 'technical'];
  const priorities = ['high', 'medium', 'low'];
  
  for (let i = 0; i < count; i++) {
    const requirement = {
      id: `REQ-${String(docIndex * 100 + i + 1).padStart(3, '0')}`,
      title: `Requirement ${i + 1} for Document ${docIndex}`,
      description: `This is a detailed description of requirement ${i + 1} for test document ${docIndex}.`,
      type: types[i % types.length],
      priority: priorities[i % priorities.length],
      status: ['draft', 'approved', 'implemented', 'tested'][i % 4],
      source: {
        documentId: documentId,
        section: `Section ${Math.floor(i / 2) + 1}`,
        line: Math.floor(Math.random() * 100) + 1
      },
      acceptance_criteria: [
        `Criteria ${i + 1}.1: The system must validate input`,
        `Criteria ${i + 1}.2: The system must provide feedback`,
        `Criteria ${i + 1}.3: The system must handle errors gracefully`
      ],
      dependencies: i > 0 ? [`REQ-${String(docIndex * 100 + i).padStart(3, '0')}`] : [],
      tags: generateDocumentTags(i),
      createdAt: new Date(Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000).toISOString(),
      updatedAt: new Date(Date.now() - Math.random() * 7 * 24 * 60 * 60 * 1000).toISOString()
    };
    
    requirements.push(requirement);
  }
  
  return requirements;
}

function generateCollaborators(index) {
  const collaboratorCount = Math.floor(Math.random() * 4) + 1; // 1-4 collaborators
  const collaborators = [];
  
  for (let i = 0; i < collaboratorCount; i++) {
    const collaborator = {
      userId: `testuser${((index + i) % 10) + 1}@example.com`,
      role: ['editor', 'reviewer', 'viewer'][i % 3],
      addedAt: new Date(Date.now() - Math.random() * 20 * 24 * 60 * 60 * 1000).toISOString(),
      lastActive: new Date(Date.now() - Math.random() * 2 * 24 * 60 * 60 * 1000).toISOString(),
      permissions: {
        canEdit: i % 3 !== 2, // Viewers can't edit
        canComment: true,
        canShare: i % 3 === 0, // Only editors can share
        canDownload: true
      }
    };
    
    collaborators.push(collaborator);
  }
  
  return collaborators;
}

async function generateTestWorkflows() {
  const workflows = [];
  const { count, types } = TEST_DATA_CONFIG.workflows;
  
  for (let i = 0; i < count; i++) {
    const workflowId = crypto.randomUUID();
    const type = types[i % types.length];
    
    const workflow = {
      id: workflowId,
      name: `${type.charAt(0).toUpperCase() + type.slice(1)} Workflow ${i + 1}`,
      type: type,
      status: ['active', 'completed', 'cancelled', 'pending'][i % 4],
      description: `Test ${type} workflow for document processing`,
      documentId: `doc-${i % 20}`, // Reference to documents
      initiator: `testuser${(i % 10) + 1}@example.com`,
      participants: generateWorkflowParticipants(i),
      steps: generateWorkflowSteps(type, i),
      metadata: {
        createdAt: new Date(Date.now() - Math.random() * 45 * 24 * 60 * 60 * 1000).toISOString(),
        updatedAt: new Date(Date.now() - Math.random() * 5 * 24 * 60 * 60 * 1000).toISOString(),
        deadline: new Date(Date.now() + Math.random() * 14 * 24 * 60 * 60 * 1000).toISOString(),
        priority: ['high', 'medium', 'low'][i % 3],
        estimatedDuration: Math.floor(Math.random() * 168) + 24 // 1-7 days in hours
      },
      currentStep: Math.floor(Math.random() * 3) + 1,
      progress: {
        completedSteps: Math.floor(Math.random() * 3),
        totalSteps: 4,
        percentComplete: Math.floor(Math.random() * 80) + 10 // 10-90%
      }
    };
    
    workflows.push(workflow);
  }
  
  return workflows;
}

function generateWorkflowParticipants(index) {
  const participantCount = Math.floor(Math.random() * 3) + 2; // 2-4 participants
  const participants = [];
  
  for (let i = 0; i < participantCount; i++) {
    const participant = {
      userId: `testuser${((index + i + 1) % 10) + 1}@example.com`,
      role: ['approver', 'reviewer', 'observer'][i % 3],
      status: ['pending', 'approved', 'rejected', 'delegated'][i % 4],
      assignedAt: new Date(Date.now() - Math.random() * 10 * 24 * 60 * 60 * 1000).toISOString(),
      respondedAt: Math.random() > 0.3 ? new Date(Date.now() - Math.random() * 5 * 24 * 60 * 60 * 1000).toISOString() : null,
      comments: Math.random() > 0.5 ? `Comments from participant ${i + 1}` : null
    };
    
    participants.push(participant);
  }
  
  return participants;
}

function generateWorkflowSteps(type, index) {
  const stepTemplates = {
    approval: [
      { name: 'Initial Review', description: 'Document review by team lead' },
      { name: 'Technical Approval', description: 'Technical review and approval' },
      { name: 'Final Approval', description: 'Final approval by stakeholder' },
      { name: 'Publication', description: 'Publish approved document' }
    ],
    review: [
      { name: 'Content Review', description: 'Review document content' },
      { name: 'Quality Check', description: 'Quality assurance check' },
      { name: 'Feedback Integration', description: 'Integrate reviewer feedback' },
      { name: 'Final Review', description: 'Final review and sign-off' }
    ],
    collaboration: [
      { name: 'Team Assignment', description: 'Assign team members' },
      { name: 'Collaborative Editing', description: 'Team editing phase' },
      { name: 'Consensus Building', description: 'Build consensus on changes' },
      { name: 'Finalization', description: 'Finalize collaborative work' }
    ]
  };
  
  const templates = stepTemplates[type] || stepTemplates.approval;
  
  return templates.map((template, i) => ({
    id: `step-${i + 1}`,
    name: template.name,
    description: template.description,
    status: i < (index % 3) + 1 ? 'completed' : 'pending',
    assignee: `testuser${((index + i) % 10) + 1}@example.com`,
    estimatedDuration: Math.floor(Math.random() * 48) + 12, // 12-60 hours
    actualDuration: i < (index % 3) + 1 ? Math.floor(Math.random() * 36) + 6 : null,
    startedAt: i < (index % 3) + 1 ? new Date(Date.now() - Math.random() * 7 * 24 * 60 * 60 * 1000).toISOString() : null,
    completedAt: i < (index % 3) + 1 ? new Date(Date.now() - Math.random() * 3 * 24 * 60 * 60 * 1000).toISOString() : null
  }));
}

async function generateTestAnalytics() {
  const now = new Date();
  const thirtyDaysAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
  
  return {
    overview: {
      totalDocuments: 25,
      processedDocuments: 20,
      failedDocuments: 2,
      pendingDocuments: 3,
      totalUsers: 11,
      activeUsers: 8,
      totalWorkflows: 15,
      completedWorkflows: 8
    },
    trends: {
      documentsPerDay: generateDailyTrend(30, 1, 5),
      usersPerDay: generateDailyTrend(30, 0, 3),
      workflowsPerDay: generateDailyTrend(30, 0, 2)
    },
    performance: {
      averageProcessingTime: 32000, // milliseconds
      averageUploadSize: 2.3, // MB
      systemUptime: 99.7, // percentage
      apiResponseTime: 150 // milliseconds
    },
    usage: {
      topUsers: [
        { email: 'testuser1@example.com', documentCount: 5, lastActive: now.toISOString() },
        { email: 'testuser2@example.com', documentCount: 4, lastActive: new Date(now.getTime() - 2 * 60 * 60 * 1000).toISOString() },
        { email: 'testuser3@example.com', documentCount: 3, lastActive: new Date(now.getTime() - 6 * 60 * 60 * 1000).toISOString() }
      ],
      topDocuments: [
        { title: 'Test Document 1', views: 45, downloads: 12 },
        { title: 'Test Document 5', views: 38, downloads: 8 },
        { title: 'Test Document 10', views: 32, downloads: 6 }
      ],
      featureUsage: {
        documentUpload: 95,
        realTimeCollaboration: 72,
        commentSystem: 68,
        workflowManagement: 45,
        exportFeatures: 38
      }
    }
  };
}

function generateDailyTrend(days, min, max) {
  const trend = [];
  const now = new Date();
  
  for (let i = days - 1; i >= 0; i--) {
    const date = new Date(now.getTime() - i * 24 * 60 * 60 * 1000);
    const value = Math.floor(Math.random() * (max - min + 1)) + min;
    
    trend.push({
      date: date.toISOString().split('T')[0],
      value: value
    });
  }
  
  return trend;
}

async function generateTestNotifications() {
  const notifications = [];
  const types = ['document_processed', 'workflow_assigned', 'comment_added', 'document_shared', 'system_update'];
  
  for (let i = 0; i < 20; i++) {
    const notification = {
      id: crypto.randomUUID(),
      type: types[i % types.length],
      title: generateNotificationTitle(types[i % types.length]),
      message: generateNotificationMessage(types[i % types.length], i),
      userId: `testuser${(i % 10) + 1}@example.com`,
      read: Math.random() > 0.3, // 70% read
      createdAt: new Date(Date.now() - Math.random() * 14 * 24 * 60 * 60 * 1000).toISOString(),
      readAt: Math.random() > 0.3 ? new Date(Date.now() - Math.random() * 10 * 24 * 60 * 60 * 1000).toISOString() : null,
      metadata: {
        documentId: i < 15 ? `doc-${i % 10}` : null,
        workflowId: i < 10 ? `workflow-${i % 5}` : null,
        priority: ['high', 'medium', 'low'][i % 3]
      }
    };
    
    notifications.push(notification);
  }
  
  return notifications;
}

function generateNotificationTitle(type) {
  const titles = {
    document_processed: 'Document Processing Complete',
    workflow_assigned: 'New Workflow Assignment',
    comment_added: 'New Comment Added',
    document_shared: 'Document Shared With You',
    system_update: 'System Update Available'
  };
  
  return titles[type] || 'Notification';
}

function generateNotificationMessage(type, index) {
  const messages = {
    document_processed: `Your document "Test Document ${index + 1}" has been successfully processed.`,
    workflow_assigned: `You have been assigned to a new workflow for document review.`,
    comment_added: `A new comment has been added to your document.`,
    document_shared: `A document has been shared with you by a team member.`,
    system_update: `A new system update is available with improved features.`
  };
  
  return messages[type] || 'You have a new notification.';
}

async function saveTestData(testData, testDataDir) {
  console.log('Saving test data to files...');
  
  // Save each data type to separate files
  const dataFiles = {
    'users.json': testData.users,
    'documents.json': testData.documents,
    'workflows.json': testData.workflows,
    'analytics.json': testData.analytics,
    'notifications.json': testData.notifications,
    'metadata.json': testData.metadata
  };
  
  for (const [filename, data] of Object.entries(dataFiles)) {
    const filePath = path.join(testDataDir, filename);
    fs.writeFileSync(filePath, JSON.stringify(data, null, 2));
  }
  
  // Save combined data
  const combinedFilePath = path.join(testDataDir, 'combined-test-data.json');
  fs.writeFileSync(combinedFilePath, JSON.stringify(testData, null, 2));
  
  console.log(`Test data saved to ${testDataDir}`);
}

async function initializeDatabaseWithTestData(testData) {
  console.log('Initializing database with test data...');
  
  // This would connect to the actual database and insert test data
  // For now, we'll just simulate the process
  
  try {
    // Simulated database operations
    console.log('Inserting users...');
    // await insertUsers(testData.users);
    
    console.log('Inserting documents...');
    // await insertDocuments(testData.documents);
    
    console.log('Inserting workflows...');
    // await insertWorkflows(testData.workflows);
    
    console.log('Database initialization completed');
    
  } catch (error) {
    console.error('Database initialization failed:', error);
    throw error;
  }
}

// Export functions
module.exports = {
  setupTestData,
  generateTestUsers,
  generateTestDocuments,
  generateTestWorkflows,
  generateTestAnalytics,
  generateTestNotifications
};

// If running directly, execute setup
if (require.main === module) {
  setupTestData()
    .then((testData) => {
      console.log('Test data setup completed successfully');
      console.log('Summary:');
      console.log(`- Users: ${testData.users.length}`);
      console.log(`- Documents: ${testData.documents.length}`);
      console.log(`- Workflows: ${testData.workflows.length}`);
      console.log(`- Notifications: ${testData.notifications.length}`);
      process.exit(0);
    })
    .catch((error) => {
      console.error('Test data setup failed:', error);
      process.exit(1);
    });
}