/**
 * Intelligent Document Routing and Classification Lambda
 * Automatically routes documents to appropriate workflows and teams using AI analysis
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
  DOCUMENTS_TABLE: process.env.DOCUMENTS_TABLE || 'autospec-ai-documents',
  ROUTING_TABLE: process.env.ROUTING_TABLE || 'autospec-ai-routing',
  WORKFLOWS_TABLE: process.env.WORKFLOWS_TABLE || 'autospec-ai-workflows',
  TEAMS_TABLE: process.env.TEAMS_TABLE || 'autospec-ai-teams',
  ROUTING_RULES_TABLE: process.env.ROUTING_RULES_TABLE || 'autospec-ai-routing-rules',
  NOTIFICATIONS_TOPIC: process.env.NOTIFICATIONS_TOPIC,
  WORKFLOW_STATE_MACHINE: process.env.WORKFLOW_STATE_MACHINE,
  BEDROCK_MODEL_ID: 'anthropic.claude-3-sonnet-20240229-v1:0',
  CONFIDENCE_THRESHOLD: 0.7,
  MAX_ROUTING_DEPTH: 3
};

// Document classification categories
const CLASSIFICATION_CATEGORIES = {
  DOCUMENT_TYPE: [
    'requirements_specification',
    'system_design',
    'api_documentation',
    'user_manual',
    'test_plan',
    'architecture_document',
    'business_requirements',
    'technical_specification',
    'compliance_document',
    'process_documentation'
  ],
  DOMAIN: [
    'frontend',
    'backend',
    'database',
    'security',
    'infrastructure',
    'mobile',
    'integration',
    'analytics',
    'compliance',
    'user_experience'
  ],
  PRIORITY: [
    'critical',
    'high',
    'medium',
    'low'
  ],
  COMPLEXITY: [
    'simple',
    'moderate',
    'complex',
    'enterprise'
  ]
};

/**
 * Main Lambda handler for intelligent routing
 */
exports.handler = async (event, context) => {
  console.log('Intelligent Routing - Event:', JSON.stringify(event, null, 2));
  
  try {
    // Handle different event sources
    if (event.Records) {
      // SNS/SQS triggered routing
      return await handleQueuedRouting(event);
    } else if (event.httpMethod) {
      // API Gateway triggered routing
      return await handleAPIRouting(event, context);
    } else if (event.source === 'aws.s3') {
      // S3 triggered routing (document upload)
      return await handleDocumentUpload(event);
    } else {
      // Direct invocation
      return await performIntelligentRouting(event);
    }
  } catch (error) {
    console.error('Intelligent routing failed:', error);
    
    return {
      statusCode: 500,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*'
      },
      body: JSON.stringify({
        error: 'Intelligent routing failed',
        message: error.message,
        requestId: context.awsRequestId
      })
    };
  }
};

/**
 * Handle API Gateway triggered routing requests
 */
