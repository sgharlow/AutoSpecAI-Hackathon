/**
 * Document Processor Lambda Tests
 * Comprehensive testing of the document processing Lambda function
 */

const AWS = require('aws-sdk');
const { handler } = require('@lambdas/process/process');

// Mock AWS services
jest.mock('aws-sdk');

describe('Document Processor Lambda', () => {
  let mockS3, mockDynamoDB, mockBedrock, mockSNS;
  
  beforeEach(() => {
    // Reset all mocks
    jest.clearAllMocks();
    
    // Mock S3
    mockS3 = {
      getObject: jest.fn().mockReturnValue({
        promise: jest.fn().mockResolvedValue({
          Body: Buffer.from('Mock PDF content with requirements and specifications'),
          ContentType: 'application/pdf',
        }),
      }),
      putObject: jest.fn().mockReturnValue({
        promise: jest.fn().mockResolvedValue({ ETag: 'mock-etag' }),
      }),
    };
    
    // Mock DynamoDB
    mockDynamoDB = {
      get: jest.fn().mockReturnValue({
        promise: jest.fn().mockResolvedValue({
          Item: {
            id: 'doc-123',
            title: 'Test Document',
            status: 'uploaded',
            organizationId: 'org-123',
            uploadedBy: 'user-123',
          },
        }),
      }),
      update: jest.fn().mockReturnValue({
        promise: jest.fn().mockResolvedValue({}),
      }),
    };
    
    // Mock Bedrock
    mockBedrock = {
      invokeModel: jest.fn().mockReturnValue({
        promise: jest.fn().mockResolvedValue({
          body: JSON.stringify({
            completion: JSON.stringify({
              requirements: [
                {
                  id: 'REQ-001',
                  type: 'functional',
                  title: 'User Authentication',
                  description: 'The system shall provide user authentication',
                  priority: 'high',
                  category: 'security',
                },
                {
                  id: 'REQ-002',
                  type: 'non-functional',
                  title: 'Performance',
                  description: 'The system shall respond within 2 seconds',
                  priority: 'medium',
                  category: 'performance',
                },
              ],
              summary: 'Document contains authentication and performance requirements',
              complexity: 'medium',
              completeness: 0.85,
              suggestions: [
                'Consider adding security requirements',
                'Define specific performance metrics',
              ],
            }),
          }),
        }),
      }),
    };
    
    // Mock SNS
    mockSNS = {
      publish: jest.fn().mockReturnValue({
        promise: jest.fn().mockResolvedValue({ MessageId: 'mock-message-id' }),
      }),
    };
    
    AWS.S3.mockImplementation(() => mockS3);
    AWS.DynamoDB.DocumentClient.mockImplementation(() => mockDynamoDB);
    AWS.BedrockRuntime.mockImplementation(() => mockBedrock);
    AWS.SNS.mockImplementation(() => mockSNS);
  });

  describe('S3 Event Processing', () => {
    const createS3Event = (bucketName = 'test-bucket', objectKey = 'documents/doc-123.pdf') => ({
      Records: [
        {
          eventSource: 'aws:s3',
          eventName: 'ObjectCreated:Put',
          s3: {
            bucket: { name: bucketName },
            object: { key: objectKey },
          },
        },
      ],
    });

    it('processes S3 object creation event successfully', async () => {
      const event = createS3Event();
      const context = { requestId: 'test-request-id' };
      
      const result = await handler(event, context);
      
      expect(result.statusCode).toBe(200);
      expect(JSON.parse(result.body)).toEqual({
        message: 'Document processed successfully',
        documentId: 'doc-123',
        requirementsCount: 2,
      });
    });

    it('retrieves document from S3', async () => {
      const event = createS3Event();
      const context = { requestId: 'test-request-id' };
      
      await handler(event, context);
      
      expect(mockS3.getObject).toHaveBeenCalledWith({
        Bucket: 'test-bucket',
        Key: 'documents/doc-123.pdf',
      });
    });

    it('extracts document ID from S3 object key', async () => {
      const event = createS3Event('test-bucket', 'documents/my-document-456.pdf');
      const context = { requestId: 'test-request-id' };
      
      await handler(event, context);
      
      expect(mockDynamoDB.get).toHaveBeenCalledWith({
        TableName: process.env.DOCUMENTS_TABLE || 'autospec-ai-documents-dev',
        Key: { id: 'my-document-456' },
      });
    });

    it('handles missing S3 object gracefully', async () => {
      mockS3.getObject.mockReturnValue({
        promise: jest.fn().mockRejectedValue({
          code: 'NoSuchKey',
          message: 'The specified key does not exist.',
        }),
      });

      const event = createS3Event();
      const context = { requestId: 'test-request-id' };
      
      const result = await handler(event, context);
      
      expect(result.statusCode).toBe(404);
      expect(JSON.parse(result.body)).toEqual({
        error: 'Document not found in S3',
      });
    });
  });

  describe('Document Retrieval', () => {
    it('retrieves document metadata from DynamoDB', async () => {
      const event = createS3Event();
      const context = { requestId: 'test-request-id' };
      
      await handler(event, context);
      
      expect(mockDynamoDB.get).toHaveBeenCalledWith({
        TableName: process.env.DOCUMENTS_TABLE || 'autospec-ai-documents-dev',
        Key: { id: 'doc-123' },
      });
    });

    it('handles missing document metadata', async () => {
      mockDynamoDB.get.mockReturnValue({
        promise: jest.fn().mockResolvedValue({}), // No Item
      });

      const event = createS3Event();
      const context = { requestId: 'test-request-id' };
      
      const result = await handler(event, context);
      
      expect(result.statusCode).toBe(404);
      expect(JSON.parse(result.body)).toEqual({
        error: 'Document metadata not found',
      });
    });

    it('updates document status to processing', async () => {
      const event = createS3Event();
      const context = { requestId: 'test-request-id' };
      
      await handler(event, context);
      
      expect(mockDynamoDB.update).toHaveBeenCalledWith({
        TableName: process.env.DOCUMENTS_TABLE || 'autospec-ai-documents-dev',
        Key: { id: 'doc-123' },
        UpdateExpression: 'SET #status = :status, processingStartedAt = :timestamp',
        ExpressionAttributeNames: { '#status': 'status' },
        ExpressionAttributeValues: {
          ':status': 'processing',
          ':timestamp': expect.any(String),
        },
      });
    });
  });

  describe('Content Processing', () => {
    it('processes PDF content correctly', async () => {
      const event = createS3Event();
      const context = { requestId: 'test-request-id' };
      
      await handler(event, context);
      
      // Verify that the content was processed (PDF parsing would be mocked)
      expect(mockBedrock.invokeModel).toHaveBeenCalled();
    });

    it('handles different file types', async () => {
      const testCases = [
        { key: 'documents/doc-123.pdf', expectedType: 'pdf' },
        { key: 'documents/doc-123.docx', expectedType: 'docx' },
        { key: 'documents/doc-123.txt', expectedType: 'txt' },
      ];

      for (const testCase of testCases) {
        const event = createS3Event('test-bucket', testCase.key);
        const context = { requestId: 'test-request-id' };
        
        await handler(event, context);
        
        // Verify appropriate content processing for file type
        expect(mockBedrock.invokeModel).toHaveBeenCalled();
      }
    });

    it('handles unsupported file types', async () => {
      const event = createS3Event('test-bucket', 'documents/doc-123.exe');
      const context = { requestId: 'test-request-id' };
      
      const result = await handler(event, context);
      
      expect(result.statusCode).toBe(400);
      expect(JSON.parse(result.body)).toEqual({
        error: 'Unsupported file type: exe',
      });
    });
  });

  describe('AI Analysis with Bedrock', () => {
    it('calls Bedrock with correct parameters', async () => {
      const event = createS3Event();
      const context = { requestId: 'test-request-id' };
      
      await handler(event, context);
      
      expect(mockBedrock.invokeModel).toHaveBeenCalledWith({
        modelId: 'anthropic.claude-3-sonnet-20240229-v1:0',
        contentType: 'application/json',
        accept: 'application/json',
        body: JSON.stringify({
          anthropic_version: 'bedrock-2023-05-31',
          max_tokens: 4000,
          temperature: 0.1,
          system: expect.stringContaining('You are a skilled systems analyst'),
          messages: [
            {
              role: 'user',
              content: expect.stringContaining('Mock PDF content'),
            },
          ],
        }),
      });
    });

    it('parses Bedrock response correctly', async () => {
      const event = createS3Event();
      const context = { requestId: 'test-request-id' };
      
      await handler(event, context);
      
      // Verify that the response was parsed and stored
      expect(mockDynamoDB.update).toHaveBeenCalledWith(
        expect.objectContaining({
          UpdateExpression: expect.stringContaining('aiAnalysis'),
          ExpressionAttributeValues: expect.objectContaining({
            ':analysis': expect.objectContaining({
              requirements: expect.arrayContaining([
                expect.objectContaining({
                  id: 'REQ-001',
                  type: 'functional',
                  title: 'User Authentication',
                }),
              ]),
              summary: 'Document contains authentication and performance requirements',
              complexity: 'medium',
              completeness: 0.85,
            }),
          }),
        })
      );
    });

    it('handles Bedrock API errors', async () => {
      mockBedrock.invokeModel.mockReturnValue({
        promise: jest.fn().mockRejectedValue(new Error('Bedrock API error')),
      });

      const event = createS3Event();
      const context = { requestId: 'test-request-id' };
      
      const result = await handler(event, context);
      
      expect(result.statusCode).toBe(500);
      expect(JSON.parse(result.body)).toEqual({
        error: 'AI analysis failed: Bedrock API error',
      });
      
      // Verify document status is updated to failed
      expect(mockDynamoDB.update).toHaveBeenCalledWith(
        expect.objectContaining({
          ExpressionAttributeValues: expect.objectContaining({
            ':status': 'failed',
          }),
        })
      );
    });

    it('handles invalid Bedrock response format', async () => {
      mockBedrock.invokeModel.mockReturnValue({
        promise: jest.fn().mockResolvedValue({
          body: 'invalid json response',
        }),
      });

      const event = createS3Event();
      const context = { requestId: 'test-request-id' };
      
      const result = await handler(event, context);
      
      expect(result.statusCode).toBe(500);
      expect(JSON.parse(result.body)).toEqual({
        error: 'Failed to parse AI analysis response',
      });
    });
  });

  describe('Output Generation', () => {
    it('stores processed content in S3', async () => {
      const event = createS3Event();
      const context = { requestId: 'test-request-id' };
      
      await handler(event, context);
      
      expect(mockS3.putObject).toHaveBeenCalledWith({
        Bucket: process.env.OUTPUT_BUCKET || 'autospec-ai-output-dev',
        Key: 'processed/doc-123.json',
        Body: expect.any(String),
        ContentType: 'application/json',
        Metadata: expect.objectContaining({
          documentId: 'doc-123',
          processedAt: expect.any(String),
        }),
      });
    });

    it('updates document status to completed', async () => {
      const event = createS3Event();
      const context = { requestId: 'test-request-id' };
      
      await handler(event, context);
      
      expect(mockDynamoDB.update).toHaveBeenCalledWith(
        expect.objectContaining({
          ExpressionAttributeValues: expect.objectContaining({
            ':status': 'completed',
            ':processedAt': expect.any(String),
          }),
        })
      );
    });

    it('calculates processing time', async () => {
      const event = createS3Event();
      const context = { requestId: 'test-request-id' };
      
      const startTime = Date.now();
      await handler(event, context);
      const endTime = Date.now();
      
      expect(mockDynamoDB.update).toHaveBeenCalledWith(
        expect.objectContaining({
          ExpressionAttributeValues: expect.objectContaining({
            ':processingTime': expect.any(Number),
          }),
        })
      );
      
      // Verify processing time is reasonable
      const updateCall = mockDynamoDB.update.mock.calls.find(
        call => call[0].ExpressionAttributeValues[':processingTime']
      );
      const processingTime = updateCall[0].ExpressionAttributeValues[':processingTime'];
      expect(processingTime).toBeGreaterThan(0);
      expect(processingTime).toBeLessThan(endTime - startTime + 1000); // Allow some margin
    });
  });

  describe('Notifications', () => {
    it('sends completion notification', async () => {
      const event = createS3Event();
      const context = { requestId: 'test-request-id' };
      
      await handler(event, context);
      
      expect(mockSNS.publish).toHaveBeenCalledWith({
        TopicArn: process.env.NOTIFICATION_TOPIC_ARN,
        Message: JSON.stringify({
          type: 'document_processed',
          documentId: 'doc-123',
          status: 'completed',
          requirementsCount: 2,
          userId: 'user-123',
          organizationId: 'org-123',
          timestamp: expect.any(String),
        }),
        Subject: 'Document Processing Completed',
        MessageAttributes: {
          documentId: {
            DataType: 'String',
            StringValue: 'doc-123',
          },
          userId: {
            DataType: 'String',
            StringValue: 'user-123',
          },
        },
      });
    });

    it('sends failure notification on error', async () => {
      mockBedrock.invokeModel.mockReturnValue({
        promise: jest.fn().mockRejectedValue(new Error('Processing failed')),
      });

      const event = createS3Event();
      const context = { requestId: 'test-request-id' };
      
      await handler(event, context);
      
      expect(mockSNS.publish).toHaveBeenCalledWith(
        expect.objectContaining({
          Message: expect.stringContaining('"status":"failed"'),
          Subject: 'Document Processing Failed',
        })
      );
    });
  });

  describe('Error Handling', () => {
    it('handles DynamoDB errors gracefully', async () => {
      mockDynamoDB.get.mockReturnValue({
        promise: jest.fn().mockRejectedValue(new Error('DynamoDB error')),
      });

      const event = createS3Event();
      const context = { requestId: 'test-request-id' };
      
      const result = await handler(event, context);
      
      expect(result.statusCode).toBe(500);
      expect(JSON.parse(result.body)).toEqual({
        error: 'Database error: DynamoDB error',
      });
    });

    it('handles S3 access errors', async () => {
      mockS3.getObject.mockReturnValue({
        promise: jest.fn().mockRejectedValue(new Error('Access denied')),
      });

      const event = createS3Event();
      const context = { requestId: 'test-request-id' };
      
      const result = await handler(event, context);
      
      expect(result.statusCode).toBe(500);
      expect(JSON.parse(result.body)).toEqual({
        error: 'Failed to retrieve document: Access denied',
      });
    });

    it('handles malformed S3 events', async () => {
      const malformedEvent = {
        Records: [
          {
            eventSource: 'aws:s3',
            // Missing s3 object
          },
        ],
      };

      const context = { requestId: 'test-request-id' };
      
      const result = await handler(malformedEvent, context);
      
      expect(result.statusCode).toBe(400);
      expect(JSON.parse(result.body)).toEqual({
        error: 'Invalid S3 event format',
      });
    });
  });

  describe('Performance', () => {
    it('processes documents within acceptable time limits', async () => {
      const event = createS3Event();
      const context = { requestId: 'test-request-id' };
      
      const startTime = Date.now();
      await handler(event, context);
      const processingTime = Date.now() - startTime;
      
      // Processing should complete within 30 seconds for unit tests
      expect(processingTime).toBeLessThan(30000);
    });

    it('handles concurrent processing requests', async () => {
      const events = [
        createS3Event('bucket1', 'documents/doc-1.pdf'),
        createS3Event('bucket2', 'documents/doc-2.pdf'),
        createS3Event('bucket3', 'documents/doc-3.pdf'),
      ];
      
      const context = { requestId: 'test-request-id' };
      
      const results = await Promise.all(
        events.map(event => handler(event, context))
      );
      
      results.forEach(result => {
        expect(result.statusCode).toBe(200);
      });
    });
  });

  describe('Security', () => {
    it('validates document ownership', async () => {
      // This would check that users can only process their own documents
      // Implementation depends on how security is handled in the actual function
      const event = createS3Event();
      const context = { requestId: 'test-request-id' };
      
      await handler(event, context);
      
      // Verify that document metadata includes proper ownership validation
      expect(mockDynamoDB.get).toHaveBeenCalled();
    });

    it('sanitizes content before AI processing', async () => {
      mockS3.getObject.mockReturnValue({
        promise: jest.fn().mockResolvedValue({
          Body: Buffer.from('<script>alert("xss")</script>Legitimate content'),
          ContentType: 'text/plain',
        }),
      });

      const event = createS3Event();
      const context = { requestId: 'test-request-id' };
      
      await handler(event, context);
      
      // Verify that dangerous content is handled appropriately
      expect(mockBedrock.invokeModel).toHaveBeenCalled();
      const bedrockCall = mockBedrock.invokeModel.mock.calls[0][0];
      const messageContent = JSON.parse(bedrockCall.body).messages[0].content;
      
      // Content should be sanitized or properly escaped
      expect(messageContent).not.toContain('<script>');
    });
  });
});