/**
 * Semantic Similarity Analysis Service
 * Advanced document relationship analysis and content similarity scoring
 */

const AWS = require('aws-sdk');
const { v4: uuidv4 } = require('uuid');

// Initialize AWS services
const bedrock = new AWS.BedrockRuntime({ region: process.env.AWS_REGION || 'us-east-1' });
const dynamodb = new AWS.DynamoDB.DocumentClient();
const s3 = new AWS.S3();
const comprehend = new AWS.Comprehend();

// Configuration
const CONFIG = {
  DOCUMENTS_TABLE: process.env.DOCUMENTS_TABLE || 'autospec-ai-documents',
  SIMILARITY_TABLE: process.env.SIMILARITY_TABLE || 'autospec-ai-similarity',
  EMBEDDINGS_BUCKET: process.env.EMBEDDINGS_BUCKET,
  BEDROCK_MODEL_ID: 'anthropic.claude-3-sonnet-20240229-v1:0',
  EMBEDDING_MODEL_ID: 'amazon.titan-embed-text-v1',
  SIMILARITY_THRESHOLD: 0.7,
  MAX_CONTENT_LENGTH: 100000,
  BATCH_SIZE: 50
};

/**
 * Main Lambda handler for semantic similarity analysis
 */
exports.handler = async (event, context) => {
  console.log('Semantic Analysis - Event:', JSON.stringify(event, null, 2));
  
  try {
    if (event.Records) {
      // Batch processing from SQS/SNS
      return await handleBatchAnalysis(event);
    } else if (event.httpMethod) {
      // API Gateway requests
      return await handleAPIRequest(event, context);
    } else {
      // Direct invocation
      return await performSemanticAnalysis(event);
    }
  } catch (error) {
    console.error('Semantic analysis failed:', error);
    
    return {
      statusCode: 500,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*'
      },
      body: JSON.stringify({
        error: 'Semantic analysis failed',
        message: error.message,
        requestId: context.awsRequestId
      })
    };
  }
};

/**
 * Handle API Gateway requests
 */
