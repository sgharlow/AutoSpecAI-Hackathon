#!/bin/bash

# AutoSpec.AI Comprehensive Test Runner
# Executes the complete testing suite with proper environment setup

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT="test"
TEST_TYPE="all"
SKIP_SETUP=false
PARALLEL=true
COVERAGE=true
CLEANUP=true
REPORT_FORMAT="html"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    -e|--environment)
      ENVIRONMENT="$2"
      shift 2
      ;;
    -t|--type)
      TEST_TYPE="$2"
      shift 2
      ;;
    --skip-setup)
      SKIP_SETUP=true
      shift
      ;;
    --no-parallel)
      PARALLEL=false
      shift
      ;;
    --no-coverage)
      COVERAGE=false
      shift
      ;;
    --no-cleanup)
      CLEANUP=false
      shift
      ;;
    --report)
      REPORT_FORMAT="$2"
      shift 2
      ;;
    -h|--help)
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  -e, --environment ENV    Test environment (dev|staging|prod) [default: test]"
      echo "  -t, --type TYPE         Test type (unit|integration|e2e|performance|security|all) [default: all]"
      echo "  --skip-setup           Skip test environment setup"
      echo "  --no-parallel          Run tests sequentially"
      echo "  --no-coverage          Skip coverage collection"
      echo "  --no-cleanup           Skip cleanup after tests"
      echo "  --report FORMAT        Report format (html|json|junit) [default: html]"
      echo "  -h, --help             Show this help message"
      echo ""
      echo "Examples:"
      echo "  $0 --type unit --environment dev"
      echo "  $0 --type e2e --no-cleanup"
      echo "  $0 --type performance --environment staging"
      exit 0
      ;;
    *)
      echo "Unknown option $1"
      exit 1
      ;;
  esac
done

# Function to print colored output
print_status() {
  local status=$1
  local message=$2
  case $status in
    "INFO")
      echo -e "${BLUE}[INFO]${NC} $message"
      ;;
    "SUCCESS")
      echo -e "${GREEN}[SUCCESS]${NC} $message"
      ;;
    "WARNING")
      echo -e "${YELLOW}[WARNING]${NC} $message"
      ;;
    "ERROR")
      echo -e "${RED}[ERROR]${NC} $message"
      ;;
  esac
}

# Function to check prerequisites
check_prerequisites() {
  print_status "INFO" "Checking prerequisites..."
  
  # Check Node.js version
  if ! command -v node &> /dev/null; then
    print_status "ERROR" "Node.js is not installed"
    exit 1
  fi
  
  local node_version=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
  if [ "$node_version" -lt 16 ]; then
    print_status "ERROR" "Node.js version 16 or higher is required (current: $(node --version))"
    exit 1
  fi
  
  # Check npm
  if ! command -v npm &> /dev/null; then
    print_status "ERROR" "npm is not installed"
    exit 1
  fi
  
  # Check AWS CLI (for integration tests)
  if [ "$TEST_TYPE" = "integration" ] || [ "$TEST_TYPE" = "all" ]; then
    if ! command -v aws &> /dev/null; then
      print_status "WARNING" "AWS CLI not found - some integration tests may fail"
    fi
  fi
  
  # Check Docker (for E2E tests)
  if [ "$TEST_TYPE" = "e2e" ] || [ "$TEST_TYPE" = "all" ]; then
    if ! command -v docker &> /dev/null; then
      print_status "WARNING" "Docker not found - containerized tests will be skipped"
    fi
  fi
  
  print_status "SUCCESS" "Prerequisites check completed"
}

# Function to setup test environment
setup_environment() {
  if [ "$SKIP_SETUP" = true ]; then
    print_status "INFO" "Skipping environment setup"
    return
  fi
  
  print_status "INFO" "Setting up test environment: $ENVIRONMENT"
  
  # Set environment variables
  export NODE_ENV="test"
  export TEST_ENVIRONMENT="$ENVIRONMENT"
  export CI=${CI:-false}
  
  # Load environment-specific configuration
  if [ -f ".env.test" ]; then
    print_status "INFO" "Loading test environment variables"
    set -a
    source .env.test
    set +a
  fi
  
  # Install dependencies if needed
  if [ ! -d "node_modules" ] || [ "package.json" -nt "node_modules/.package-lock.json" ]; then
    print_status "INFO" "Installing dependencies..."
    npm ci --silent
  fi
  
  # Install testing dependencies
  if [ ! -d "testing/node_modules" ]; then
    print_status "INFO" "Installing testing dependencies..."
    cd testing
    npm ci --silent
    cd ..
  fi
  
  # Setup test data
  print_status "INFO" "Setting up test data..."
  npm run --prefix testing setup:test-data
  
  print_status "SUCCESS" "Environment setup completed"
}

