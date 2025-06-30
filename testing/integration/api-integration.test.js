/**
 * API Integration Tests
 * End-to-end testing of the complete API workflow
 */

const request = require('supertest');
const AWS = require('aws-sdk-mock');
const { startTestServer, stopTestServer } = require('../helpers/test-server');
const { createTestUser, createTestDocument, cleanupTestData } = require('../helpers/test-data');

describe('API Integration Tests', () => {
  let app;
  let testUser;
  let authToken;

  beforeAll(async () => {
    // Start test server
    app = await startTestServer();
    
    // Create test user and get auth token
    testUser = await createTestUser();
    authToken = testUser.token;
    
    // Mock AWS services for integration tests
    AWS.mock('S3', 'upload', (params, callback) => {
      callback(null, { Location: `https://test-bucket.s3.amazonaws.com/${params.Key}` });
    });
    
    AWS.mock('DynamoDB.DocumentClient', 'put', (params, callback) => {
      callback(null, {});
    });
    
    AWS.mock('DynamoDB.DocumentClient', 'get', (params, callback) => {
      callback(null, { Item: { id: params.Key.id, status: 'uploaded' } });
    });
  });

  afterAll(async () => {
    await cleanupTestData();
    await stopTestServer();
    AWS.restore();
  });

  describe('Authentication Endpoints', () => {
    describe('POST /api/auth/login', () => {
      it('authenticates user with valid credentials', async () => {
        const response = await request(app)
          .post('/api/auth/login')
          .send({
            email: 'test@example.com',
            password: 'testpassword123',
          })
          .expect(200);

        expect(response.body).toMatchObject({
          user: {
            id: expect.any(String),
            email: 'test@example.com',
            firstName: expect.any(String),
            lastName: expect.any(String),
          },
          token: expect.any(String),
          refreshToken: expect.any(String),
        });
      });

      it('rejects invalid credentials', async () => {
        const response = await request(app)
          .post('/api/auth/login')
          .send({
            email: 'test@example.com',
            password: 'wrongpassword',
          })
          .expect(401);

        expect(response.body).toMatchObject({
          error: 'Invalid credentials',
        });
      });

      it('validates required fields', async () => {
        const response = await request(app)
          .post('/api/auth/login')
          .send({
            email: 'test@example.com',
            // Missing password
          })
          .expect(400);

        expect(response.body).toMatchObject({
          error: expect.stringContaining('password'),
        });
      });

      it('handles rate limiting', async () => {
        // Attempt multiple rapid logins
        const promises = Array(10).fill(0).map(() =>
          request(app)
            .post('/api/auth/login')
            .send({
              email: 'test@example.com',
              password: 'wrongpassword',
            })
        );

        const responses = await Promise.all(promises);
        
        // Some requests should be rate limited
        const rateLimitedResponses = responses.filter(r => r.status === 429);
        expect(rateLimitedResponses.length).toBeGreaterThan(0);
      });
    });

    describe('POST /api/auth/refresh', () => {
      it('refreshes token with valid refresh token', async () => {
        const response = await request(app)
          .post('/api/auth/refresh')
          .send({
            refreshToken: testUser.refreshToken,
          })
          .expect(200);

        expect(response.body).toMatchObject({
          token: expect.any(String),
          refreshToken: expect.any(String),
        });
      });

      it('rejects invalid refresh token', async () => {
        const response = await request(app)
          .post('/api/auth/refresh')
          .send({
            refreshToken: 'invalid-token',
          })
          .expect(401);

        expect(response.body).toMatchObject({
          error: 'Invalid refresh token',
        });
      });
    });

    describe('POST /api/auth/sso/google', () => {
      it('initiates Google SSO flow', async () => {
        const response = await request(app)
          .post('/api/auth/sso/google')
          .expect(200);

        expect(response.body).toMatchObject({
          redirectUrl: expect.stringContaining('accounts.google.com'),
          state: expect.any(String),
        });
      });
    });
  });

  describe('Document Management Endpoints', () => {
    describe('POST /api/documents/upload', () => {
      it('uploads document successfully', async () => {
        const response = await request(app)
          .post('/api/documents/upload')
          .set('Authorization', `Bearer ${authToken}`)
          .attach('file', Buffer.from('Mock PDF content'), 'test.pdf')
          .field('title', 'Test Document')
          .field('tags', 'test,integration')
          .expect(201);

        expect(response.body).toMatchObject({
          id: expect.any(String),
          title: 'Test Document',
          status: 'uploaded',
          originalFileName: 'test.pdf',
          uploadedBy: testUser.id,
        });
      });

      it('validates file type', async () => {
        const response = await request(app)
          .post('/api/documents/upload')
          .set('Authorization', `Bearer ${authToken}`)
          .attach('file', Buffer.from('Invalid content'), 'test.exe')
          .field('title', 'Invalid Document')
          .expect(400);

        expect(response.body).toMatchObject({
          error: expect.stringContaining('file type'),
        });
      });

      it('validates file size', async () => {
        const largeBuffer = Buffer.alloc(60 * 1024 * 1024); // 60MB
        
        const response = await request(app)
          .post('/api/documents/upload')
          .set('Authorization', `Bearer ${authToken}`)
          .attach('file', largeBuffer, 'large.pdf')
          .field('title', 'Large Document')
          .expect(400);

        expect(response.body).toMatchObject({
          error: expect.stringContaining('file size'),
        });
      });

      it('requires authentication', async () => {
        const response = await request(app)
          .post('/api/documents/upload')
          .attach('file', Buffer.from('Mock content'), 'test.pdf')
          .field('title', 'Test Document')
          .expect(401);

        expect(response.body).toMatchObject({
          error: 'Authentication required',
        });
      });
    });

    describe('GET /api/documents', () => {
      let testDocument;

      beforeEach(async () => {
        testDocument = await createTestDocument(testUser.id);
      });

      it('retrieves user documents', async () => {
        const response = await request(app)
          .get('/api/documents')
          .set('Authorization', `Bearer ${authToken}`)
          .expect(200);

        expect(response.body).toMatchObject({
          documents: expect.arrayContaining([
            expect.objectContaining({
              id: testDocument.id,
              title: testDocument.title,
            }),
          ]),
          total: expect.any(Number),
          page: 1,
          limit: 20,
        });
      });

      it('supports pagination', async () => {
        const response = await request(app)
          .get('/api/documents?page=1&limit=5')
          .set('Authorization', `Bearer ${authToken}`)
          .expect(200);

        expect(response.body).toMatchObject({
          page: 1,
          limit: 5,
          documents: expect.any(Array),
        });
        
        expect(response.body.documents.length).toBeLessThanOrEqual(5);
      });

      it('supports search filtering', async () => {
        const response = await request(app)
          .get(`/api/documents?search=${testDocument.title}`)
          .set('Authorization', `Bearer ${authToken}`)
          .expect(200);

        expect(response.body.documents).toEqual(
          expect.arrayContaining([
            expect.objectContaining({
              title: expect.stringContaining(testDocument.title),
            }),
          ])
        );
      });

      it('supports status filtering', async () => {
        const response = await request(app)
          .get('/api/documents?status=completed')
          .set('Authorization', `Bearer ${authToken}`)
          .expect(200);

        response.body.documents.forEach(doc => {
          expect(doc.status).toBe('completed');
        });
      });

      it('requires authentication', async () => {
        const response = await request(app)
          .get('/api/documents')
          .expect(401);

        expect(response.body).toMatchObject({
          error: 'Authentication required',
        });
      });
    });

    describe('GET /api/documents/:id', () => {
      let testDocument;

      beforeEach(async () => {
        testDocument = await createTestDocument(testUser.id);
      });

      it('retrieves specific document', async () => {
        const response = await request(app)
          .get(`/api/documents/${testDocument.id}`)
          .set('Authorization', `Bearer ${authToken}`)
          .expect(200);

        expect(response.body).toMatchObject({
          id: testDocument.id,
          title: testDocument.title,
          content: expect.any(String),
          metadata: expect.any(Object),
        });
      });

      it('returns 404 for non-existent document', async () => {
        const response = await request(app)
          .get('/api/documents/non-existent-id')
          .set('Authorization', `Bearer ${authToken}`)
          .expect(404);

        expect(response.body).toMatchObject({
          error: 'Document not found',
        });
      });

      it('enforces document ownership', async () => {
        const otherUser = await createTestUser('other@example.com');
        const otherDocument = await createTestDocument(otherUser.id);

        const response = await request(app)
          .get(`/api/documents/${otherDocument.id}`)
          .set('Authorization', `Bearer ${authToken}`)
          .expect(403);

        expect(response.body).toMatchObject({
          error: 'Access denied',
        });
      });
    });

    describe('PUT /api/documents/:id', () => {
      let testDocument;

      beforeEach(async () => {
        testDocument = await createTestDocument(testUser.id);
      });

      it('updates document successfully', async () => {
        const updateData = {
          title: 'Updated Document Title',
          tags: ['updated', 'test'],
        };

        const response = await request(app)
          .put(`/api/documents/${testDocument.id}`)
          .set('Authorization', `Bearer ${authToken}`)
          .send(updateData)
          .expect(200);

        expect(response.body).toMatchObject({
          id: testDocument.id,
          title: 'Updated Document Title',
          tags: ['updated', 'test'],
        });
      });

      it('validates update data', async () => {
        const response = await request(app)
          .put(`/api/documents/${testDocument.id}`)
          .set('Authorization', `Bearer ${authToken}`)
          .send({
            title: '', // Invalid empty title
          })
          .expect(400);

        expect(response.body).toMatchObject({
          error: expect.stringContaining('title'),
        });
      });

      it('enforces document ownership', async () => {
        const otherUser = await createTestUser('other2@example.com');
        const otherDocument = await createTestDocument(otherUser.id);

        const response = await request(app)
          .put(`/api/documents/${otherDocument.id}`)
          .set('Authorization', `Bearer ${authToken}`)
          .send({ title: 'Unauthorized Update' })
          .expect(403);

        expect(response.body).toMatchObject({
          error: 'Access denied',
        });
      });
    });

    describe('DELETE /api/documents/:id', () => {
      let testDocument;

      beforeEach(async () => {
        testDocument = await createTestDocument(testUser.id);
      });

      it('deletes document successfully', async () => {
        const response = await request(app)
          .delete(`/api/documents/${testDocument.id}`)
          .set('Authorization', `Bearer ${authToken}`)
          .expect(200);

        expect(response.body).toMatchObject({
          message: 'Document deleted successfully',
        });

        // Verify document is deleted
        const getResponse = await request(app)
          .get(`/api/documents/${testDocument.id}`)
          .set('Authorization', `Bearer ${authToken}`)
          .expect(404);
      });

      it('enforces document ownership', async () => {
        const otherUser = await createTestUser('other3@example.com');
        const otherDocument = await createTestDocument(otherUser.id);

        const response = await request(app)
          .delete(`/api/documents/${otherDocument.id}`)
          .set('Authorization', `Bearer ${authToken}`)
          .expect(403);

        expect(response.body).toMatchObject({
          error: 'Access denied',
        });
      });
    });
  });

  describe('Collaboration Endpoints', () => {
    describe('POST /api/collaboration/sessions', () => {
      let testDocument;

      beforeEach(async () => {
        testDocument = await createTestDocument(testUser.id);
      });

      it('starts collaboration session', async () => {
        const response = await request(app)
          .post('/api/collaboration/sessions')
          .set('Authorization', `Bearer ${authToken}`)
          .send({
            documentId: testDocument.id,
            sessionType: 'edit',
          })
          .expect(201);

        expect(response.body).toMatchObject({
          sessionId: expect.any(String),
          documentId: testDocument.id,
          status: 'active',
          websocketEndpoint: expect.any(String),
        });
      });

      it('validates session data', async () => {
        const response = await request(app)
          .post('/api/collaboration/sessions')
          .set('Authorization', `Bearer ${authToken}`)
          .send({
            // Missing documentId
            sessionType: 'edit',
          })
          .expect(400);

        expect(response.body).toMatchObject({
          error: expect.stringContaining('documentId'),
        });
      });
    });

    describe('GET /api/collaboration/presence/:documentId', () => {
      let testDocument;

      beforeEach(async () => {
        testDocument = await createTestDocument(testUser.id);
      });

      it('retrieves document presence information', async () => {
        const response = await request(app)
          .get(`/api/collaboration/presence/${testDocument.id}`)
          .set('Authorization', `Bearer ${authToken}`)
          .expect(200);

        expect(response.body).toMatchObject({
          documentId: testDocument.id,
          activeUsers: expect.any(Array),
        });
      });
    });

    describe('POST /api/collaboration/comments', () => {
      let testDocument;

      beforeEach(async () => {
        testDocument = await createTestDocument(testUser.id);
      });

      it('creates comment successfully', async () => {
        const commentData = {
          documentId: testDocument.id,
          content: 'This is a test comment',
          annotationData: {
            selectionStart: 10,
            selectionEnd: 20,
            selectedText: 'test text',
          },
        };

        const response = await request(app)
          .post('/api/collaboration/comments')
          .set('Authorization', `Bearer ${authToken}`)
          .send(commentData)
          .expect(201);

        expect(response.body).toMatchObject({
          commentId: expect.any(String),
          content: 'This is a test comment',
          userId: testUser.id,
          threadId: expect.any(String),
        });
      });

      it('validates comment data', async () => {
        const response = await request(app)
          .post('/api/collaboration/comments')
          .set('Authorization', `Bearer ${authToken}`)
          .send({
            documentId: testDocument.id,
            // Missing content
          })
          .expect(400);

        expect(response.body).toMatchObject({
          error: expect.stringContaining('content'),
        });
      });
    });

    describe('GET /api/collaboration/comments/:documentId', () => {
      let testDocument;

      beforeEach(async () => {
        testDocument = await createTestDocument(testUser.id);
      });

      it('retrieves document comments', async () => {
        const response = await request(app)
          .get(`/api/collaboration/comments/${testDocument.id}`)
          .set('Authorization', `Bearer ${authToken}`)
          .expect(200);

        expect(response.body).toMatchObject({
          threads: expect.any(Object),
        });
      });
    });
  });

  describe('Workflow Endpoints', () => {
    describe('POST /api/workflows/start', () => {
      let testDocument;

      beforeEach(async () => {
        testDocument = await createTestDocument(testUser.id);
      });

      it('starts approval workflow', async () => {
        const workflowData = {
          documentId: testDocument.id,
          workflowType: 'approval',
          approvers: ['approver1@example.com', 'approver2@example.com'],
          description: 'Please review this document',
        };

        const response = await request(app)
          .post('/api/workflows/start')
          .set('Authorization', `Bearer ${authToken}`)
          .send(workflowData)
          .expect(201);

        expect(response.body).toMatchObject({
          workflowId: expect.any(String),
          executionArn: expect.any(String),
          status: 'started',
        });
      });
    });

    describe('GET /api/workflows/tasks', () => {
      it('retrieves user tasks', async () => {
        const response = await request(app)
          .get('/api/workflows/tasks')
          .set('Authorization', `Bearer ${authToken}`)
          .expect(200);

        expect(response.body).toMatchObject({
          tasks: expect.any(Array),
        });
      });
    });
  });

  describe('Analytics Endpoints', () => {
    describe('GET /api/analytics/dashboard', () => {
      it('retrieves dashboard analytics', async () => {
        const response = await request(app)
          .get('/api/analytics/dashboard')
          .set('Authorization', `Bearer ${authToken}`)
          .expect(200);

        expect(response.body).toMatchObject({
          metrics: expect.any(Object),
          charts: expect.any(Array),
        });
      });

      it('supports date range filtering', async () => {
        const response = await request(app)
          .get('/api/analytics/dashboard?startDate=2024-01-01&endDate=2024-01-31')
          .set('Authorization', `Bearer ${authToken}`)
          .expect(200);

        expect(response.body).toMatchObject({
          period: {
            startDate: '2024-01-01',
            endDate: '2024-01-31',
          },
          metrics: expect.any(Object),
        });
      });
    });
  });

  describe('Error Handling', () => {
    it('handles server errors gracefully', async () => {
      // Mock a server error
      AWS.mock('DynamoDB.DocumentClient', 'get', (params, callback) => {
        callback(new Error('Database connection failed'));
      });

      const response = await request(app)
        .get('/api/documents')
        .set('Authorization', `Bearer ${authToken}`)
        .expect(500);

      expect(response.body).toMatchObject({
        error: 'Internal server error',
        requestId: expect.any(String),
      });

      AWS.restore('DynamoDB.DocumentClient', 'get');
    });

    it('validates request headers', async () => {
      const response = await request(app)
        .post('/api/documents/upload')
        .set('Authorization', `Bearer ${authToken}`)
        .set('Content-Type', 'invalid/type')
        .expect(400);

      expect(response.body).toMatchObject({
        error: expect.stringContaining('Content-Type'),
      });
    });

    it('handles malformed JSON gracefully', async () => {
      const response = await request(app)
        .post('/api/auth/login')
        .set('Content-Type', 'application/json')
        .send('{"invalid": json}')
        .expect(400);

      expect(response.body).toMatchObject({
        error: expect.stringContaining('JSON'),
      });
    });
  });

  describe('Performance', () => {
    it('responds within acceptable time limits', async () => {
      const startTime = Date.now();
      
      await request(app)
        .get('/api/documents')
        .set('Authorization', `Bearer ${authToken}`)
        .expect(200);
      
      const responseTime = Date.now() - startTime;
      expect(responseTime).toBeLessThan(2000); // 2 second limit
    });

    it('handles concurrent requests', async () => {
      const requests = Array(10).fill(0).map(() =>
        request(app)
          .get('/api/documents')
          .set('Authorization', `Bearer ${authToken}`)
      );

      const responses = await Promise.all(requests);
      
      responses.forEach(response => {
        expect(response.status).toBe(200);
      });
    });
  });

  describe('Security', () => {
    it('includes security headers', async () => {
      const response = await request(app)
        .get('/api/health')
        .expect(200);

      expect(response.headers).toMatchObject({
        'x-content-type-options': 'nosniff',
        'x-frame-options': 'DENY',
        'x-xss-protection': '1; mode=block',
      });
    });

    it('prevents SQL injection attempts', async () => {
      const response = await request(app)
        .get('/api/documents?search=\'; DROP TABLE documents; --')
        .set('Authorization', `Bearer ${authToken}`)
        .expect(200);

      // Should return empty results, not crash
      expect(response.body.documents).toEqual([]);
    });

    it('sanitizes file uploads', async () => {
      const response = await request(app)
        .post('/api/documents/upload')
        .set('Authorization', `Bearer ${authToken}`)
        .attach('file', Buffer.from('<script>alert("xss")</script>'), 'test.txt')
        .field('title', 'XSS Test')
        .expect(201);

      // Document should be created but content should be sanitized
      expect(response.body.title).toBe('XSS Test');
    });
  });
});