async function handleAPIRequest(event, context) {
  const { httpMethod, pathParameters, body, queryStringParameters } = event;
  
  switch (httpMethod) {
    case 'POST':
      if (pathParameters?.action === 'analyze') {
        return await analyzeSimilarity(JSON.parse(body || '{}'), context);
      } else if (pathParameters?.action === 'batch') {
        return await startBatchAnalysis(JSON.parse(body || '{}'), context);
      } else if (pathParameters?.action === 'embed') {
        return await generateEmbeddings(JSON.parse(body || '{}'), context);
      }
      break;
      
    case 'GET':
      if (pathParameters?.documentId) {
        return await getSimilarDocuments(pathParameters.documentId, queryStringParameters || {});
      } else if (pathParameters?.action === 'relationships') {
        return await getDocumentRelationships(queryStringParameters || {});
      } else if (pathParameters?.action === 'clusters') {
        return await getDocumentClusters(queryStringParameters || {});
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
 * Analyze similarity between documents
 */
async function analyzeSimilarity(requestBody, context) {
  const { documentIds, analysisType = 'comprehensive', options = {} } = requestBody;
  
  if (!documentIds || documentIds.length < 2) {
    return {
      statusCode: 400,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        error: 'Invalid parameters',
        message: 'At least 2 document IDs are required'
      })
    };
  }
  
  try {
    const analysisId = uuidv4();
    const result = await performSemanticAnalysis({
      analysisId,
      documentIds,
      analysisType,
      options,
      requestId: context.awsRequestId
    });
    
    return {
      statusCode: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(result)
    };
    
  } catch (error) {
    console.error('Similarity analysis failed:', error);
    throw error;
  }
}

/**
 * Perform comprehensive semantic analysis
 */
async function performSemanticAnalysis(params) {
  const { analysisId, documentIds, analysisType = 'comprehensive', options = {} } = params;
  
  console.log(`Starting semantic analysis ${analysisId} for documents:`, documentIds);
  
  try {
    // Load documents
    const documents = await loadDocuments(documentIds);
    
    // Generate embeddings for all documents
    const embeddings = await generateDocumentEmbeddings(documents);
    
    // Perform different types of analysis
    const analysisResults = {
      analysisId,
      documentIds,
      analysisType,
      timestamp: new Date().toISOString()
    };
    
    switch (analysisType) {
      case 'pairwise':
        analysisResults.pairwiseAnalysis = await performPairwiseAnalysis(documents, embeddings, options);
        break;
        
      case 'clustering':
        analysisResults.clusterAnalysis = await performClusterAnalysis(documents, embeddings, options);
        break;
        
      case 'comprehensive':
      default:
        analysisResults.pairwiseAnalysis = await performPairwiseAnalysis(documents, embeddings, options);
        analysisResults.clusterAnalysis = await performClusterAnalysis(documents, embeddings, options);
        analysisResults.contentAnalysis = await performContentAnalysis(documents, options);
        analysisResults.topicAnalysis = await performTopicAnalysis(documents, options);
        analysisResults.relationshipGraph = await buildRelationshipGraph(documents, analysisResults.pairwiseAnalysis);
        break;
    }
    
    // Save analysis results
    await saveAnalysisResults(analysisResults);
    
    // Generate insights and recommendations
    analysisResults.insights = await generateSemanticInsights(analysisResults);
    
    console.log(`Semantic analysis ${analysisId} completed`);
    return analysisResults;
    
  } catch (error) {
    console.error(`Semantic analysis ${analysisId} failed:`, error);
    throw error;
  }
}

/**
 * Load documents from DynamoDB
 */
async function loadDocuments(documentIds) {
  const documents = [];
  
  // Batch get documents
  const batchKeys = documentIds.map(id => ({ id }));
  
  try {
    const result = await dynamodb.batchGet({
      RequestItems: {
        [CONFIG.DOCUMENTS_TABLE]: {
          Keys: batchKeys
        }
      }
    }).promise();
    
    const foundDocuments = result.Responses[CONFIG.DOCUMENTS_TABLE] || [];
    
    if (foundDocuments.length !== documentIds.length) {
      const foundIds = foundDocuments.map(doc => doc.id);
      const missingIds = documentIds.filter(id => !foundIds.includes(id));
      console.warn(`Missing documents: ${missingIds.join(', ')}`);
    }
    
    return foundDocuments;
    
  } catch (error) {
    console.error('Failed to load documents:', error);
    throw error;
  }
}

/**
 * Generate embeddings for documents
 */
async function generateDocumentEmbeddings(documents) {
  const embeddings = {};
  
  for (const document of documents) {
    try {
      // Check if embeddings already exist
      const existingEmbedding = await getExistingEmbedding(document.id);
      
      if (existingEmbedding && !isEmbeddingStale(existingEmbedding, document)) {
        embeddings[document.id] = existingEmbedding;
        continue;
      }
      
      // Generate new embedding
      const content = prepareContentForEmbedding(document);
      const embedding = await generateEmbedding(content);
      
      // Store embedding
      const embeddingRecord = {
        documentId: document.id,
        embedding,
        contentHash: generateContentHash(content),
        createdAt: new Date().toISOString(),
        modelId: CONFIG.EMBEDDING_MODEL_ID
      };
      
      await storeEmbedding(embeddingRecord);
      embeddings[document.id] = embeddingRecord;
      
    } catch (error) {
      console.error(`Failed to generate embedding for document ${document.id}:`, error);
      // Continue with other documents
    }
  }
  
  return embeddings;
}

/**
 * Prepare document content for embedding
 */
function prepareContentForEmbedding(document) {
  let content = '';
  
  // Add title
  content += `Title: ${document.title}\n\n`;
  
  // Add processed content or raw content
  const documentContent = document.processedContent || document.content || '';
  
  // Truncate if too long
  if (documentContent.length > CONFIG.MAX_CONTENT_LENGTH) {
    content += documentContent.substring(0, CONFIG.MAX_CONTENT_LENGTH) + '...';
  } else {
    content += documentContent;
  }
  
  // Add requirements if available
  if (document.requirements && document.requirements.length > 0) {
    content += '\n\nRequirements:\n';
    document.requirements.forEach((req, index) => {
      if (index < 10) { // Limit to first 10 requirements
        content += `${req.id || `REQ-${index + 1}`}: ${req.description || req.text || ''}\n`;
      }
    });
  }
  
  return content;
}

/**
 * Generate embedding using Amazon Bedrock
 */
async function generateEmbedding(text) {
  try {
    const response = await bedrock.invokeModel({
      modelId: CONFIG.EMBEDDING_MODEL_ID,
      contentType: 'application/json',
      accept: 'application/json',
      body: JSON.stringify({
        inputText: text
      })
    }).promise();
    
    const responseBody = JSON.parse(response.body.toString());
    return responseBody.embedding;
    
  } catch (error) {
    console.error('Failed to generate embedding:', error);
    throw error;
  }
}

/**
 * Perform pairwise similarity analysis
 */
async function performPairwiseAnalysis(documents, embeddings, options = {}) {
  const pairs = [];
  
  // Generate all pairs
  for (let i = 0; i < documents.length; i++) {
    for (let j = i + 1; j < documents.length; j++) {
      const doc1 = documents[i];
      const doc2 = documents[j];
      
      const embedding1 = embeddings[doc1.id];
      const embedding2 = embeddings[doc2.id];
      
      if (!embedding1 || !embedding2) {
        console.warn(`Missing embeddings for pair ${doc1.id} - ${doc2.id}`);
        continue;
      }
      
      // Calculate cosine similarity
      const cosineSimilarity = calculateCosineSimilarity(embedding1.embedding, embedding2.embedding);
      
      // Perform deep semantic analysis
      const semanticAnalysis = await performDeepSemanticAnalysis(doc1, doc2, options);
      
      const pairAnalysis = {
        document1: {
          id: doc1.id,
          title: doc1.title,
          type: doc1.type
        },
        document2: {
          id: doc2.id,
          title: doc2.title,
          type: doc2.type
        },
        similarity: {
          cosine: cosineSimilarity,
          semantic: semanticAnalysis.overallSimilarity,
          structural: semanticAnalysis.structuralSimilarity,
          conceptual: semanticAnalysis.conceptualSimilarity
        },
        analysis: semanticAnalysis,
        relationship: determineRelationshipType(cosineSimilarity, semanticAnalysis),
        confidence: calculateConfidenceScore(cosineSimilarity, semanticAnalysis)
      };
      
      pairs.push(pairAnalysis);
    }
  }
  
  // Sort by similarity (highest first)
  pairs.sort((a, b) => b.similarity.semantic - a.similarity.semantic);
  
  return {
    totalPairs: pairs.length,
    highSimilarityPairs: pairs.filter(p => p.similarity.semantic >= CONFIG.SIMILARITY_THRESHOLD),
    averageSimilarity: pairs.reduce((sum, p) => sum + p.similarity.semantic, 0) / pairs.length,
    pairs
  };
}

/**
 * Perform deep semantic analysis between two documents
 */
async function performDeepSemanticAnalysis(doc1, doc2, options = {}) {
  const prompt = `
Analyze the semantic relationship between these two documents and provide detailed similarity metrics.

Document 1:
Title: ${doc1.title}
Type: ${doc1.type}
Content: ${(doc1.processedContent || doc1.content || '').substring(0, 3000)}...

Document 2:
Title: ${doc2.title}
Type: ${doc2.type}
Content: ${(doc2.processedContent || doc2.content || '').substring(0, 3000)}...

Provide analysis in JSON format:
{
  "overallSimilarity": 0.85,
  "structuralSimilarity": 0.80,
  "conceptualSimilarity": 0.90,
  "topicOverlap": {
    "score": 0.75,
    "sharedTopics": ["authentication", "data_validation"],
    "uniqueToDoc1": ["legacy_integration"],
    "uniqueToDoc2": ["mobile_optimization"]
  },
  "requirementsSimilarity": {
    "score": 0.70,
    "sharedConcepts": 8,
    "totalConcepts": 15,
    "alignmentAreas": ["security", "performance"]
  },
  "terminologyConsistency": {
    "score": 0.85,
    "consistentTerms": 12,
    "inconsistentTerms": 3
  },
  "relationshipType": "complementary",
  "keyDifferences": [
    {
      "category": "scope",
      "description": "Document 1 focuses on backend, Document 2 on frontend",
      "impact": "medium"
    }
  ],
  "recommendedActions": [
    {
      "action": "harmonize_terminology",
      "priority": "medium",
      "description": "Align technical terminology across documents"
    }
  ]
}
`;
  
  try {
    const response = await bedrock.invokeModel({
      modelId: CONFIG.BEDROCK_MODEL_ID,
      contentType: 'application/json',
      accept: 'application/json',
      body: JSON.stringify({
        anthropic_version: 'bedrock-2023-05-31',
        max_tokens: 3000,
        messages: [{
          role: 'user',
          content: prompt
        }]
      })
    }).promise();
    
    const responseBody = JSON.parse(response.body.toString());
    const analysisText = responseBody.content[0].text;
    
    // Extract JSON from response
    const jsonMatch = analysisText.match(/\{[\s\S]*\}/);
    if (jsonMatch) {
      return JSON.parse(jsonMatch[0]);
    } else {
      throw new Error('Invalid JSON response from Bedrock');
    }
    
  } catch (error) {
    console.error('Deep semantic analysis failed:', error);
    
    // Fallback to basic analysis
    return {
      overallSimilarity: 0.5,
      structuralSimilarity: 0.5,
      conceptualSimilarity: 0.5,
      topicOverlap: { score: 0.5, sharedTopics: [], uniqueToDoc1: [], uniqueToDoc2: [] },
      requirementsSimilarity: { score: 0.5, sharedConcepts: 0, totalConcepts: 0, alignmentAreas: [] },
      terminologyConsistency: { score: 0.5, consistentTerms: 0, inconsistentTerms: 0 },
      relationshipType: 'unknown',
      keyDifferences: [],
      recommendedActions: [],
      error: error.message
    };
  }
}

/**
 * Perform cluster analysis
 */
async function performClusterAnalysis(documents, embeddings, options = {}) {
  const numClusters = options.numClusters || Math.min(Math.ceil(documents.length / 3), 5);
  
  // Extract embedding vectors
  const vectors = [];
  const documentMap = {};
  
  for (const document of documents) {
    const embedding = embeddings[document.id];
    if (embedding) {
      vectors.push(embedding.embedding);
      documentMap[vectors.length - 1] = document;
    }
  }
  
  // Perform k-means clustering
  const clusters = performKMeansClustering(vectors, numClusters);
  
  // Build cluster results
  const clusterResults = [];
  
  for (let i = 0; i < numClusters; i++) {
    const clusterDocuments = clusters
      .map((cluster, index) => cluster === i ? documentMap[index] : null)
      .filter(doc => doc !== null);
    
    if (clusterDocuments.length > 0) {
      const clusterAnalysis = await analyzeCluster(clusterDocuments);
      
      clusterResults.push({
        clusterId: i,
        documentCount: clusterDocuments.length,
        documents: clusterDocuments.map(doc => ({
          id: doc.id,
          title: doc.title,
          type: doc.type
        })),
        characteristics: clusterAnalysis.characteristics,
        commonThemes: clusterAnalysis.commonThemes,
        centroid: calculateClusterCentroid(clusterDocuments, embeddings)
      });
    }
  }
  
  return {
    numClusters: clusterResults.length,
    clusters: clusterResults,
    silhouetteScore: calculateSilhouetteScore(vectors, clusters)
  };
}

/**
 * Perform content analysis
 */
async function performContentAnalysis(documents, options = {}) {
  const analysis = {
    documentTypes: {},
    domains: {},
    commonConcepts: [],
    topicDistribution: {},
    lengthAnalysis: {
      average: 0,
      median: 0,
      min: Infinity,
      max: 0
    }
  };
  
  const lengths = [];
  const allText = documents.map(doc => doc.processedContent || doc.content || '').join(' ');
  
  // Analyze document characteristics
  for (const document of documents) {
    // Document type distribution
    analysis.documentTypes[document.type] = (analysis.documentTypes[document.type] || 0) + 1;
    
    // Length analysis
    const content = document.processedContent || document.content || '';
    const length = content.length;
    lengths.push(length);
    
    analysis.lengthAnalysis.min = Math.min(analysis.lengthAnalysis.min, length);
    analysis.lengthAnalysis.max = Math.max(analysis.lengthAnalysis.max, length);
  }
  
  // Calculate length statistics
  analysis.lengthAnalysis.average = lengths.reduce((a, b) => a + b, 0) / lengths.length;
  analysis.lengthAnalysis.median = lengths.sort((a, b) => a - b)[Math.floor(lengths.length / 2)];
  
  // Extract common concepts using AWS Comprehend
  try {
    const entitiesResult = await comprehend.detectEntities({
      Text: allText.substring(0, 5000), // Comprehend limit
      LanguageCode: 'en'
    }).promise();
    
    const conceptCounts = {};
    entitiesResult.Entities.forEach(entity => {
      if (entity.Score > 0.8) {
        conceptCounts[entity.Text] = (conceptCounts[entity.Text] || 0) + 1;
      }
    });
    
    analysis.commonConcepts = Object.entries(conceptCounts)
      .filter(([text, count]) => count > 1)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 20)
      .map(([text, count]) => ({ concept: text, frequency: count }));
      
  } catch (error) {
    console.warn('Failed to extract entities with Comprehend:', error);
  }
  
  return analysis;
}

