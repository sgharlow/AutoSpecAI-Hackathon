/**
 * Requirement Traceability and Impact Analysis Service
 * Tracks relationships between requirements and analyzes change impacts
 */

const AWS = require('aws-sdk');
const { v4: uuidv4 } = require('uuid');

// Initialize AWS services
const bedrock = new AWS.BedrockRuntime({ region: process.env.AWS_REGION || 'us-east-1' });
const dynamodb = new AWS.DynamoDB.DocumentClient();
const sns = new AWS.SNS();
const stepfunctions = new AWS.StepFunctions();

// Configuration
const CONFIG = {
  REQUIREMENTS_TABLE: process.env.REQUIREMENTS_TABLE || 'autospec-ai-requirements',
  TRACEABILITY_TABLE: process.env.TRACEABILITY_TABLE || 'autospec-ai-traceability',
  IMPACT_ANALYSIS_TABLE: process.env.IMPACT_ANALYSIS_TABLE || 'autospec-ai-impact-analysis',
  DOCUMENTS_TABLE: process.env.DOCUMENTS_TABLE || 'autospec-ai-documents',
  NOTIFICATIONS_TOPIC: process.env.NOTIFICATIONS_TOPIC,
  BEDROCK_MODEL_ID: 'anthropic.claude-3-sonnet-20240229-v1:0',
  MAX_ANALYSIS_DEPTH: 5,
  IMPACT_THRESHOLD: 0.3
};

// Traceability relationship types
const RELATIONSHIP_TYPES = {
  DERIVES_FROM: 'derives_from',
  REFINES: 'refines',
  IMPLEMENTS: 'implements',
  TESTS: 'tests',
  DEPENDS_ON: 'depends_on',
  CONFLICTS_WITH: 'conflicts_with',
  SUPPORTS: 'supports',
  REPLACES: 'replaces'
};

// Impact types
const IMPACT_TYPES = {
  DIRECT: 'direct',
  CASCADING: 'cascading',
  ARCHITECTURAL: 'architectural',
  FUNCTIONAL: 'functional',
  PERFORMANCE: 'performance',
  SECURITY: 'security',
  COMPLIANCE: 'compliance'
};

/**
 * Main Lambda handler for traceability and impact analysis
 */
