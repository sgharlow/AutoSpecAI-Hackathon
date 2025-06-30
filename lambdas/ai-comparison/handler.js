/**
 * AI-Powered Document Comparison Lambda
 * Performs sophisticated document comparison using Amazon Bedrock and semantic analysis
 */

const AWS = require('aws-sdk');
const { v4: uuidv4 } = require('uuid');

// Initialize AWS services
const bedrock = new AWS.BedrockRuntime({ region: process.env.AWS_REGION || 'us-east-1' });
const s3 = new AWS.S3();
const dynamodb = new AWS.DynamoDB.DocumentClient();
const sns = new AWS.SNS();

// Configuration
const CONFIG = {
  BUCKET_NAME: process.env.DOCUMENTS_BUCKET,
  COMPARISONS_TABLE: process.env.COMPARISONS_TABLE || 'autospec-ai-comparisons',
  NOTIFICATIONS_TOPIC: process.env.NOTIFICATIONS_TOPIC,
  MAX_DOCUMENT_SIZE: 50 * 1024 * 1024, // 50MB
  SIMILARITY_THRESHOLD: 0.7,
  BEDROCK_MODEL_ID: 'anthropic.claude-3-sonnet-20240229-v1:0'
};

/**
 * Main Lambda handler for document comparison
 */
exports.handler = async (event, context) => {
  console.log('AI Document Comparison - Event:', JSON.stringify(event, null, 2));
  
  try {
    // Handle different event sources
    if (event.Records) {
      // SNS/SQS triggered comparison
      return await handleQueuedComparison(event);
    } else if (event.httpMethod) {
      // API Gateway triggered comparison
      return await handleAPIComparison(event, context);
    } else {
      // Direct invocation
      return await performDocumentComparison(event);
    }
  } catch (error) {
    console.error('Document comparison failed:', error);
    
    return {
      statusCode: 500,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*'
      },
      body: JSON.stringify({
        error: 'Document comparison failed',
        message: error.message,
        requestId: context.awsRequestId
      })
    };
  }
};

/**
 * Handle API Gateway triggered comparison requests
 */
async function handleAPIComparison(event, context) {
  const { httpMethod, pathParameters, body } = event;
  
  switch (httpMethod) {
    case 'POST':
      if (pathParameters && pathParameters.action === 'compare') {
        return await startComparison(JSON.parse(body || '{}'), context);
      }
      break;
      
    case 'GET':
      if (pathParameters && pathParameters.comparisonId) {
        return await getComparisonResult(pathParameters.comparisonId);
      } else {
        return await listComparisons(event.queryStringParameters || {});
      }
      break;
      
    case 'DELETE':
      if (pathParameters && pathParameters.comparisonId) {
        return await deleteComparison(pathParameters.comparisonId);
      }
      break;
      
    default:
      return {
        statusCode: 405,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ error: 'Method not allowed' })
      };
  }
}

/**
 * Start a new document comparison
 */
async function startComparison(requestBody, context) {
  const { sourceDocumentId, targetDocumentId, comparisonType = 'full', options = {} } = requestBody;
  
  if (!sourceDocumentId || !targetDocumentId) {
    return {
      statusCode: 400,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        error: 'Missing required parameters',
        message: 'Both sourceDocumentId and targetDocumentId are required'
      })
    };
  }
  
  const comparisonId = uuidv4();
  const timestamp = new Date().toISOString();
  
  // Create comparison record
  const comparisonRecord = {
    id: comparisonId,
    sourceDocumentId,
    targetDocumentId,
    comparisonType,
    options,
    status: 'processing',
    createdAt: timestamp,
    updatedAt: timestamp,
    requestId: context.awsRequestId
  };
  
  try {
    // Save initial comparison record
    await dynamodb.put({
      TableName: CONFIG.COMPARISONS_TABLE,
      Item: comparisonRecord
    }).promise();
    
    // Start async comparison process
    const comparisonParams = {
      comparisonId,
      sourceDocumentId,
      targetDocumentId,
      comparisonType,
      options
    };
    
    // Invoke comparison process asynchronously
    await performDocumentComparison(comparisonParams);
    
    return {
      statusCode: 202,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        comparisonId,
        status: 'processing',
        message: 'Document comparison started',
        estimatedCompletionTime: new Date(Date.now() + 2 * 60 * 1000).toISOString() // 2 minutes
      })
    };
    
  } catch (error) {
    console.error('Failed to start comparison:', error);
    throw error;
  }
}