/**
 * Perform topic analysis
 */
async function performTopicAnalysis(documents, options = {}) {
  // Simple topic extraction using keyword frequency
  const topicWords = {};
  const stopWords = new Set(['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by']);
  
  for (const document of documents) {
    const content = document.processedContent || document.content || '';
    const words = content.toLowerCase()
      .replace(/[^a-z\s]/g, '')
      .split(/\s+/)
      .filter(word => word.length > 3 && !stopWords.has(word));
    
    words.forEach(word => {
      topicWords[word] = (topicWords[word] || 0) + 1;
    });
  }
  
  const topics = Object.entries(topicWords)
    .filter(([word, count]) => count >= 2)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 15)
    .map(([word, count]) => ({
      topic: word,
      frequency: count,
      relevance: count / documents.length
    }));
  
  return {
    extractedTopics: topics,
    topicCount: topics.length,
    coverage: topics.reduce((sum, topic) => sum + topic.relevance, 0) / topics.length
  };
}

/**
 * Build relationship graph
 */
async function buildRelationshipGraph(documents, pairwiseAnalysis) {
  const nodes = documents.map(doc => ({
    id: doc.id,
    title: doc.title,
    type: doc.type,
    group: determineDocumentGroup(doc)
  }));
  
  const edges = pairwiseAnalysis.pairs
    .filter(pair => pair.similarity.semantic >= 0.5)
    .map(pair => ({
      source: pair.document1.id,
      target: pair.document2.id,
      weight: pair.similarity.semantic,
      type: pair.relationship,
      confidence: pair.confidence
    }));
  
  return {
    nodes,
    edges,
    metrics: {
      nodeCount: nodes.length,
      edgeCount: edges.length,
      density: edges.length / (nodes.length * (nodes.length - 1) / 2),
      avgDegree: (edges.length * 2) / nodes.length
    }
  };
}