# Function to run unit tests
run_unit_tests() {
  print_status "INFO" "Running unit tests..."
  
  local coverage_flag=""
  if [ "$COVERAGE" = true ]; then
    coverage_flag="--coverage"
  fi
  
  local parallel_flag=""
  if [ "$PARALLEL" = false ]; then
    parallel_flag="--runInBand"
  fi
  
  cd testing
  npm run test:unit $coverage_flag $parallel_flag
  local exit_code=$?
  cd ..
  
  if [ $exit_code -eq 0 ]; then
    print_status "SUCCESS" "Unit tests passed"
  else
    print_status "ERROR" "Unit tests failed"
    return $exit_code
  fi
}

# Function to run integration tests
run_integration_tests() {
  print_status "INFO" "Running integration tests..."
  
  # Start test services if needed
  if [ "$ENVIRONMENT" != "prod" ]; then
    print_status "INFO" "Starting test services..."
    # This would start localstack, test databases, etc.
    # docker-compose -f docker-compose.test.yml up -d
  fi
  
  cd testing
  npm run test:integration
  local exit_code=$?
  cd ..
  
  if [ $exit_code -eq 0 ]; then
    print_status "SUCCESS" "Integration tests passed"
  else
    print_status "ERROR" "Integration tests failed"
    return $exit_code
  fi
}

# Function to run E2E tests
run_e2e_tests() {
  print_status "INFO" "Running end-to-end tests..."
  
  # Start application if needed
  local app_pid=""
  if [ "$ENVIRONMENT" = "test" ]; then
    print_status "INFO" "Starting application for E2E tests..."
    npm start &
    app_pid=$!
    
    # Wait for application to be ready
    print_status "INFO" "Waiting for application to start..."
    for i in {1..30}; do
      if curl -s http://localhost:3000 > /dev/null; then
        break
      fi
      sleep 2
    done
  fi
  
  cd testing
  npm run test:e2e
  local exit_code=$?
  cd ..
  
  # Stop application if we started it
  if [ ! -z "$app_pid" ]; then
    print_status "INFO" "Stopping test application..."
    kill $app_pid 2>/dev/null || true
  fi
  
  if [ $exit_code -eq 0 ]; then
    print_status "SUCCESS" "E2E tests passed"
  else
    print_status "ERROR" "E2E tests failed"
    return $exit_code
  fi
}

# Function to run performance tests
run_performance_tests() {
  print_status "INFO" "Running performance tests..."
  
  # Performance tests require a running application
  if [ "$ENVIRONMENT" = "test" ]; then
    print_status "INFO" "Starting application for performance tests..."
    npm start &
    local app_pid=$!
    
    # Wait for application to be ready
    sleep 10
  fi
  
  cd testing
  npm run test:performance
  local exit_code=$?
  cd ..
  
  # Stop application if we started it
  if [ ! -z "$app_pid" ]; then
    kill $app_pid 2>/dev/null || true
  fi
  
  if [ $exit_code -eq 0 ]; then
    print_status "SUCCESS" "Performance tests passed"
  else
    print_status "ERROR" "Performance tests failed"
    return $exit_code
  fi
}

# Function to run security tests
run_security_tests() {
  print_status "INFO" "Running security tests..."
  
  cd testing
  npm run test:security
  local exit_code=$?
  cd ..
  
  if [ $exit_code -eq 0 ]; then
    print_status "SUCCESS" "Security tests passed"
  else
    print_status "ERROR" "Security tests failed"
    return $exit_code
  fi
}

# Function to run accessibility tests
run_accessibility_tests() {
  print_status "INFO" "Running accessibility tests..."
  
  # Start application if needed
  local app_pid=""
  if [ "$ENVIRONMENT" = "test" ]; then
    npm start &
    app_pid=$!
    sleep 10
  fi
  
  cd testing
  npm run test:accessibility
  local exit_code=$?
  cd ..
  
  # Stop application if we started it
  if [ ! -z "$app_pid" ]; then
    kill $app_pid 2>/dev/null || true
  fi
  
  if [ $exit_code -eq 0 ]; then
    print_status "SUCCESS" "Accessibility tests passed"
  else
    print_status "ERROR" "Accessibility tests failed"
    return $exit_code
  fi
}

