#!/usr/bin/env node
const cdk = require('aws-cdk-lib');
const { AutoSpecAIStack } = require('./lib/autospec-ai-stack');
const { loadConfig } = require('./lib/config-loader');

// Load environment configuration
const environment = process.env.ENVIRONMENT || 'prod';
const config = loadConfig(environment);

console.log(`Loading configuration for environment: ${environment}`);

const app = new cdk.App();

// Create stack with environment-specific configuration
new AutoSpecAIStack(app, `AutoSpecAI-${environment}`, {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT || process.env.AWS_ACCOUNT_ID,
    region: process.env.CDK_DEFAULT_REGION || 'us-east-1',
  },
  config: config,
  environment: environment,
});