/**
 * Calculate cosine similarity between two vectors
 */
function calculateCosineSimilarity(vector1, vector2) {
  let dotProduct = 0;
  let norm1 = 0;
  let norm2 = 0;
  
  for (let i = 0; i < vector1.length; i++) {
    dotProduct += vector1[i] * vector2[i];
    norm1 += vector1[i] * vector1[i];
    norm2 += vector2[i] * vector2[i];
  }
  
  return dotProduct / (Math.sqrt(norm1) * Math.sqrt(norm2));
}

/**
 * Determine relationship type between documents
 */
function determineRelationshipType(cosineSimilarity, semanticAnalysis) {
  if (semanticAnalysis.relationshipType !== 'unknown') {
    return semanticAnalysis.relationshipType;
  }
  
  if (cosineSimilarity >= 0.9) {
    return 'duplicate';
  } else if (cosineSimilarity >= 0.8) {
    return 'highly_similar';
  } else if (cosineSimilarity >= 0.7) {
    return 'related';
  } else if (cosineSimilarity >= 0.5) {
    return 'somewhat_related';
  } else {
    return 'unrelated';
  }
}

/**
 * Calculate confidence score
 */
function calculateConfidenceScore(cosineSimilarity, semanticAnalysis) {
  // Weight different factors
  const cosineWeight = 0.3;
  const semanticWeight = 0.4;
  const structuralWeight = 0.2;
  const conceptualWeight = 0.1;
  
  return (
    cosineSimilarity * cosineWeight +
    semanticAnalysis.overallSimilarity * semanticWeight +
    semanticAnalysis.structuralSimilarity * structuralWeight +
    semanticAnalysis.conceptualSimilarity * conceptualWeight
  );
}