async function handleAPIRouting(event, context) {
  const { httpMethod, pathParameters, body, queryStringParameters } = event;
  
  switch (httpMethod) {
    case 'POST':
      if (pathParameters && pathParameters.action === 'route') {
        return await routeDocument(JSON.parse(body || '{}'), context);
      } else if (pathParameters && pathParameters.action === 'classify') {
        return await classifyDocument(JSON.parse(body || '{}'), context);
      } else if (pathParameters && pathParameters.action === 'rules') {
        return await createRoutingRule(JSON.parse(body || '{}'), context);
      }
      break;
      
    case 'GET':
      if (pathParameters && pathParameters.documentId) {
        return await getRoutingHistory(pathParameters.documentId);
      } else if (pathParameters && pathParameters.action === 'rules') {
        return await listRoutingRules(queryStringParameters || {});
      } else if (pathParameters && pathParameters.action === 'analytics') {
        return await getRoutingAnalytics(queryStringParameters || {});
      }
      break;
      
    case 'PUT':
      if (pathParameters && pathParameters.ruleId) {
        return await updateRoutingRule(pathParameters.ruleId, JSON.parse(body || '{}'));
      }
      break;
      
    case 'DELETE':
      if (pathParameters && pathParameters.ruleId) {
        return await deleteRoutingRule(pathParameters.ruleId);
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
 * Route a document to appropriate workflows and teams
 */
async function routeDocument(requestBody, context) {
  const { documentId, options = {} } = requestBody;
  
  if (!documentId) {
    return {
      statusCode: 400,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        error: 'Missing required parameter',
        message: 'documentId is required'
      })
    };
  }
  
  try {
    const routingResult = await performIntelligentRouting({
      documentId,
      options,
      requestId: context.awsRequestId
    });
    
    return {
      statusCode: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(routingResult)
    };
    
  } catch (error) {
    console.error('Document routing failed:', error);
    throw error;
  }
}

/**
 * Perform intelligent routing analysis
 */
async function performIntelligentRouting(params) {
  const { documentId, options = {}, requestId } = params;
  
  console.log(`Starting intelligent routing for document ${documentId}`);
  
  try {
    // Load document
    const document = await loadDocument(documentId);
    
    // Classify document
    const classification = await classifyDocumentContent(document, options);
    
    // Apply routing rules
    const routingRules = await getApplicableRoutingRules(classification);
    
    // Generate routing recommendations
    const recommendations = await generateRoutingRecommendations(document, classification, routingRules);
    
    // Execute automatic routing if enabled
    const executionResults = [];
    if (options.autoExecute !== false) {
      for (const recommendation of recommendations.automaticRoutes) {
        try {
          const result = await executeRouting(document, recommendation);
          executionResults.push(result);
        } catch (error) {
          console.error(`Failed to execute routing for ${recommendation.type}:`, error);
          executionResults.push({ error: error.message, recommendation });
        }
      }
    }
    
    // Save routing analysis
    const routingRecord = {
      id: uuidv4(),
      documentId,
      classification,
      recommendations,
      executionResults,
      timestamp: new Date().toISOString(),
      requestId
    };
    
    await saveRoutingRecord(routingRecord);
    
    // Send notifications
    if (CONFIG.NOTIFICATIONS_TOPIC) {
      await sendRoutingNotifications(document, routingRecord);
    }
    
    console.log(`Intelligent routing completed for document ${documentId}`);
    
    return {
      routingId: routingRecord.id,
      documentId,
      classification,
      recommendations,
      executionResults,
      summary: generateRoutingSummary(routingRecord)
    };
    
  } catch (error) {
    console.error(`Intelligent routing failed for document ${documentId}:`, error);
    throw error;
  }
}

/**
 * Classify document content using AI
 */
async function classifyDocumentContent(document, options = {}) {
  const prompt = `
As an expert document classifier, analyze this document and provide detailed classification in JSON format.

Document Information:
Title: ${document.title}
Type: ${document.type}
Content Preview: ${(document.processedContent || document.content || '').substring(0, 5000)}...

Classify this document according to the following categories and provide confidence scores (0-1):

1. Document Type: ${CLASSIFICATION_CATEGORIES.DOCUMENT_TYPE.join(', ')}
2. Domain: ${CLASSIFICATION_CATEGORIES.DOMAIN.join(', ')}
3. Priority: ${CLASSIFICATION_CATEGORIES.PRIORITY.join(', ')}
4. Complexity: ${CLASSIFICATION_CATEGORIES.COMPLEXITY.join(', ')}

Provide classification in this JSON format:
{
  "documentType": {
    "primary": "requirements_specification",
    "confidence": 0.85,
    "alternatives": [
      {"type": "system_design", "confidence": 0.15}
    ]
  },
  "domain": {
    "primary": "backend",
    "confidence": 0.90,
    "alternatives": [
      {"type": "database", "confidence": 0.25}
    ]
  },
  "priority": {
    "primary": "high",
    "confidence": 0.75,
    "reasoning": "Contains critical security requirements"
  },
  "complexity": {
    "primary": "complex",
    "confidence": 0.80,
    "reasoning": "Multiple system integrations required"
  },
  "characteristics": {
    "requiresReview": true,
    "hasComplianceRequirements": false,
    "involvesSecurity": true,
    "requiresTechnicalExpertise": true,
    "estimatedReviewTime": "4-6 hours",
    "stakeholderTypes": ["technical_lead", "security_expert", "product_manager"]
  },
  "contentAnalysis": {
    "keyTopics": ["authentication", "authorization", "data_encryption"],
    "technicalConcepts": ["API", "database", "microservices"],
    "businessConcepts": ["user_experience", "compliance", "performance"]
  },
  "routingRecommendations": {
    "primaryTeam": "backend_development",
    "reviewerRoles": ["senior_developer", "security_architect"],
    "workflowType": "technical_review",
    "urgency": "medium"
  }
}

Focus on accurate classification based on content analysis.
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
    const classificationText = responseBody.content[0].text;
    
    // Extract JSON from the response
    const jsonMatch = classificationText.match(/\{[\s\S]*\}/);
    if (jsonMatch) {
      const classification = JSON.parse(jsonMatch[0]);
      
      // Add metadata
      classification.metadata = {
        classifiedAt: new Date().toISOString(),
        model: CONFIG.BEDROCK_MODEL_ID,
        version: '1.0.0',
        documentId: document.id
      };
      
      return classification;
    } else {
      throw new Error('Invalid JSON response from Bedrock');
    }
    
  } catch (error) {
    console.error('Document classification failed:', error);
    
    // Fallback to rule-based classification
    return generateFallbackClassification(document);
  }
}

/**
 * Generate fallback classification using rule-based approach
 */
function generateFallbackClassification(document) {
  const content = (document.processedContent || document.content || '').toLowerCase();
  const title = document.title.toLowerCase();
  
  // Simple rule-based classification
  let documentType = 'technical_specification';
  let domain = 'backend';
  let priority = 'medium';
  let complexity = 'moderate';
  
  // Document type detection
  if (title.includes('requirement') || content.includes('shall') || content.includes('must')) {
    documentType = 'requirements_specification';
  } else if (title.includes('design') || content.includes('architecture')) {
    documentType = 'system_design';
  } else if (title.includes('api') || content.includes('endpoint')) {
    documentType = 'api_documentation';
  } else if (title.includes('test') || content.includes('testing')) {
    documentType = 'test_plan';
  }
  
  // Domain detection
  if (content.includes('frontend') || content.includes('ui') || content.includes('react')) {
    domain = 'frontend';
  } else if (content.includes('database') || content.includes('sql')) {
    domain = 'database';
  } else if (content.includes('security') || content.includes('authentication')) {
    domain = 'security';
  } else if (content.includes('mobile') || content.includes('ios') || content.includes('android')) {
    domain = 'mobile';
  }
  
  // Priority detection
  if (content.includes('critical') || content.includes('urgent') || content.includes('security')) {
    priority = 'high';
  } else if (content.includes('nice to have') || content.includes('future')) {
    priority = 'low';
  }
  
  // Complexity detection
  const complexityIndicators = [
    'integration', 'microservice', 'distributed', 'enterprise',
    'scalability', 'performance', 'compliance', 'migration'
  ];
  
  const complexityScore = complexityIndicators.filter(indicator => 
    content.includes(indicator)
  ).length;
  
  if (complexityScore >= 3) {
    complexity = 'enterprise';
  } else if (complexityScore >= 2) {
    complexity = 'complex';
  } else if (complexityScore === 0) {
    complexity = 'simple';
  }
  
  return {
    documentType: {
      primary: documentType,
      confidence: 0.6,
      alternatives: []
    },
    domain: {
      primary: domain,
      confidence: 0.6,
      alternatives: []
    },
    priority: {
      primary: priority,
      confidence: 0.6,
      reasoning: 'Rule-based classification'
    },
    complexity: {
      primary: complexity,
      confidence: 0.6,
      reasoning: 'Based on complexity indicators'
    },
    characteristics: {
      requiresReview: true,
      hasComplianceRequirements: content.includes('compliance') || content.includes('gdpr'),
      involvesSecurity: content.includes('security') || content.includes('auth'),
      requiresTechnicalExpertise: complexity !== 'simple',
      estimatedReviewTime: complexity === 'enterprise' ? '6-8 hours' : '2-4 hours',
      stakeholderTypes: ['technical_lead']
    },
    contentAnalysis: {
      keyTopics: [],
      technicalConcepts: [],
      businessConcepts: []
    },
    routingRecommendations: {
      primaryTeam: domain + '_team',
      reviewerRoles: ['senior_developer'],
      workflowType: 'standard_review',
      urgency: priority === 'high' ? 'high' : 'medium'
    },
    metadata: {
      classifiedAt: new Date().toISOString(),
      model: 'rule_based_fallback',
      version: '1.0.0',
      documentId: document.id
    }
  };
}

/**
 * Get applicable routing rules based on classification
 */
async function getApplicableRoutingRules(classification) {
  try {
    // Get all active routing rules
    const result = await dynamodb.scan({
      TableName: CONFIG.ROUTING_RULES_TABLE,
      FilterExpression: '#status = :status',
      ExpressionAttributeNames: {
        '#status': 'status'
      },
      ExpressionAttributeValues: {
        ':status': 'active'
      }
    }).promise();
    
    const allRules = result.Items || [];
    const applicableRules = [];
    
    // Filter rules based on classification
    for (const rule of allRules) {
      if (isRuleApplicable(rule, classification)) {
        applicableRules.push({
          ...rule,
          matchScore: calculateRuleMatchScore(rule, classification)
        });
      }
    }
    
    // Sort by match score (highest first)
    applicableRules.sort((a, b) => b.matchScore - a.matchScore);
    
    return applicableRules;
    
  } catch (error) {
    console.error('Failed to get routing rules:', error);
    return [];
  }
}

/**
 * Check if a routing rule is applicable to the classification
 */
function isRuleApplicable(rule, classification) {
  const conditions = rule.conditions || {};
  
  // Check document type condition
  if (conditions.documentType && conditions.documentType !== classification.documentType.primary) {
    return false;
  }
  
  // Check domain condition
  if (conditions.domain && conditions.domain !== classification.domain.primary) {
    return false;
  }
  
  // Check priority condition
  if (conditions.priority && conditions.priority !== classification.priority.primary) {
    return false;
  }
  
  // Check complexity condition
  if (conditions.complexity && conditions.complexity !== classification.complexity.primary) {
    return false;
  }
  
  // Check characteristics conditions
  if (conditions.characteristics) {
    for (const [key, value] of Object.entries(conditions.characteristics)) {
      if (classification.characteristics[key] !== value) {
        return false;
      }
    }
  }
  
  // Check minimum confidence threshold
  const minConfidence = rule.minConfidence || 0.5;
  if (classification.documentType.confidence < minConfidence) {
    return false;
  }
  
  return true;
}

/**
 * Calculate rule match score based on classification
 */
function calculateRuleMatchScore(rule, classification) {
  let score = 0;
  
  // Base score from classification confidence
  score += classification.documentType.confidence * 0.3;
  score += classification.domain.confidence * 0.3;
  score += classification.priority.confidence * 0.2;
  score += classification.complexity.confidence * 0.2;
  
  // Bonus for exact matches
  if (rule.conditions?.documentType === classification.documentType.primary) {
    score += 0.1;
  }
  if (rule.conditions?.domain === classification.domain.primary) {
    score += 0.1;
  }
  
  // Rule priority weight
  const priorityWeights = { high: 1.2, medium: 1.0, low: 0.8 };
  score *= priorityWeights[rule.priority] || 1.0;
  
  return Math.min(score, 1.0);
}

/**
 * Generate routing recommendations
 */
async function generateRoutingRecommendations(document, classification, routingRules) {
  const recommendations = {
    automaticRoutes: [],
    suggestedRoutes: [],
    manualReviewRequired: false,
    reasoning: []
  };
  
  // Apply routing rules
  for (const rule of routingRules.slice(0, 5)) { // Limit to top 5 rules
    try {
      const routeRecommendation = await applyRoutingRule(document, classification, rule);
      
      if (rule.autoExecute && routeRecommendation.confidence >= CONFIG.CONFIDENCE_THRESHOLD) {
        recommendations.automaticRoutes.push(routeRecommendation);
      } else {
        recommendations.suggestedRoutes.push(routeRecommendation);
      }
      
      recommendations.reasoning.push({
        rule: rule.name,
        reason: routeRecommendation.reasoning,
        confidence: routeRecommendation.confidence
      });
      
    } catch (error) {
      console.error(`Failed to apply routing rule ${rule.name}:`, error);
    }
  }
  
  // Add AI-generated recommendations
  const aiRecommendations = generateAIRecommendations(classification);
  recommendations.suggestedRoutes.push(...aiRecommendations);
  
  // Determine if manual review is required
  recommendations.manualReviewRequired = (
    classification.characteristics.requiresReview ||
    classification.complexity.primary === 'enterprise' ||
    classification.priority.primary === 'critical' ||
    recommendations.automaticRoutes.length === 0
  );
  
  return recommendations;
}

/**
 * Apply a specific routing rule
 */
async function applyRoutingRule(document, classification, rule) {
  const actions = rule.actions || {};
  const routeRecommendation = {
    ruleId: rule.id,
    ruleName: rule.name,
    type: actions.type || 'workflow',
    target: actions.target,
    parameters: actions.parameters || {},
    confidence: rule.matchScore || 0.5,
    reasoning: rule.description || 'Routing rule applied',
    estimatedDuration: actions.estimatedDuration,
    priority: actions.priority || classification.priority.primary
  };
  
  // Customize parameters based on classification
  if (actions.type === 'workflow') {
    routeRecommendation.parameters.documentId = document.id;
    routeRecommendation.parameters.classification = classification;
    routeRecommendation.parameters.assignees = await getRecommendedAssignees(classification, actions);
  } else if (actions.type === 'team_assignment') {
    routeRecommendation.parameters.teamId = actions.target;
    routeRecommendation.parameters.role = actions.role || 'reviewer';
  } else if (actions.type === 'notification') {
    routeRecommendation.parameters.recipients = await getNotificationRecipients(classification, actions);
    routeRecommendation.parameters.template = actions.template;
  }
  
  return routeRecommendation;
}

/**
 * Generate AI-based routing recommendations
 */
function generateAIRecommendations(classification) {
  const recommendations = [];
  
  // Workflow recommendation
  const workflowType = determineWorkflowType(classification);
  if (workflowType) {
    recommendations.push({
      type: 'workflow',
      target: workflowType,
      confidence: 0.8,
      reasoning: `AI-recommended based on ${classification.documentType.primary} classification`,
      parameters: {
        workflowType,
        priority: classification.priority.primary,
        estimatedDuration: classification.characteristics.estimatedReviewTime
      }
    });
  }
  
  // Team assignment recommendation
  const primaryTeam = classification.routingRecommendations?.primaryTeam;
  if (primaryTeam) {
    recommendations.push({
      type: 'team_assignment',
      target: primaryTeam,
      confidence: classification.domain.confidence,
      reasoning: `AI-recommended based on ${classification.domain.primary} domain`,
      parameters: {
        teamId: primaryTeam,
        role: 'primary_reviewer'
      }
    });
  }
  
  // Expert review recommendation
  if (classification.characteristics.requiresTechnicalExpertise) {
    recommendations.push({
      type: 'expert_review',
      target: 'technical_experts',
      confidence: 0.9,
      reasoning: 'Technical expertise required based on document complexity',
      parameters: {
        expertiseAreas: classification.contentAnalysis?.technicalConcepts || [],
        reviewType: 'technical_review'
      }
    });
  }
  
  return recommendations;
}

/**
 * Determine appropriate workflow type
 */
function determineWorkflowType(classification) {
  const docType = classification.documentType.primary;
  const complexity = classification.complexity.primary;
  const priority = classification.priority.primary;
  
  if (docType === 'requirements_specification') {
    return complexity === 'enterprise' ? 'enterprise_requirements_review' : 'requirements_review';
  } else if (docType === 'system_design') {
    return 'architecture_review';
  } else if (docType === 'api_documentation') {
    return 'api_review';
  } else if (docType === 'test_plan') {
    return 'test_review';
  } else if (priority === 'critical') {
    return 'expedited_review';
  } else {
    return 'standard_review';
  }
}

/**
 * Execute routing recommendation
 */
async function executeRouting(document, recommendation) {
  console.log(`Executing routing: ${recommendation.type} for document ${document.id}`);
  
  try {
    switch (recommendation.type) {
      case 'workflow':
        return await startWorkflow(document, recommendation);
        
      case 'team_assignment':
        return await assignToTeam(document, recommendation);
        
      case 'notification':
        return await sendNotification(document, recommendation);
        
      case 'expert_review':
        return await requestExpertReview(document, recommendation);
        
      default:
        throw new Error(`Unknown routing type: ${recommendation.type}`);
    }
  } catch (error) {
    console.error(`Failed to execute routing ${recommendation.type}:`, error);
    throw error;
  }
}

/**
 * Start a workflow
 */
async function startWorkflow(document, recommendation) {
  if (!CONFIG.WORKFLOW_STATE_MACHINE) {
    throw new Error('Workflow state machine not configured');
  }
  
  const workflowInput = {
    documentId: document.id,
    workflowType: recommendation.target,
    classification: recommendation.parameters.classification,
    priority: recommendation.priority,
    assignees: recommendation.parameters.assignees || [],
    metadata: {
      routingId: recommendation.ruleId,
      startedBy: 'intelligent_routing',
      startedAt: new Date().toISOString()
    }
  };
  
  try {
    const response = await stepfunctions.startExecution({
      stateMachineArn: CONFIG.WORKFLOW_STATE_MACHINE,
      name: `workflow-${document.id}-${Date.now()}`,
      input: JSON.stringify(workflowInput)
    }).promise();
    
    return {
      type: 'workflow',
      success: true,
      executionArn: response.executionArn,
      workflowType: recommendation.target,
      startedAt: new Date().toISOString()
    };
    
  } catch (error) {
    console.error('Failed to start workflow:', error);
    throw error;
  }
}

/**
 * Assign document to team
 */
async function assignToTeam(document, recommendation) {
  try {
    // Create team assignment record
    const assignment = {
      id: uuidv4(),
      documentId: document.id,
      teamId: recommendation.target,
      role: recommendation.parameters.role,
      assignedAt: new Date().toISOString(),
      status: 'pending',
      priority: recommendation.priority,
      routingRuleId: recommendation.ruleId
    };
    
    // Save assignment
    await dynamodb.put({
      TableName: CONFIG.WORKFLOWS_TABLE,
      Item: assignment
    }).promise();
    
    return {
      type: 'team_assignment',
      success: true,
      assignmentId: assignment.id,
      teamId: recommendation.target,
      assignedAt: assignment.assignedAt
    };
    
  } catch (error) {
    console.error('Failed to assign to team:', error);
    throw error;
  }
}

/**
 * Send notification
 */
async function sendNotification(document, recommendation) {
  try {
    const message = {
      type: 'document_routed',
      documentId: document.id,
      documentTitle: document.title,
      routingType: recommendation.type,
      target: recommendation.target,
      priority: recommendation.priority,
      timestamp: new Date().toISOString()
    };
    
    await sns.publish({
      TopicArn: CONFIG.NOTIFICATIONS_TOPIC,
      Message: JSON.stringify(message),
      Subject: `Document Routed: ${document.title}`
    }).promise();
    
    return {
      type: 'notification',
      success: true,
      sentAt: new Date().toISOString()
    };
    
  } catch (error) {
    console.error('Failed to send notification:', error);
    throw error;
  }
}

/**
 * Request expert review
 */
async function requestExpertReview(document, recommendation) {
  try {
    // Create expert review request
    const reviewRequest = {
      id: uuidv4(),
      documentId: document.id,
      reviewType: recommendation.parameters.reviewType,
      expertiseAreas: recommendation.parameters.expertiseAreas,
      requestedAt: new Date().toISOString(),
      status: 'pending',
      priority: recommendation.priority,
      routingRuleId: recommendation.ruleId
    };
    
    // Save review request
    await dynamodb.put({
      TableName: CONFIG.WORKFLOWS_TABLE,
      Item: reviewRequest
    }).promise();
    
    return {
      type: 'expert_review',
      success: true,
      reviewRequestId: reviewRequest.id,
      requestedAt: reviewRequest.requestedAt
    };
    
  } catch (error) {
    console.error('Failed to request expert review:', error);
    throw error;
  }
}

/**
 * Load document from DynamoDB
 */
async function loadDocument(documentId) {
  try {
    const result = await dynamodb.get({
      TableName: CONFIG.DOCUMENTS_TABLE,
      Key: { id: documentId }
    }).promise();
    
    if (!result.Item) {
      throw new Error(`Document ${documentId} not found`);
    }
    
    return result.Item;
    
  } catch (error) {
    console.error(`Failed to load document ${documentId}:`, error);
    throw error;
  }
}

/**
 * Save routing record
 */
async function saveRoutingRecord(routingRecord) {
  try {
    await dynamodb.put({
      TableName: CONFIG.ROUTING_TABLE,
      Item: routingRecord
    }).promise();
    
  } catch (error) {
    console.error('Failed to save routing record:', error);
    throw error;
  }
}

/**
 * Generate routing summary
 */
function generateRoutingSummary(routingRecord) {
  const { classification, recommendations, executionResults } = routingRecord;
  
  return {
    classifiedAs: classification.documentType.primary,
    domain: classification.domain.primary,
    priority: classification.priority.primary,
    automaticRoutesExecuted: executionResults.filter(r => r.success).length,
    manualReviewRequired: recommendations.manualReviewRequired,
    estimatedProcessingTime: classification.characteristics.estimatedReviewTime,
    confidence: Math.round(classification.documentType.confidence * 100)
  };
}

/**
 * Get recommended assignees (placeholder)
 */
async function getRecommendedAssignees(classification, actions) {
  // This would integrate with team management system
  return actions.defaultAssignees || [];
}

/**
 * Get notification recipients (placeholder)
 */
async function getNotificationRecipients(classification, actions) {
  // This would integrate with user management system
  return actions.defaultRecipients || [];
}

/**
 * Classify document (API endpoint)
 */
async function classifyDocument(requestBody, context) {
  const { documentId } = requestBody;
  
  if (!documentId) {
    return {
      statusCode: 400,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        error: 'Missing required parameter',
        message: 'documentId is required'
      })
    };
  }
  
  try {
    const document = await loadDocument(documentId);
    const classification = await classifyDocumentContent(document);
    
    return {
      statusCode: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        documentId,
        classification
      })
    };
    
  } catch (error) {
    console.error('Document classification failed:', error);
    throw error;
  }
}

/**
 * Send routing notifications
 */
async function sendRoutingNotifications(document, routingRecord) {
  try {
    const message = {
      type: 'document_routing_completed',
      documentId: document.id,
      documentTitle: document.title,
      classification: routingRecord.classification.documentType.primary,
      routesExecuted: routingRecord.executionResults.length,
      timestamp: new Date().toISOString()
    };
    
    await sns.publish({
      TopicArn: CONFIG.NOTIFICATIONS_TOPIC,
      Message: JSON.stringify(message),
      Subject: `Document Routing Complete: ${document.title}`
    }).promise();
    
  } catch (error) {
    console.error('Failed to send routing notifications:', error);
    // Don't throw error for notification failures
  }
}

/**
 * Handle queued routing requests
 */
async function handleQueuedRouting(event) {
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
      
      const result = await performIntelligentRouting(message);
      results.push(result);
      
    } catch (error) {
      console.error('Failed to process queued routing:', error);
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

/**
 * Handle document upload events
 */
async function handleDocumentUpload(event) {
  // Extract document ID from S3 event
  const bucket = event.Records[0].s3.bucket.name;
  const key = event.Records[0].s3.object.key;
  
  // Assume document ID is embedded in the key
  const documentId = key.split('/').pop().split('.')[0];
  
  if (documentId) {
    return await performIntelligentRouting({
      documentId,
      options: { autoExecute: true },
      source: 's3_upload'
    });
  }
  
  return { message: 'No document ID found in S3 key' };
}

// Additional API endpoints would be implemented here:
// - getRoutingHistory
// - listRoutingRules
// - createRoutingRule
// - updateRoutingRule
// - deleteRoutingRule
// - getRoutingAnalytics

/**
 * Get routing history for a document
 */
async function getRoutingHistory(documentId) {
  try {
    const result = await dynamodb.query({
      TableName: CONFIG.ROUTING_TABLE,
      IndexName: 'DocumentIdIndex',
      KeyConditionExpression: 'documentId = :documentId',
      ExpressionAttributeValues: {
        ':documentId': documentId
      },
      ScanIndexForward: false // Most recent first
    }).promise();
    
    return {
      statusCode: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        documentId,
        history: result.Items || []
      })
    };
    
  } catch (error) {
    console.error('Failed to get routing history:', error);
    throw error;
  }
}

/**
 * List routing rules
 */
async function listRoutingRules(queryParams) {
  try {
    const { limit = 20, status = 'active' } = queryParams;
    
    const result = await dynamodb.scan({
      TableName: CONFIG.ROUTING_RULES_TABLE,
      FilterExpression: '#status = :status',
      ExpressionAttributeNames: {
        '#status': 'status'
      },
      ExpressionAttributeValues: {
        ':status': status
      },
      Limit: parseInt(limit)
    }).promise();
    
    return {
      statusCode: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        rules: result.Items || [],
        count: result.Count
      })
    };
    
  } catch (error) {
    console.error('Failed to list routing rules:', error);
    throw error;
  }
}

/**
 * Create routing rule
 */
async function createRoutingRule(requestBody, context) {
  const rule = {
    id: uuidv4(),
    ...requestBody,
    status: 'active',
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    createdBy: context.identity?.userArn || 'system'
  };
  
  try {
    await dynamodb.put({
      TableName: CONFIG.ROUTING_RULES_TABLE,
      Item: rule
    }).promise();
    
    return {
      statusCode: 201,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(rule)
    };
    
  } catch (error) {
    console.error('Failed to create routing rule:', error);
    throw error;
  }
}