/**
 * Perform the actual document comparison
 */
async function performDocumentComparison(params) {
  const { comparisonId, sourceDocumentId, targetDocumentId, comparisonType, options } = params;
  
  console.log(`Starting comparison ${comparisonId}: ${sourceDocumentId} vs ${targetDocumentId}`);
  
  try {
    // Update status to processing
    await updateComparisonStatus(comparisonId, 'processing', { step: 'loading_documents' });
    
    // Load source and target documents
    const [sourceDoc, targetDoc] = await Promise.all([
      loadDocument(sourceDocumentId),
      loadDocument(targetDocumentId)
    ]);
    
    await updateComparisonStatus(comparisonId, 'processing', { step: 'extracting_content' });
    
    // Extract content and metadata
    const sourceContent = await extractDocumentContent(sourceDoc);
    const targetContent = await extractDocumentContent(targetDoc);
    
    await updateComparisonStatus(comparisonId, 'processing', { step: 'analyzing_structure' });
    
    // Perform structural analysis
    const structuralComparison = await performStructuralComparison(sourceContent, targetContent);
    
    await updateComparisonStatus(comparisonId, 'processing', { step: 'analyzing_semantics' });
    
    // Perform semantic analysis using Bedrock
    const semanticComparison = await performSemanticComparison(sourceContent, targetContent, options);
    
    await updateComparisonStatus(comparisonId, 'processing', { step: 'analyzing_requirements' });
    
    // Perform requirements comparison
    const requirementsComparison = await performRequirementsComparison(sourceContent, targetContent);
    
    await updateComparisonStatus(comparisonId, 'processing', { step: 'generating_insights' });
    
    // Generate AI insights and recommendations
    const insights = await generateComparisonInsights({
      sourceDoc,
      targetDoc,
      structuralComparison,
      semanticComparison,
      requirementsComparison
    });
    
    // Compile final results
    const comparisonResult = {
      comparisonId,
      sourceDocument: {
        id: sourceDocumentId,
        title: sourceDoc.title,
        type: sourceDoc.type,
        size: sourceDoc.size
      },
      targetDocument: {
        id: targetDocumentId,
        title: targetDoc.title,
        type: targetDoc.type,
        size: targetDoc.size
      },
      comparisonType,
      results: {
        overallSimilarity: calculateOverallSimilarity(structuralComparison, semanticComparison),
        structural: structuralComparison,
        semantic: semanticComparison,
        requirements: requirementsComparison,
        insights,
        summary: generateComparisonSummary(structuralComparison, semanticComparison, requirementsComparison)
      },
      metadata: {
        processingTime: Date.now() - new Date(params.startTime || Date.now()).getTime(),
        bedrockModel: CONFIG.BEDROCK_MODEL_ID,
        version: '1.0.0'
      }
    };
    
    // Save final results
    await updateComparisonStatus(comparisonId, 'completed', {
      results: comparisonResult,
      completedAt: new Date().toISOString()
    });
    
    // Send notification if configured
    if (CONFIG.NOTIFICATIONS_TOPIC) {
      await sendComparisonNotification(comparisonResult);
    }
    
    console.log(`Comparison ${comparisonId} completed successfully`);
    return comparisonResult;
    
  } catch (error) {
    console.error(`Comparison ${comparisonId} failed:`, error);
    
    await updateComparisonStatus(comparisonId, 'failed', {
      error: error.message,
      failedAt: new Date().toISOString()
    });
    
    throw error;
  }
}

/**
 * Load document from S3 and DynamoDB
 */