exports.handler = async (event, context) => {
  console.log('Traceability Analysis - Event:', JSON.stringify(event, null, 2));
  
  try {
    if (event.Records) {
      // Process batch events
      return await handleBatchProcessing(event);
    } else if (event.httpMethod) {
      // Handle API Gateway requests
      return await handleAPIRequest(event, context);
    } else {
      // Direct invocation
      return await performTraceabilityAnalysis(event);
    }
  } catch (error) {
    console.error('Traceability analysis failed:', error);
    
    return {
      statusCode: 500,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*'
      },
      body: JSON.stringify({
        error: 'Traceability analysis failed',
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
      if (pathParameters?.action === 'trace') {
        return await buildTraceabilityMatrix(JSON.parse(body || '{}'), context);
      } else if (pathParameters?.action === 'impact') {
        return await analyzeImpact(JSON.parse(body || '{}'), context);
      } else if (pathParameters?.action === 'relationships') {
        return await createRelationship(JSON.parse(body || '{}'), context);
      }
      break;
      
    case 'GET':
      if (pathParameters?.requirementId) {
        if (pathParameters?.action === 'trace') {
          return await getRequirementTrace(pathParameters.requirementId, queryStringParameters || {});
        } else if (pathParameters?.action === 'impact') {
          return await getImpactAnalysis(pathParameters.requirementId, queryStringParameters || {});
        } else if (pathParameters?.action === 'relationships') {
          return await getRequirementRelationships(pathParameters.requirementId);
        }
      } else if (pathParameters?.action === 'matrix') {
        return await getTraceabilityMatrix(queryStringParameters || {});
      } else if (pathParameters?.action === 'coverage') {
        return await getTraceabilityCoverage(queryStringParameters || {});
      }
      break;
      
    case 'PUT':
      if (pathParameters?.relationshipId) {
        return await updateRelationship(pathParameters.relationshipId, JSON.parse(body || '{}'));
      }
      break;
      
    case 'DELETE':
      if (pathParameters?.relationshipId) {
        return await deleteRelationship(pathParameters.relationshipId);
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
 * Build comprehensive traceability matrix
 */
async function buildTraceabilityMatrix(requestBody, context) {
  const { documentIds, options = {} } = requestBody;
  
  if (!documentIds || documentIds.length === 0) {
    return {
      statusCode: 400,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        error: 'Invalid parameters',
        message: 'Document IDs are required'
      })
    };
  }
  
  try {
    const matrixId = uuidv4();
    const result = await performTraceabilityAnalysis({
      matrixId,
      documentIds,
      analysisType: 'traceability_matrix',
      options,
      requestId: context.awsRequestId
    });
    
    return {
      statusCode: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(result)
    };
    
  } catch (error) {
    console.error('Traceability matrix generation failed:', error);
    throw error;
  }
}

/**
 * Perform comprehensive traceability analysis
 */
async function performTraceabilityAnalysis(params) {
  const { matrixId, documentIds, analysisType = 'full', options = {} } = params;
  
  console.log(`Starting traceability analysis ${matrixId} for documents:`, documentIds);
  
  try {
    // Load requirements from documents
    const requirements = await loadRequirementsFromDocuments(documentIds);
    
    // Discover relationships using AI
    const discoveredRelationships = await discoverRequirementRelationships(requirements, options);
    
    // Build traceability matrix
    const traceabilityMatrix = await buildMatrix(requirements, discoveredRelationships);
    
    // Analyze coverage and gaps
    const coverageAnalysis = await analyzeCoverage(requirements, discoveredRelationships);
    
    // Generate traceability insights
    const insights = await generateTraceabilityInsights(traceabilityMatrix, coverageAnalysis);
    
    const analysisResult = {
      matrixId,
      documentIds,
      analysisType,
      timestamp: new Date().toISOString(),
      requirements: {
        total: requirements.length,
        byType: groupRequirementsByType(requirements),
        byPriority: groupRequirementsByPriority(requirements)
      },
      traceabilityMatrix,
      relationships: {
        discovered: discoveredRelationships.length,
        byType: groupRelationshipsByType(discoveredRelationships),
        confidence: calculateAverageConfidence(discoveredRelationships)
      },
      coverage: coverageAnalysis,
      insights,
      metadata: {
        generatedBy: 'ai_traceability_analysis',
        model: CONFIG.BEDROCK_MODEL_ID,
        version: '1.0.0'
      }
    };
    
    // Save analysis results
    await saveTraceabilityAnalysis(analysisResult);
    
    // Send notifications if configured
    if (CONFIG.NOTIFICATIONS_TOPIC) {
      await sendTraceabilityNotification(analysisResult);
    }
    
    console.log(`Traceability analysis ${matrixId} completed`);
    return analysisResult;
    
  } catch (error) {
    console.error(`Traceability analysis ${matrixId} failed:`, error);
    throw error;
  }
}

/**
 * Load requirements from documents
 */
async function loadRequirementsFromDocuments(documentIds) {
  const requirements = [];
  
  // Load documents
  const batchKeys = documentIds.map(id => ({ id }));
  
  try {
    const result = await dynamodb.batchGet({
      RequestItems: {
        [CONFIG.DOCUMENTS_TABLE]: {
          Keys: batchKeys
        }
      }
    }).promise();
    
    const documents = result.Responses[CONFIG.DOCUMENTS_TABLE] || [];
    
    // Extract requirements from each document
    for (const document of documents) {
      if (document.requirements && Array.isArray(document.requirements)) {
        for (const req of document.requirements) {
          requirements.push({
            ...req,
            sourceDocumentId: document.id,
            sourceDocumentTitle: document.title,
            extractedAt: new Date().toISOString()
          });
        }
      }
    }
    
    // Also load standalone requirements
    const standaloneReqs = await loadStandaloneRequirements(documentIds);
    requirements.push(...standaloneReqs);
    
    return requirements;
    
  } catch (error) {
    console.error('Failed to load requirements:', error);
    throw error;
  }
}

/**
 * Load standalone requirements from requirements table
 */
async function loadStandaloneRequirements(documentIds) {
  try {
    const requirements = [];
    
    for (const documentId of documentIds) {
      const result = await dynamodb.query({
        TableName: CONFIG.REQUIREMENTS_TABLE,
        IndexName: 'DocumentIdIndex',
        KeyConditionExpression: 'documentId = :documentId',
        ExpressionAttributeValues: {
          ':documentId': documentId
        }
      }).promise();
      
      requirements.push(...(result.Items || []));
    }
    
    return requirements;
    
  } catch (error) {
    console.error('Failed to load standalone requirements:', error);
    return [];
  }
}

/**
 * Discover requirement relationships using AI
 */
async function discoverRequirementRelationships(requirements, options = {}) {
  const relationships = [];
  const maxPairs = Math.min(100, requirements.length * (requirements.length - 1) / 2);
  let processedPairs = 0;
  
  console.log(`Analyzing relationships for ${requirements.length} requirements`);
  
  // Analyze requirement pairs
  for (let i = 0; i < requirements.length && processedPairs < maxPairs; i++) {
    for (let j = i + 1; j < requirements.length && processedPairs < maxPairs; j++) {
      const req1 = requirements[i];
      const req2 = requirements[j];
      
      try {
        const relationship = await analyzeRequirementPair(req1, req2, options);
        
        if (relationship && relationship.confidence >= (options.minConfidence || 0.5)) {
          relationships.push({
            id: uuidv4(),
            sourceRequirement: {
              id: req1.id,
              text: req1.description || req1.text,
              type: req1.type,
              priority: req1.priority
            },
            targetRequirement: {
              id: req2.id,
              text: req2.description || req2.text,
              type: req2.type,
              priority: req2.priority
            },
            relationshipType: relationship.type,
            confidence: relationship.confidence,
            reasoning: relationship.reasoning,
            bidirectional: relationship.bidirectional || false,
            discoveredAt: new Date().toISOString(),
            metadata: {
              analysisMethod: 'ai_bedrock',
              model: CONFIG.BEDROCK_MODEL_ID
            }
          });
        }
        
        processedPairs++;
        
      } catch (error) {
        console.error(`Failed to analyze pair ${req1.id} - ${req2.id}:`, error);
      }
    }
  }
  
  // Also check for existing manual relationships
  const existingRelationships = await loadExistingRelationships(requirements.map(r => r.id));
  relationships.push(...existingRelationships);
  
  return relationships;
}

/**
 * Analyze relationship between two requirements
 */
async function analyzeRequirementPair(req1, req2, options = {}) {
  const prompt = `
Analyze the relationship between these two requirements and determine if there's a meaningful connection.

Requirement 1:
ID: ${req1.id}
Type: ${req1.type}
Priority: ${req1.priority}
Text: ${req1.description || req1.text}

Requirement 2:
ID: ${req2.id}
Type: ${req2.type}
Priority: ${req2.priority}
Text: ${req2.description || req2.text}

Analyze for these relationship types:
- derives_from: One requirement is derived from another
- refines: One requirement refines/elaborates another
- implements: One requirement implements another at a lower level
- tests: One requirement tests another
- depends_on: One requirement depends on another
- conflicts_with: Requirements are in conflict
- supports: One requirement supports another
- replaces: One requirement replaces another

Provide analysis in JSON format:
{
  "hasRelationship": true,
  "type": "depends_on",
  "confidence": 0.85,
  "bidirectional": false,
  "reasoning": "Requirement 1 depends on the authentication mechanism defined in Requirement 2",
  "strength": "strong",
  "impactLevel": "medium"
}

Only identify relationships with confidence >= 0.5. If no meaningful relationship exists, return:
{"hasRelationship": false}
`;
  
  try {
    const response = await bedrock.invokeModel({
      modelId: CONFIG.BEDROCK_MODEL_ID,
      contentType: 'application/json',
      accept: 'application/json',
      body: JSON.stringify({
        anthropic_version: 'bedrock-2023-05-31',
        max_tokens: 1000,
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
      const analysis = JSON.parse(jsonMatch[0]);
      
      if (analysis.hasRelationship) {
        return {
          type: analysis.type,
          confidence: analysis.confidence,
          reasoning: analysis.reasoning,
          bidirectional: analysis.bidirectional,
          strength: analysis.strength,
          impactLevel: analysis.impactLevel
        };
      }
    }
    
    return null;
    
  } catch (error) {
    console.error('Failed to analyze requirement pair:', error);
    
    // Fallback to rule-based analysis
    return analyzeRequirementPairFallback(req1, req2);
  }
}

/**
 * Fallback rule-based relationship analysis
 */
function analyzeRequirementPairFallback(req1, req2) {
  const text1 = (req1.description || req1.text || '').toLowerCase();
  const text2 = (req2.description || req2.text || '').toLowerCase();
  
  // Simple keyword-based relationship detection
  const dependencyKeywords = ['depend', 'require', 'need', 'prerequisite'];
  const refinementKeywords = ['detail', 'specific', 'elaborate', 'expand'];
  const conflictKeywords = ['conflict', 'contradict', 'oppose', 'mutually exclusive'];
  
  // Check for dependencies
  if (dependencyKeywords.some(keyword => 
    text1.includes(keyword) || text2.includes(keyword)
  )) {
    return {
      type: RELATIONSHIP_TYPES.DEPENDS_ON,
      confidence: 0.6,
      reasoning: 'Detected dependency keywords',
      bidirectional: false
    };
  }
  
  // Check for refinements
  if (refinementKeywords.some(keyword => 
    text1.includes(keyword) || text2.includes(keyword)
  )) {
    return {
      type: RELATIONSHIP_TYPES.REFINES,
      confidence: 0.6,
      reasoning: 'Detected refinement keywords',
      bidirectional: false
    };
  }
  
  // Check for conflicts
  if (conflictKeywords.some(keyword => 
    text1.includes(keyword) || text2.includes(keyword)
  )) {
    return {
      type: RELATIONSHIP_TYPES.CONFLICTS_WITH,
      confidence: 0.7,
      reasoning: 'Detected conflict keywords',
      bidirectional: true
    };
  }
  
  // Check for similar requirements (potential duplicates)
  const words1 = new Set(text1.split(/\s+/));
  const words2 = new Set(text2.split(/\s+/));
  const intersection = new Set([...words1].filter(x => words2.has(x)));
  const union = new Set([...words1, ...words2]);
  const similarity = intersection.size / union.size;
  
  if (similarity > 0.5) {
    return {
      type: RELATIONSHIP_TYPES.SUPPORTS,
      confidence: similarity,
      reasoning: `High text similarity (${(similarity * 100).toFixed(1)}%)`,
      bidirectional: true
    };
  }
  
  return null;
}

/**
 * Build traceability matrix
 */
async function buildMatrix(requirements, relationships) {
  const matrix = {
    requirements: requirements.map(req => ({
      id: req.id,
      text: req.description || req.text,
      type: req.type,
      priority: req.priority,
      sourceDocument: req.sourceDocumentTitle
    })),
    relationships: relationships.map(rel => ({
      id: rel.id,
      source: rel.sourceRequirement.id,
      target: rel.targetRequirement.id,
      type: rel.relationshipType,
      confidence: rel.confidence,
      bidirectional: rel.bidirectional
    })),
    matrix: {}
  };
  
  // Build adjacency matrix
  const reqIds = requirements.map(r => r.id);
  
  for (const sourceId of reqIds) {
    matrix.matrix[sourceId] = {};
    for (const targetId of reqIds) {
      matrix.matrix[sourceId][targetId] = null;
    }
  }
  
  // Populate matrix with relationships
  for (const relationship of relationships) {
    const sourceId = relationship.sourceRequirement.id;
    const targetId = relationship.targetRequirement.id;
    
    matrix.matrix[sourceId][targetId] = {
      type: relationship.relationshipType,
      confidence: relationship.confidence
    };
    
    if (relationship.bidirectional) {
      matrix.matrix[targetId][sourceId] = {
        type: relationship.relationshipType,
        confidence: relationship.confidence
      };
    }
  }
  
  return matrix;
}

/**
 * Analyze traceability coverage
 */
async function analyzeCoverage(requirements, relationships) {
  const coverage = {
    overall: {
      totalRequirements: requirements.length,
      trackedRequirements: 0,
      orphanedRequirements: [],
      coveragePercentage: 0
    },
    byType: {},
    byPriority: {},
    gaps: [],
    recommendations: []
  };
  
  // Track which requirements have relationships
  const trackedRequirements = new Set();
  
  for (const relationship of relationships) {
    trackedRequirements.add(relationship.sourceRequirement.id);
    trackedRequirements.add(relationship.targetRequirement.id);
  }
  
  coverage.overall.trackedRequirements = trackedRequirements.size;
  coverage.overall.coveragePercentage = (trackedRequirements.size / requirements.length) * 100;
  
  // Find orphaned requirements
  for (const requirement of requirements) {
    if (!trackedRequirements.has(requirement.id)) {
      coverage.overall.orphanedRequirements.push({
        id: requirement.id,
        text: requirement.description || requirement.text,
        type: requirement.type,
        priority: requirement.priority
      });
    }
  }
  
  // Analyze coverage by type
  const typeGroups = groupRequirementsByType(requirements);
  for (const [type, typeReqs] of Object.entries(typeGroups)) {
    const trackedInType = typeReqs.filter(req => trackedRequirements.has(req.id)).length;
    coverage.byType[type] = {
      total: typeReqs.length,
      tracked: trackedInType,
      percentage: (trackedInType / typeReqs.length) * 100
    };
  }
  
  // Analyze coverage by priority
  const priorityGroups = groupRequirementsByPriority(requirements);
  for (const [priority, priorityReqs] of Object.entries(priorityGroups)) {
    const trackedInPriority = priorityReqs.filter(req => trackedRequirements.has(req.id)).length;
    coverage.byPriority[priority] = {
      total: priorityReqs.length,
      tracked: trackedInPriority,
      percentage: (trackedInPriority / priorityReqs.length) * 100
    };
  }
  
  // Identify coverage gaps
  if (coverage.overall.coveragePercentage < 80) {
    coverage.gaps.push({
      type: 'low_overall_coverage',
      description: `Only ${coverage.overall.coveragePercentage.toFixed(1)}% of requirements are traced`,
      severity: 'high'
    });
  }
  
  // Check for missing test relationships
  const functionalReqs = requirements.filter(req => req.type === 'functional');
  const testRelationships = relationships.filter(rel => rel.relationshipType === RELATIONSHIP_TYPES.TESTS);
  
  if (testRelationships.length < functionalReqs.length * 0.5) {
    coverage.gaps.push({
      type: 'insufficient_test_coverage',
      description: 'Many functional requirements lack test traceability',
      severity: 'medium'
    });
  }
  
  // Generate recommendations
  if (coverage.overall.orphanedRequirements.length > 0) {
    coverage.recommendations.push({
      type: 'address_orphaned_requirements',
      priority: 'high',
      description: `Review ${coverage.overall.orphanedRequirements.length} orphaned requirements and establish traceability`
    });
  }
  
  return coverage;
}

/**
 * Analyze impact of requirement changes
 */
async function analyzeImpact(requestBody, context) {
  const { requirementId, changeDescription, options = {} } = requestBody;
  
  if (!requirementId) {
    return {
      statusCode: 400,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        error: 'Invalid parameters',
        message: 'Requirement ID is required'
      })
    };
  }
  
  try {
    const impactAnalysisId = uuidv4();
    const result = await performImpactAnalysis({
      impactAnalysisId,
      requirementId,
      changeDescription,
      options,
      requestId: context.awsRequestId
    });
    
    return {
      statusCode: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(result)
    };
    
  } catch (error) {
    console.error('Impact analysis failed:', error);
    throw error;
  }
}

/**
 * Perform comprehensive impact analysis
 */
async function performImpactAnalysis(params) {
  const { impactAnalysisId, requirementId, changeDescription, options = {} } = params;
  
  console.log(`Starting impact analysis ${impactAnalysisId} for requirement ${requirementId}`);
  
  try {
    // Load the requirement
    const requirement = await loadRequirement(requirementId);
    
    // Find all related requirements
    const relatedRequirements = await findRelatedRequirements(requirementId, options.maxDepth || CONFIG.MAX_ANALYSIS_DEPTH);
    
    // Analyze direct impacts
    const directImpacts = await analyzeDirectImpacts(requirement, relatedRequirements, changeDescription);
    
    // Analyze cascading impacts
    const cascadingImpacts = await analyzeCascadingImpacts(requirement, relatedRequirements, directImpacts, options);
    
    // Assess risk levels
    const riskAssessment = await assessImpactRisks(requirement, directImpacts, cascadingImpacts);
    
    // Generate mitigation strategies
    const mitigationStrategies = await generateMitigationStrategies(requirement, directImpacts, cascadingImpacts, riskAssessment);
    
    const impactAnalysis = {
      impactAnalysisId,
      requirementId,
      changeDescription,
      timestamp: new Date().toISOString(),
      requirement: {
        id: requirement.id,
        text: requirement.description || requirement.text,
        type: requirement.type,
        priority: requirement.priority
      },
      impacts: {
        direct: directImpacts,
        cascading: cascadingImpacts,
        summary: {
          totalAffectedRequirements: new Set([...directImpacts.map(i => i.requirementId), ...cascadingImpacts.map(i => i.requirementId)]).size,
          highRiskImpacts: [...directImpacts, ...cascadingImpacts].filter(i => i.riskLevel === 'high').length,
          estimatedEffort: calculateTotalEffort(directImpacts, cascadingImpacts)
        }
      },
      riskAssessment,
      mitigationStrategies,
      metadata: {
        analysisDepth: options.maxDepth || CONFIG.MAX_ANALYSIS_DEPTH,
        model: CONFIG.BEDROCK_MODEL_ID,
        version: '1.0.0'
      }
    };
    
    // Save impact analysis
    await saveImpactAnalysis(impactAnalysis);
    
    // Send notifications for high-risk impacts
    if (riskAssessment.overallRisk === 'high' && CONFIG.NOTIFICATIONS_TOPIC) {
      await sendImpactNotification(impactAnalysis);
    }
    
    console.log(`Impact analysis ${impactAnalysisId} completed`);
    return impactAnalysis;
    
  } catch (error) {
    console.error(`Impact analysis ${impactAnalysisId} failed:`, error);
    throw error;
  }
}

/**
 * Load a specific requirement
 */
async function loadRequirement(requirementId) {
  try {
    const result = await dynamodb.get({
      TableName: CONFIG.REQUIREMENTS_TABLE,
      Key: { id: requirementId }
    }).promise();
    
    if (!result.Item) {
      throw new Error(`Requirement ${requirementId} not found`);
    }
    
    return result.Item;
    
  } catch (error) {
    console.error(`Failed to load requirement ${requirementId}:`, error);
    throw error;
  }
}

/**
 * Find related requirements using graph traversal
 */
async function findRelatedRequirements(requirementId, maxDepth = 3) {
  const visited = new Set();
  const related = [];
  const queue = [{ id: requirementId, depth: 0 }];
  
  while (queue.length > 0) {
    const { id, depth } = queue.shift();
    
    if (visited.has(id) || depth > maxDepth) {
      continue;
    }
    
    visited.add(id);
    
    if (id !== requirementId) {
      const requirement = await loadRequirement(id);
      related.push({ ...requirement, relationshipDepth: depth });
    }
    
    // Find relationships for this requirement
    const relationships = await getRequirementRelationshipsFromDB(id);
    
    for (const relationship of relationships) {
      const nextId = relationship.sourceRequirement.id === id ? 
        relationship.targetRequirement.id : relationship.sourceRequirement.id;
      
      if (!visited.has(nextId)) {
        queue.push({ id: nextId, depth: depth + 1 });
      }
    }
  }
  
  return related;
}

/**
 * Get requirement relationships from database
 */
async function getRequirementRelationshipsFromDB(requirementId) {
  try {
    // Query relationships where this requirement is the source
    const sourceResult = await dynamodb.query({
      TableName: CONFIG.TRACEABILITY_TABLE,
      IndexName: 'SourceRequirementIndex',
      KeyConditionExpression: 'sourceRequirementId = :reqId',
      ExpressionAttributeValues: {
        ':reqId': requirementId
      }
    }).promise();
    
    // Query relationships where this requirement is the target
    const targetResult = await dynamodb.query({
      TableName: CONFIG.TRACEABILITY_TABLE,
      IndexName: 'TargetRequirementIndex',
      KeyConditionExpression: 'targetRequirementId = :reqId',
      ExpressionAttributeValues: {
        ':reqId': requirementId
      }
    }).promise();
    
    return [...(sourceResult.Items || []), ...(targetResult.Items || [])];
    
  } catch (error) {
    console.error(`Failed to get relationships for ${requirementId}:`, error);
    return [];
  }
}

/**
 * Analyze direct impacts
 */
async function analyzeDirectImpacts(requirement, relatedRequirements, changeDescription) {
  const directImpacts = [];
  
  // Get directly connected requirements
  const directlyConnected = relatedRequirements.filter(req => req.relationshipDepth === 1);
  
  for (const relatedReq of directlyConnected) {
    const impact = await analyzeSpecificImpact(requirement, relatedReq, changeDescription, 'direct');
    if (impact && impact.severity >= CONFIG.IMPACT_THRESHOLD) {
      directImpacts.push(impact);
    }
  }
  
  return directImpacts;
}

/**
 * Analyze cascading impacts
 */
async function analyzeCascadingImpacts(requirement, relatedRequirements, directImpacts, options = {}) {
  const cascadingImpacts = [];
  
  // Get indirectly connected requirements
  const indirectlyConnected = relatedRequirements.filter(req => req.relationshipDepth > 1);
  
  for (const relatedReq of indirectlyConnected) {
    const impact = await analyzeSpecificImpact(requirement, relatedReq, null, 'cascading');
    if (impact && impact.severity >= CONFIG.IMPACT_THRESHOLD) {
      cascadingImpacts.push(impact);
    }
  }
  
  return cascadingImpacts;
}

/**
 * Analyze specific impact between two requirements
 */
async function analyzeSpecificImpact(sourceRequirement, targetRequirement, changeDescription, impactType) {
  // Simplified impact analysis - in production, this would use more sophisticated AI analysis
  const impactScore = calculateImpactScore(sourceRequirement, targetRequirement);
  
  if (impactScore < CONFIG.IMPACT_THRESHOLD) {
    return null;
  }
  
  return {
    requirementId: targetRequirement.id,
    requirementText: targetRequirement.description || targetRequirement.text,
    impactType,
    severity: impactScore,
    riskLevel: impactScore > 0.7 ? 'high' : impactScore > 0.4 ? 'medium' : 'low',
    estimatedEffort: estimateChangeEffort(targetRequirement, impactScore),
    reasoning: `Potential impact due to ${impactType} relationship`,
    mitigationRequired: impactScore > 0.6
  };
}

/**
 * Calculate impact score between requirements
 */
function calculateImpactScore(sourceReq, targetReq) {
  // Simple scoring based on requirement characteristics
  let score = 0.3; // Base score
  
  // Priority influence
  if (sourceReq.priority === 'high' || targetReq.priority === 'high') {
    score += 0.2;
  }
  
  // Type influence
  if (sourceReq.type === 'functional' && targetReq.type === 'functional') {
    score += 0.2;
  }
  
  // Text similarity (simplified)
  const text1 = (sourceReq.description || sourceReq.text || '').toLowerCase();
  const text2 = (targetReq.description || targetReq.text || '').toLowerCase();
  
  const words1 = new Set(text1.split(/\s+/));
  const words2 = new Set(text2.split(/\s+/));
  const intersection = new Set([...words1].filter(x => words2.has(x)));
  const similarity = intersection.size / Math.max(words1.size, words2.size);
  
  score += similarity * 0.3;
  
  return Math.min(score, 1.0);
}

/**
 * Estimate change effort
 */
function estimateChangeEffort(requirement, impactScore) {
  const baseEffort = {
    'low': '1-2 hours',
    'medium': '4-8 hours',
    'high': '1-2 days'
  };
  
  const complexity = requirement.complexity || 'medium';
  const riskLevel = impactScore > 0.7 ? 'high' : impactScore > 0.4 ? 'medium' : 'low';
  
  return baseEffort[riskLevel] || baseEffort['medium'];
}

/**
 * Helper functions for grouping and calculations
 */
function groupRequirementsByType(requirements) {
  return requirements.reduce((groups, req) => {
    const type = req.type || 'unknown';
    if (!groups[type]) groups[type] = [];
    groups[type].push(req);
    return groups;
  }, {});
}

function groupRequirementsByPriority(requirements) {
  return requirements.reduce((groups, req) => {
    const priority = req.priority || 'medium';
    if (!groups[priority]) groups[priority] = [];
    groups[priority].push(req);
    return groups;
  }, {});
}

function groupRelationshipsByType(relationships) {
  return relationships.reduce((groups, rel) => {
    const type = rel.relationshipType || 'unknown';
    if (!groups[type]) groups[type] = 0;
    groups[type]++;
    return groups;
  }, {});
}

function calculateAverageConfidence(relationships) {
  if (relationships.length === 0) return 0;
  return relationships.reduce((sum, rel) => sum + rel.confidence, 0) / relationships.length;
}

function calculateTotalEffort(directImpacts, cascadingImpacts) {
  // Simplified effort calculation
  const totalImpacts = directImpacts.length + cascadingImpacts.length;
  
  if (totalImpacts <= 5) return 'Low (1-2 days)';
  if (totalImpacts <= 15) return 'Medium (1-2 weeks)';
  return 'High (2-4 weeks)';
}

/**
 * Generate traceability insights
 */
async function generateTraceabilityInsights(matrix, coverage) {
  return {
    keyFindings: [
      {
        type: 'coverage',
        description: `${coverage.overall.coveragePercentage.toFixed(1)}% of requirements have traceability`,
        impact: coverage.overall.coveragePercentage < 80 ? 'high' : 'low'
      },
      {
        type: 'orphaned',
        description: `${coverage.overall.orphanedRequirements.length} requirements lack traceability`,
        impact: coverage.overall.orphanedRequirements.length > 0 ? 'medium' : 'low'
      }
    ],
    recommendations: coverage.recommendations,
    qualityScore: Math.round(coverage.overall.coveragePercentage)
  };
}

/**
 * Save analysis results
 */
async function saveTraceabilityAnalysis(analysis) {
  try {
    await dynamodb.put({
      TableName: CONFIG.TRACEABILITY_TABLE,
      Item: {
        ...analysis,
        ttl: Math.floor(Date.now() / 1000) + (90 * 24 * 60 * 60) // 90 days TTL
      }
    }).promise();
    
  } catch (error) {
    console.error('Failed to save traceability analysis:', error);
    throw error;
  }
}

/**
 * Save impact analysis
 */
async function saveImpactAnalysis(analysis) {
  try {
    await dynamodb.put({
      TableName: CONFIG.IMPACT_ANALYSIS_TABLE,
      Item: {
        ...analysis,
        ttl: Math.floor(Date.now() / 1000) + (60 * 24 * 60 * 60) // 60 days TTL
      }
    }).promise();
    
  } catch (error) {
    console.error('Failed to save impact analysis:', error);
    throw error;
  }
}

/**
 * Send notifications
 */
async function sendTraceabilityNotification(analysis) {
  try {
    const message = {
      type: 'traceability_analysis_complete',
      analysisId: analysis.matrixId,
      documentCount: analysis.documentIds.length,
      requirementCount: analysis.requirements.total,
      coveragePercentage: analysis.coverage.overall.coveragePercentage,
      timestamp: new Date().toISOString()
    };
    
    await sns.publish({
      TopicArn: CONFIG.NOTIFICATIONS_TOPIC,
      Message: JSON.stringify(message),
      Subject: `Traceability Analysis Complete - ${analysis.coverage.overall.coveragePercentage.toFixed(1)}% Coverage`
    }).promise();
    
  } catch (error) {
    console.error('Failed to send traceability notification:', error);
  }
}

/**
 * Send impact analysis notification
 */
async function sendImpactNotification(analysis) {
  try {
    const message = {
      type: 'high_risk_impact_detected',
      analysisId: analysis.impactAnalysisId,
      requirementId: analysis.requirementId,
      affectedRequirements: analysis.impacts.summary.totalAffectedRequirements,
      riskLevel: analysis.riskAssessment.overallRisk,
      timestamp: new Date().toISOString()
    };
    
    await sns.publish({
      TopicArn: CONFIG.NOTIFICATIONS_TOPIC,
      Message: JSON.stringify(message),
      Subject: `High Risk Impact Detected - Requirement ${analysis.requirementId}`
    }).promise();
    
  } catch (error) {
    console.error('Failed to send impact notification:', error);
  }
}

// Additional placeholder functions for API endpoints
async function loadExistingRelationships(requirementIds) { return []; }
async function assessImpactRisks(requirement, directImpacts, cascadingImpacts) { 
  return { overallRisk: 'medium', factors: [] }; 
}
async function generateMitigationStrategies(requirement, directImpacts, cascadingImpacts, riskAssessment) { 
  return []; 
}
async function getRequirementTrace(requirementId, options) { return { statusCode: 200, body: JSON.stringify({}) }; }
async function getImpactAnalysis(requirementId, options) { return { statusCode: 200, body: JSON.stringify({}) }; }
async function getRequirementRelationships(requirementId) { return { statusCode: 200, body: JSON.stringify({}) }; }
async function getTraceabilityMatrix(options) { return { statusCode: 200, body: JSON.stringify({}) }; }
async function getTraceabilityCoverage(options) { return { statusCode: 200, body: JSON.stringify({}) }; }
async function createRelationship(requestBody, context) { return { statusCode: 201, body: JSON.stringify({}) }; }
async function updateRelationship(relationshipId, requestBody) { return { statusCode: 200, body: JSON.stringify({}) }; }
async function deleteRelationship(relationshipId) { return { statusCode: 200, body: JSON.stringify({}) }; }
async function handleBatchProcessing(event) { return { statusCode: 200, body: JSON.stringify({}) }; }