/**
 * Simple k-means clustering implementation
 */
function performKMeansClustering(vectors, k) {
  const maxIterations = 100;
  const clusters = new Array(vectors.length);
  
  // Initialize centroids randomly
  const centroids = [];
  for (let i = 0; i < k; i++) {
    const randomIndex = Math.floor(Math.random() * vectors.length);
    centroids.push([...vectors[randomIndex]]);
  }
  
  for (let iteration = 0; iteration < maxIterations; iteration++) {
    let changed = false;
    
    // Assign points to nearest centroid
    for (let i = 0; i < vectors.length; i++) {
      let minDistance = Infinity;
      let nearestCentroid = 0;
      
      for (let j = 0; j < k; j++) {
        const distance = euclideanDistance(vectors[i], centroids[j]);
        if (distance < minDistance) {
          minDistance = distance;
          nearestCentroid = j;
        }
      }
      
      if (clusters[i] !== nearestCentroid) {
        clusters[i] = nearestCentroid;
        changed = true;
      }
    }
    
    if (!changed) break;
    
    // Update centroids
    for (let j = 0; j < k; j++) {
      const clusterPoints = vectors.filter((_, i) => clusters[i] === j);
      if (clusterPoints.length > 0) {
        for (let dim = 0; dim < centroids[j].length; dim++) {
          centroids[j][dim] = clusterPoints.reduce((sum, point) => sum + point[dim], 0) / clusterPoints.length;
        }
      }
    }
  }
  
  return clusters;
}

