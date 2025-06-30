# Testing Notes for AutoSpec.AI

## Local Testing Limitations

Due to WSL environment constraints, local testing requires additional setup:

### Required System Dependencies
```bash
# For full local testing, install:
sudo apt install python3.12-venv python3-pip
```

### Testing Setup
```bash
cd lambdas/ingest
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m unittest test_ingest.py -v
```

## Lambda Function Testing

### Ingest Function Tests Created
- ✅ API upload success test
- ✅ File type detection test  
- ✅ MIME content type mapping test
- ✅ Text extraction test for TXT files
- ✅ Invalid JSON handling test
- ✅ SES event structure test

### Test Coverage
The test suite covers:
- API Gateway upload functionality
- File type detection (PDF, DOCX, TXT)
- Content type mapping
- Error handling for invalid requests
- SES event processing structure

### Integration Testing
For full integration testing, deploy to AWS and test:
1. API Gateway endpoint with actual file uploads
2. S3 event triggers to processing Lambda
3. DynamoDB metadata storage
4. SES email processing (when implemented)

## Next Steps
Tests are ready for execution once Python environment is properly configured or when deployed to AWS Lambda environment.