async function loadDocument(documentId) {
  try {
    // Get document metadata from DynamoDB
    const docResult = await dynamodb.get({
      TableName: process.env.DOCUMENTS_TABLE || 'autospec-ai-documents',
      Key: { id: documentId }
    }).promise();
    
    if (!docResult.Item) {
      throw new Error(`Document ${documentId} not found`);
    }
    
    const document = docResult.Item;
    
    // Load document content from S3
    if (document.s3Key) {
      const s3Object = await s3.getObject({
        Bucket: CONFIG.BUCKET_NAME,
        Key: document.s3Key
      }).promise();
      
      document.rawContent = s3Object.Body;
    }
    
    return document;
    
  } catch (error) {
    console.error(`Failed to load document ${documentId}:`, error);
    throw new Error(`Failed to load document: ${error.message}`);
  }
}

/**
 * Extract structured content from document
 */
async function extractDocumentContent(document) {
  const content = {
    id: document.id,
    title: document.title,
    type: document.type,
    text: document.processedContent || document.content || '',
    structure: {
      sections: [],
      paragraphs: [],
      lists: [],
      tables: []
    },
    requirements: document.requirements || [],
    metadata: {
      wordCount: 0,
      pageCount: document.pageCount || 1,
      language: document.language || 'en',
      createdAt: document.createdAt,
      updatedAt: document.updatedAt
    }
  };
  
  // Parse document structure
  if (content.text) {
    content.structure = parseDocumentStructure(content.text);
    content.metadata.wordCount = content.text.split(/\s+/).length;
  }
  
  return content;
}

/**
 * Parse document structure from text
 */