# Function to run compliance tests
run_compliance_tests() {
  print_status "INFO" "Running compliance tests..."
  
  cd testing
  npm run compliance:gdpr
  local gdpr_exit=$?
  
  npm run compliance:accessibility
  local a11y_exit=$?
  cd ..
  
  if [ $gdpr_exit -eq 0 ] && [ $a11y_exit -eq 0 ]; then
    print_status "SUCCESS" "Compliance tests passed"
  else
    print_status "ERROR" "Compliance tests failed"
    return 1
  fi
}

# Function to generate test reports
generate_reports() {
  print_status "INFO" "Generating test reports..."
  
  cd testing
  npm run report:generate -- --format $REPORT_FORMAT
  local exit_code=$?
  cd ..
  
  if [ $exit_code -eq 0 ]; then
    print_status "SUCCESS" "Test reports generated"
    print_status "INFO" "Reports available in testing/test-results/"
  else
    print_status "WARNING" "Report generation failed"
  fi
}

# Function to cleanup test environment
cleanup_environment() {
  if [ "$CLEANUP" = false ]; then
    print_status "INFO" "Skipping cleanup"
    return
  fi
  
  print_status "INFO" "Cleaning up test environment..."
  
  # Cleanup test data
  cd testing
  npm run cleanup:test-data || true
  cd ..
  
  # Stop any running services
  # docker-compose -f docker-compose.test.yml down || true
  
  # Clean temporary files
  rm -rf tmp/test-* || true
  
  print_status "SUCCESS" "Cleanup completed"
}

# Main execution flow
main() {
  print_status "INFO" "Starting AutoSpec.AI Test Suite"
  print_status "INFO" "Environment: $ENVIRONMENT"
  print_status "INFO" "Test Type: $TEST_TYPE"
  print_status "INFO" "Coverage: $COVERAGE"
  print_status "INFO" "Parallel: $PARALLEL"
  
  # Check prerequisites
  check_prerequisites
  
  # Setup environment
  setup_environment
  
  # Track overall test results
  local overall_exit=0
  
  # Run tests based on type
  case $TEST_TYPE in
    "unit")
      run_unit_tests || overall_exit=$?
      ;;
    "integration")
      run_integration_tests || overall_exit=$?
      ;;
    "e2e")
      run_e2e_tests || overall_exit=$?
      ;;
    "performance")
      run_performance_tests || overall_exit=$?
      ;;
    "security")
      run_security_tests || overall_exit=$?
      ;;
    "accessibility")
      run_accessibility_tests || overall_exit=$?
      ;;
    "compliance")
      run_compliance_tests || overall_exit=$?
      ;;
    "all")
      print_status "INFO" "Running complete test suite..."
      
      run_unit_tests || overall_exit=$?
      
      if [ $overall_exit -eq 0 ]; then
        run_integration_tests || overall_exit=$?
      fi
      
      if [ $overall_exit -eq 0 ]; then
        run_e2e_tests || overall_exit=$?
      fi
      
      if [ $overall_exit -eq 0 ]; then
        run_performance_tests || overall_exit=$?
      fi
      
      if [ $overall_exit -eq 0 ]; then
        run_security_tests || overall_exit=$?
      fi
      
      if [ $overall_exit -eq 0 ]; then
        run_accessibility_tests || overall_exit=$?
      fi
      
      if [ $overall_exit -eq 0 ]; then
        run_compliance_tests || overall_exit=$?
      fi
      ;;
    *)
      print_status "ERROR" "Unknown test type: $TEST_TYPE"
      exit 1
      ;;
  esac
  
  # Generate reports
  generate_reports
  
  # Cleanup
  cleanup_environment
  
  # Final status
  if [ $overall_exit -eq 0 ]; then
    print_status "SUCCESS" "All tests completed successfully!"
    print_status "INFO" "Test execution completed in $(date)"
  else
    print_status "ERROR" "Some tests failed!"
    print_status "INFO" "Check the test results and logs for details"
  fi
  
  exit $overall_exit
}

# Run main function
main "$@"