/**
 * Calculate Euclidean distance between two vectors
 */
function euclideanDistance(vector1, vector2) {
  let sum = 0;
  for (let i = 0; i < vector1.length; i++) {
    sum += Math.pow(vector1[i] - vector2[i], 2);
  }
  return Math.sqrt(sum);
}

/**
 * Analyze cluster characteristics
 */
async function analyzeCluster(clusterDocuments) {
  const types = {};
  const themes = {};
  
  for (const doc of clusterDocuments) {
    types[doc.type] = (types[doc.type] || 0) + 1;
    
    // Extract themes from title and content
    const text = `${doc.title} ${doc.processedContent || doc.content || ''}`;
    const words = text.toLowerCase().match(/\b\w{4,}\b/g) || [];
    
    words.forEach(word => {
      themes[word] = (themes[word] || 0) + 1;
    });
  }
  
  return {
    characteristics: {
      dominantType: Object.entries(types).sort((a, b) => b[1] - a[1])[0]?.[0] || 'unknown',
      typeDistribution: types,
      averageLength: clusterDocuments.reduce((sum, doc) => 
        sum + (doc.processedContent || doc.content || '').length, 0) / clusterDocuments.length
    },
    commonThemes: Object.entries(themes)
      .filter(([word, count]) => count > 1)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10)
      .map(([word, count]) => ({ theme: word, frequency: count }))
  };
}

/**
 * Calculate cluster centroid
 */
function calculateClusterCentroid(clusterDocuments, embeddings) {
  const vectors = clusterDocuments
    .map(doc => embeddings[doc.id]?.embedding)
    .filter(embedding => embedding);
  
  if (vectors.length === 0) return null;
  
  const centroid = new Array(vectors[0].length).fill(0);
  
  for (const vector of vectors) {
    for (let i = 0; i < vector.length; i++) {
      centroid[i] += vector[i];
    }
  }
  
  for (let i = 0; i < centroid.length; i++) {
    centroid[i] /= vectors.length;
  }
  
  return centroid;
}

/**
 * Calculate silhouette score for clustering quality
 */
function calculateSilhouetteScore(vectors, clusters) {
  // Simplified silhouette score calculation
  // In a production system, you'd want a more robust implementation
  return 0.7; // Placeholder
}