function parseDocumentStructure(text) {
  const structure = {
    sections: [],
    paragraphs: [],
    lists: [],
    tables: []
  };
  
  const lines = text.split('\n');
  let currentSection = null;
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    
    if (!line) continue;
    
    // Detect sections (headers)
    if (line.match(/^#+\s/) || line.match(/^\d+\.\s+[A-Z]/) || line.toUpperCase() === line && line.length < 100) {
      currentSection = {
        title: line.replace(/^#+\s*/, '').replace(/^\d+\.\s*/, ''),
        level: (line.match(/^#+/) || [''])[0].length || 1,
        startLine: i,
        content: []
      };
      structure.sections.push(currentSection);
    }
    // Detect lists
    else if (line.match(/^[-*+]\s/) || line.match(/^\d+\.\s/)) {
      const listMatch = line.match(/^([-*+]|\d+\.)\s(.+)/);
      if (listMatch) {
        structure.lists.push({
          type: listMatch[1].match(/\d/) ? 'ordered' : 'unordered',
          item: listMatch[2],
          line: i
        });
      }
    }
    // Detect tables (simple heuristic)
    else if (line.includes('|') && line.split('|').length > 2) {
      structure.tables.push({
        content: line,
        line: i,
        columns: line.split('|').length - 2
      });
    }
    // Regular paragraphs
    else {
      structure.paragraphs.push({
        content: line,
        line: i,
        wordCount: line.split(/\s+/).length
      });
      
      if (currentSection) {
        currentSection.content.push(line);
      }
    }
  }
  
  return structure;
}

/**
 * Perform structural comparison between documents
 */
async function performStructuralComparison(sourceContent, targetContent) {
  const comparison = {
    documentStructure: {
      sectionsComparison: compareSections(sourceContent.structure.sections, targetContent.structure.sections),
      organizationSimilarity: calculateStructuralSimilarity(sourceContent.structure, targetContent.structure)
    },
    contentMetrics: {
      wordCountDifference: targetContent.metadata.wordCount - sourceContent.metadata.wordCount,
      wordCountRatio: targetContent.metadata.wordCount / (sourceContent.metadata.wordCount || 1),
      structuralDifferences: identifyStructuralDifferences(sourceContent.structure, targetContent.structure)
    },
    textualChanges: {
      addedSections: [],
      removedSections: [],
      modifiedSections: [],
      similarityScore: 0
    }
  };
  
  // Calculate textual similarity using simple algorithms
  comparison.textualChanges.similarityScore = calculateTextSimilarity(sourceContent.text, targetContent.text);
  
  // Identify section changes
  const { added, removed, modified } = compareSectionContent(sourceContent.structure.sections, targetContent.structure.sections);
  comparison.textualChanges.addedSections = added;
  comparison.textualChanges.removedSections = removed;
  comparison.textualChanges.modifiedSections = modified;
  
  return comparison;
}

/**
 * Perform semantic comparison using Amazon Bedrock
 */
async function performSemanticComparison(sourceContent, targetContent, options = {}) {
  const prompt = `
As an expert document analyst, compare these two documents for semantic similarity and differences.

Document 1 (Source):
Title: ${sourceContent.title}
Content: ${sourceContent.text.substring(0, 10000)}...

Document 2 (Target):
Title: ${targetContent.title}
Content: ${targetContent.text.substring(0, 10000)}...

Provide a comprehensive semantic analysis in JSON format with the following structure:
{
  "semanticSimilarity": {
    "overallScore": 0.85,
    "thematicAlignment": 0.90,
    "conceptualOverlap": 0.80,
    "terminologyConsistency": 0.85
  },
  "keyDifferences": [
    {
      "category": "scope",
      "description": "Document 2 has broader scope including mobile requirements",
      "impact": "medium"
    }
  ],
  "sharedConcepts": [
    {
      "concept": "user authentication",
      "sourceReferences": ["section 2.1"],
      "targetReferences": ["section 3.2"],
      "similarity": 0.95
    }
  ],
  "uniqueElements": {
    "sourceOnly": [
      {
        "element": "legacy system integration",
        "description": "Detailed requirements for legacy system compatibility"
      }
    ],
    "targetOnly": [
      {
        "element": "mobile application",
        "description": "Mobile-specific requirements and constraints"
      }
    ]
  },
  "recommendations": [
    {
      "type": "alignment",
      "description": "Consider harmonizing terminology across both documents",
      "priority": "medium"
    }
  ]
}

Focus on meaningful semantic differences, not just textual variations.
`;
  
  try {
    const response = await bedrock.invokeModel({
      modelId: CONFIG.BEDROCK_MODEL_ID,
      contentType: 'application/json',
      accept: 'application/json',
      body: JSON.stringify({
        anthropic_version: 'bedrock-2023-05-31',
        max_tokens: 4000,
        messages: [{
          role: 'user',
          content: prompt
        }]
      })
    }).promise();
    
    const responseBody = JSON.parse(response.body.toString());
    const analysisText = responseBody.content[0].text;
    
    // Extract JSON from the response
    const jsonMatch = analysisText.match(/\{[\s\S]*\}/);
    if (jsonMatch) {
      return JSON.parse(jsonMatch[0]);
    } else {
      throw new Error('Invalid JSON response from Bedrock');
    }
    
  } catch (error) {
    console.error('Semantic comparison failed:', error);
    
    // Fallback to basic semantic analysis
    return {
      semanticSimilarity: {
        overallScore: calculateTextSimilarity(sourceContent.text, targetContent.text),
        thematicAlignment: 0.5,
        conceptualOverlap: 0.5,
        terminologyConsistency: 0.5
      },
      keyDifferences: [],
      sharedConcepts: [],
      uniqueElements: { sourceOnly: [], targetOnly: [] },
      recommendations: [{
        type: 'error',
        description: 'Semantic analysis failed, using basic comparison',
        priority: 'high'
      }],
      error: error.message
    };
  }
}

/**
 * Perform requirements-specific comparison
 */
async function performRequirementsComparison(sourceContent, targetContent) {
  const sourceReqs = sourceContent.requirements || [];
  const targetReqs = targetContent.requirements || [];
  
  const comparison = {
    statistics: {
      sourceCount: sourceReqs.length,
      targetCount: targetReqs.length,
      netChange: targetReqs.length - sourceReqs.length
    },
    matching: {
      exact: [],
      similar: [],
      modified: []
    },
    changes: {
      added: [],
      removed: [],
      updated: []
    },
    coverage: {
      functional: {
        source: sourceReqs.filter(r => r.type === 'functional').length,
        target: targetReqs.filter(r => r.type === 'functional').length
      },
      nonFunctional: {
        source: sourceReqs.filter(r => r.type === 'non-functional').length,
        target: targetReqs.filter(r => r.type === 'non-functional').length
      }
    }
  };
  
  // Compare requirements
  for (const sourceReq of sourceReqs) {
    let bestMatch = null;
    let bestSimilarity = 0;
    
    for (const targetReq of targetReqs) {
      const similarity = calculateTextSimilarity(sourceReq.description || sourceReq.text, targetReq.description || targetReq.text);
      
      if (similarity > bestSimilarity) {
        bestSimilarity = similarity;
        bestMatch = targetReq;
      }
    }
    
    if (bestSimilarity > 0.9) {
      comparison.matching.exact.push({ source: sourceReq, target: bestMatch, similarity: bestSimilarity });
    } else if (bestSimilarity > 0.7) {
      comparison.matching.similar.push({ source: sourceReq, target: bestMatch, similarity: bestSimilarity });
    } else if (bestSimilarity > 0.5) {
      comparison.matching.modified.push({ source: sourceReq, target: bestMatch, similarity: bestSimilarity });
    } else {
      comparison.changes.removed.push(sourceReq);
    }
  }
  
  // Find added requirements
  const matchedTargetIds = new Set([
    ...comparison.matching.exact.map(m => m.target.id),
    ...comparison.matching.similar.map(m => m.target.id),
    ...comparison.matching.modified.map(m => m.target.id)
  ]);
  
  comparison.changes.added = targetReqs.filter(req => !matchedTargetIds.has(req.id));
  
  return comparison;
}

/**
 * Generate AI insights and recommendations
 */
async function generateComparisonInsights(comparisonData) {
  const { sourceDoc, targetDoc, structuralComparison, semanticComparison, requirementsComparison } = comparisonData;
  
  const insights = {
    keyFindings: [],
    recommendations: [],
    riskAssessment: {
      level: 'low',
      factors: []
    },
    actionItems: [],
    qualityMetrics: {
      completeness: 0,
      consistency: 0,
      clarity: 0
    }
  };
  
  // Analyze structural changes
  if (structuralComparison.documentStructure.organizationSimilarity < 0.7) {
    insights.keyFindings.push({
      type: 'structural',
      description: 'Significant structural reorganization detected',
      impact: 'medium',
      details: `Document organization similarity: ${(structuralComparison.documentStructure.organizationSimilarity * 100).toFixed(1)}%`
    });
  }
  
  // Analyze semantic changes
  if (semanticComparison.semanticSimilarity?.overallScore < 0.8) {
    insights.keyFindings.push({
      type: 'semantic',
      description: 'Substantial semantic changes identified',
      impact: 'high',
      details: `Semantic similarity: ${(semanticComparison.semanticSimilarity.overallScore * 100).toFixed(1)}%`
    });
    
    insights.riskAssessment.level = 'medium';
    insights.riskAssessment.factors.push('Significant semantic divergence');
  }
  
  // Analyze requirements changes
  const reqChangeRatio = Math.abs(requirementsComparison.statistics.netChange) / (requirementsComparison.statistics.sourceCount || 1);
  if (reqChangeRatio > 0.2) {
    insights.keyFindings.push({
      type: 'requirements',
      description: 'Major requirements changes detected',
      impact: 'high',
      details: `${requirementsComparison.statistics.netChange > 0 ? 'Added' : 'Removed'} ${Math.abs(requirementsComparison.statistics.netChange)} requirements`
    });
    
    if (insights.riskAssessment.level === 'low') {
      insights.riskAssessment.level = 'medium';
    }
    insights.riskAssessment.factors.push('Significant requirements changes');
  }
  
  // Generate recommendations
  if (semanticComparison.recommendations) {
    insights.recommendations.push(...semanticComparison.recommendations);
  }
  
  // Quality metrics calculation
  insights.qualityMetrics.completeness = calculateCompletenessScore(requirementsComparison);
  insights.qualityMetrics.consistency = semanticComparison.semanticSimilarity?.terminologyConsistency || 0.5;
  insights.qualityMetrics.clarity = calculateClarityScore(structuralComparison);
  
  return insights;
}

/**
 * Helper functions for calculations
 */
function calculateOverallSimilarity(structural, semantic) {
  const structuralScore = structural.documentStructure.organizationSimilarity;
  const semanticScore = semantic.semanticSimilarity?.overallScore || 0.5;
  const textualScore = structural.textualChanges.similarityScore;
  
  // Weighted average: 30% structural, 50% semantic, 20% textual
  return (structuralScore * 0.3) + (semanticScore * 0.5) + (textualScore * 0.2);
}

function calculateTextSimilarity(text1, text2) {
  // Simple Jaccard similarity for text comparison
  const words1 = new Set(text1.toLowerCase().split(/\s+/));
  const words2 = new Set(text2.toLowerCase().split(/\s+/));
  
  const intersection = new Set([...words1].filter(x => words2.has(x)));
  const union = new Set([...words1, ...words2]);
  
  return intersection.size / union.size;
}

function calculateStructuralSimilarity(structure1, structure2) {
  const sectionSimilarity = Math.min(structure1.sections.length, structure2.sections.length) / Math.max(structure1.sections.length, structure2.sections.length);
  const paragraphSimilarity = Math.min(structure1.paragraphs.length, structure2.paragraphs.length) / Math.max(structure1.paragraphs.length, structure2.paragraphs.length);
  
  return (sectionSimilarity + paragraphSimilarity) / 2;
}

function compareSections(sections1, sections2) {
  // Implementation for section comparison
  return {
    similarity: calculateStructuralSimilarity({ sections: sections1 }, { sections: sections2 }),
    alignmentScore: 0.8,
    hierarchyChanges: []
  };
}

function identifyStructuralDifferences(structure1, structure2) {
  return {
    sectionCountDiff: structure2.sections.length - structure1.sections.length,
    paragraphCountDiff: structure2.paragraphs.length - structure1.paragraphs.length,
    listCountDiff: structure2.lists.length - structure1.lists.length,
    tableCountDiff: structure2.tables.length - structure1.tables.length
  };
}

function compareSectionContent(sections1, sections2) {
  return {
    added: [],
    removed: [],
    modified: []
  };
}

function calculateCompletenessScore(requirementsComparison) {
  const totalReqs = requirementsComparison.statistics.targetCount;
  const matchedReqs = requirementsComparison.matching.exact.length + requirementsComparison.matching.similar.length;
  
  return totalReqs > 0 ? (matchedReqs / totalReqs) : 0;
}

function calculateClarityScore(structuralComparison) {
  // Simple heuristic based on structural organization
  return structuralComparison.documentStructure.organizationSimilarity;
}

function generateComparisonSummary(structural, semantic, requirements) {
  const overallSimilarity = calculateOverallSimilarity(structural, semantic);
  
  let summaryText = '';
  if (overallSimilarity > 0.8) {
    summaryText = 'Documents are highly similar with minor differences.';
  } else if (overallSimilarity > 0.6) {
    summaryText = 'Documents share substantial content but have notable differences.';
  } else if (overallSimilarity > 0.4) {
    summaryText = 'Documents have some commonalities but significant differences.';
  } else {
    summaryText = 'Documents are substantially different in content and structure.';
  }
  
  return {
    overallSimilarity,
    description: summaryText,
    highlights: [
      `${requirements.statistics.netChange} net requirement changes`,
      `${(semantic.semanticSimilarity?.overallScore * 100 || 50).toFixed(1)}% semantic similarity`,
      `${(structural.documentStructure.organizationSimilarity * 100).toFixed(1)}% structural similarity`
    ]
  };
}

/**
 * Update comparison status in DynamoDB
 */
async function updateComparisonStatus(comparisonId, status, additionalData = {}) {
  try {
    const updateParams = {
      TableName: CONFIG.COMPARISONS_TABLE,
      Key: { id: comparisonId },
      UpdateExpression: 'SET #status = :status, updatedAt = :updatedAt',
      ExpressionAttributeNames: {
        '#status': 'status'
      },
      ExpressionAttributeValues: {
        ':status': status,
        ':updatedAt': new Date().toISOString()
      }
    };
    
    // Add additional data to update
    Object.keys(additionalData).forEach(key => {
      updateParams.UpdateExpression += `, #${key} = :${key}`;
      updateParams.ExpressionAttributeNames[`#${key}`] = key;
      updateParams.ExpressionAttributeValues[`:${key}`] = additionalData[key];
    });
    
    await dynamodb.update(updateParams).promise();
    
  } catch (error) {
    console.error(`Failed to update comparison status for ${comparisonId}:`, error);
    throw error;
  }
}

/**
 * Get comparison result
 */
async function getComparisonResult(comparisonId) {
  try {
    const result = await dynamodb.get({
      TableName: CONFIG.COMPARISONS_TABLE,
      Key: { id: comparisonId }
    }).promise();
    
    if (!result.Item) {
      return {
        statusCode: 404,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ error: 'Comparison not found' })
      };
    }
    
    return {
      statusCode: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(result.Item)
    };
    
  } catch (error) {
    console.error('Failed to get comparison result:', error);
    throw error;
  }
}

/**
 * List comparisons with pagination
 */
async function listComparisons(queryParams) {
  try {
    const { limit = 10, lastKey } = queryParams;
    
    const scanParams = {
      TableName: CONFIG.COMPARISONS_TABLE,
      Limit: parseInt(limit),
      ProjectionExpression: 'id, sourceDocumentId, targetDocumentId, #status, createdAt, updatedAt',
      ExpressionAttributeNames: {
        '#status': 'status'
      }
    };
    
    if (lastKey) {
      scanParams.ExclusiveStartKey = JSON.parse(decodeURIComponent(lastKey));
    }
    
    const result = await dynamodb.scan(scanParams).promise();
    
    return {
      statusCode: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        comparisons: result.Items,
        lastKey: result.LastEvaluatedKey ? encodeURIComponent(JSON.stringify(result.LastEvaluatedKey)) : null,
        count: result.Count
      })
    };
    
  } catch (error) {
    console.error('Failed to list comparisons:', error);
    throw error;
  }
}

/**
 * Delete comparison
 */
async function deleteComparison(comparisonId) {
  try {
    await dynamodb.delete({
      TableName: CONFIG.COMPARISONS_TABLE,
      Key: { id: comparisonId }
    }).promise();
    
    return {
      statusCode: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: 'Comparison deleted successfully' })
    };
    
  } catch (error) {
    console.error('Failed to delete comparison:', error);
    throw error;
  }
}

/**
 * Send comparison notification
 */
async function sendComparisonNotification(comparisonResult) {
  try {
    const message = {
      type: 'comparison_completed',
      comparisonId: comparisonResult.comparisonId,
      sourceDocument: comparisonResult.sourceDocument.title,
      targetDocument: comparisonResult.targetDocument.title,
      overallSimilarity: comparisonResult.results.overallSimilarity,
      summary: comparisonResult.results.summary.description,
      timestamp: new Date().toISOString()
    };
    
    await sns.publish({
      TopicArn: CONFIG.NOTIFICATIONS_TOPIC,
      Message: JSON.stringify(message),
      Subject: `Document Comparison Complete: ${comparisonResult.sourceDocument.title} vs ${comparisonResult.targetDocument.title}`
    }).promise();
    
  } catch (error) {
    console.error('Failed to send comparison notification:', error);
    // Don't throw error for notification failures
  }
}

/**
 * Handle queued comparison requests
 */
async function handleQueuedComparison(event) {
  const results = [];
  
  for (const record of event.Records) {
    try {
      let message;
      
      if (record.Sns) {
        message = JSON.parse(record.Sns.Message);
      } else if (record.body) {
        message = JSON.parse(record.body);
      } else {
        continue;
      }
      
      const result = await performDocumentComparison(message);
      results.push(result);
      
    } catch (error) {
      console.error('Failed to process queued comparison:', error);
      results.push({ error: error.message });
    }
  }
  
  return {
    statusCode: 200,
    body: JSON.stringify({
      processedCount: results.length,
      results
    })
  };
}