/**
 * Determine document group for visualization
 */
function determineDocumentGroup(document) {
  // Simple grouping based on document type
  const typeGroups = {
    'requirements_specification': 'requirements',
    'system_design': 'design',
    'api_documentation': 'api',
    'test_plan': 'testing',
    'user_manual': 'documentation'
  };
  
  return typeGroups[document.type] || 'other';
}

/**
 * Generate semantic insights
 */
async function generateSemanticInsights(analysisResults) {
  const insights = {
    summary: '',
    keyFindings: [],
    recommendations: [],
    qualityMetrics: {}
  };
  
  // Analyze pairwise results
  if (analysisResults.pairwiseAnalysis) {
    const { pairs, averageSimilarity, highSimilarityPairs } = analysisResults.pairwiseAnalysis;
    
    insights.summary = `Analyzed ${pairs.length} document pairs with average similarity of ${(averageSimilarity * 100).toFixed(1)}%.`;
    
    if (highSimilarityPairs.length > 0) {
      insights.keyFindings.push({
        type: 'high_similarity',
        description: `Found ${highSimilarityPairs.length} highly similar document pairs`,
        impact: 'medium',
        details: highSimilarityPairs.slice(0, 3).map(pair => 
          `${pair.document1.title} ↔ ${pair.document2.title} (${(pair.similarity.semantic * 100).toFixed(1)}%)`
        )
      });
    }
    
    // Check for potential duplicates
    const duplicates = pairs.filter(pair => pair.relationship === 'duplicate');
    if (duplicates.length > 0) {
      insights.recommendations.push({
        type: 'duplicate_resolution',
        priority: 'high',
        description: `Review ${duplicates.length} potential duplicate document pairs for consolidation`
      });
    }
  }
  
  // Analyze clustering results
  if (analysisResults.clusterAnalysis) {
    const { clusters } = analysisResults.clusterAnalysis;
    
    insights.keyFindings.push({
      type: 'clustering',
      description: `Documents naturally group into ${clusters.length} thematic clusters`,
      impact: 'low',
      details: clusters.map(cluster => 
        `Cluster ${cluster.clusterId}: ${cluster.documentCount} documents (${cluster.characteristics.dominantType})`
      )
    });
  }
  
  // Quality metrics
  insights.qualityMetrics = {
    coherence: analysisResults.pairwiseAnalysis?.averageSimilarity || 0,
    diversity: 1 - (analysisResults.pairwiseAnalysis?.averageSimilarity || 0.5),
    completeness: analysisResults.contentAnalysis ? 0.8 : 0.5
  };
  
  return insights;
}

/**
 * Save analysis results
 */
async function saveAnalysisResults(analysisResults) {
  try {
    await dynamodb.put({
      TableName: CONFIG.SIMILARITY_TABLE,
      Item: {
        ...analysisResults,
        ttl: Math.floor(Date.now() / 1000) + (30 * 24 * 60 * 60) // 30 days TTL
      }
    }).promise();
    
  } catch (error) {
    console.error('Failed to save analysis results:', error);
    throw error;
  }
}

/**
 * Get existing embedding
 */
async function getExistingEmbedding(documentId) {
  // Implementation would check S3 or DynamoDB for existing embeddings
  return null; // Placeholder
}

/**
 * Check if embedding is stale
 */
function isEmbeddingStale(embedding, document) {
  // Compare content hash or modification time
  return false; // Placeholder
}

/**
 * Generate content hash
 */
function generateContentHash(content) {
  // Simple hash implementation
  return require('crypto').createHash('md5').update(content).digest('hex');
}

/**
 * Store embedding
 */
async function storeEmbedding(embeddingRecord) {
  // Store in S3 or DynamoDB
  console.log(`Storing embedding for document ${embeddingRecord.documentId}`);
}

/**
 * Handle batch analysis
 */
async function handleBatchAnalysis(event) {
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
      
      const result = await performSemanticAnalysis(message);
      results.push(result);
      
    } catch (error) {
      console.error('Failed to process batch analysis:', error);
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

// Additional API endpoint implementations would go here:
// - getSimilarDocuments
// - getDocumentRelationships
// - getDocumentClusters
// - startBatchAnalysis
// - generateEmbeddings