#!/usr/bin/env python3
"""
AutoSpec.AI Dual Upload System Test Suite
Tests both JSON and S3 direct upload methods
"""

import requests
import base64
import os
import json
import time
import argparse
from typing import Dict, Any, Optional
import tempfile

# Configuration
API_URL = "https://nlkg4e7zo4.execute-api.us-east-1.amazonaws.com/prod"
# Get API key from environment variable
API_KEY = os.environ.get('AUTOSPEC_API_KEY', '')

if not API_KEY:
    print("❌ Error: API key not configured!")
    print("Please set the AUTOSPEC_API_KEY environment variable:")
    print("  export AUTOSPEC_API_KEY='your-api-key'")
    sys.exit(1)
TIMEOUT = 30

class UploadTester:
    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url
        self.api_key = api_key
        self.headers = {
            'X-API-Key': api_key,
            'Content-Type': 'application/json'
        }
        self.test_results = []
    
    def log_test(self, test_name: str, status: str, details: str = ""):
        """Log test results"""
        result = {
            'test': test_name,
            'status': status,
            'details': details,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        self.test_results.append(result)
        
        status_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_icon} {test_name}: {status}")
        if details:
            print(f"   {details}")
    
    def test_health_check(self) -> bool:
        """Test system health"""
        try:
            response = requests.get(f"{self.api_url}/v1/health", headers=self.headers, timeout=TIMEOUT)
            if response.status_code == 200:
                health_data = response.json()
                if health_data.get('status') == 'healthy':
                    self.log_test("Health Check", "PASS", f"All services healthy: {health_data.get('services', {})}")
                    return True
                else:
                    self.log_test("Health Check", "FAIL", f"System not healthy: {health_data}")
                    return False
            else:
                self.log_test("Health Check", "FAIL", f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Health Check", "FAIL", f"Exception: {str(e)}")
            return False
    
    def create_test_file(self, size_kb: int) -> str:
        """Create a test file of specified size"""
        content = "This is a test document for AutoSpec.AI upload testing.\n" * (size_kb * 10)
        
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
        temp_file.write(content)
        temp_file.close()
        
        return temp_file.name
    
    def test_json_upload(self) -> bool:
        """Test JSON upload method (small files)"""
        try:
            # Create a small test file (1KB)
            test_file_path = self.create_test_file(1)
            
            with open(test_file_path, 'rb') as f:
                file_content = base64.b64encode(f.read()).decode('utf-8')
            
            payload = {
                'file_content': file_content,
                'filename': 'test_small_file.txt',
                'sender_email': 'test@autospec.ai',
                'preferences': {
                    'quality': 'high',
                    'formats': ['json', 'html']
                }
            }
            
            response = requests.post(
                f"{self.api_url}/v1/upload",
                headers=self.headers,
                json=payload,
                timeout=TIMEOUT
            )
            
            os.unlink(test_file_path)  # Clean up
            
            if response.status_code in [200, 201, 202]:
                response_data = response.json()
                request_id = response_data.get('request_id')
                if request_id:
                    self.log_test("JSON Upload", "PASS", f"Request ID: {request_id}")
                    return request_id
                else:
                    self.log_test("JSON Upload", "FAIL", "No request_id in response")
                    return False
            else:
                self.log_test("JSON Upload", "FAIL", f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("JSON Upload", "FAIL", f"Exception: {str(e)}")
            return False
    
    def test_s3_upload_initiate(self) -> Optional[Dict[str, Any]]:
        """Test S3 upload initiate endpoint"""
        try:
            payload = {
                'filename': 'test_large_file.txt',
                'file_size': 6 * 1024 * 1024,  # 6MB
                'content_type': 'text/plain',
                'metadata': {
                    'sender_email': 'test@autospec.ai',
                    'preferences': {
                        'quality': 'premium',
                        'formats': ['json', 'html', 'pdf']
                    }
                }
            }
            
            response = requests.post(
                f"{self.api_url}/v1/upload/initiate",
                headers=self.headers,
                json=payload,
                timeout=TIMEOUT
            )
            
            if response.status_code == 200:
                response_data = response.json()
                required_fields = ['request_id', 'upload_url', 'upload_headers']
                
                if all(field in response_data for field in required_fields):
                    self.log_test("S3 Upload Initiate", "PASS", f"Request ID: {response_data['request_id']}")
                    return response_data
                else:
                    missing = [f for f in required_fields if f not in response_data]
                    self.log_test("S3 Upload Initiate", "FAIL", f"Missing fields: {missing}")
                    return None
            else:
                self.log_test("S3 Upload Initiate", "FAIL", f"HTTP {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            self.log_test("S3 Upload Initiate", "FAIL", f"Exception: {str(e)}")
            return None
    
    def test_s3_upload_to_s3(self, upload_data: Dict[str, Any]) -> bool:
        """Test actual upload to S3 using pre-signed URL"""
        try:
            # Create a larger test file (6MB)
            test_file_path = self.create_test_file(6000)  # 6MB
            
            upload_url = upload_data['upload_url']
            content_type = upload_data['upload_headers']['Content-Type']
            file_size = os.path.getsize(test_file_path)
            
            with open(test_file_path, 'rb') as f:
                response = requests.put(
                    upload_url,
                    headers={
                        'Content-Type': content_type,
                        'Content-Length': str(file_size)
                    },
                    data=f,
                    timeout=120  # Longer timeout for large file
                )
            
            os.unlink(test_file_path)  # Clean up
            
            if response.status_code == 200:
                self.log_test("S3 Upload to S3", "PASS", f"File uploaded successfully ({file_size} bytes)")
                return True
            else:
                self.log_test("S3 Upload to S3", "FAIL", f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("S3 Upload to S3", "FAIL", f"Exception: {str(e)}")
            return False
    
    def test_s3_upload_complete(self, request_id: str) -> bool:
        """Test S3 upload completion endpoint"""
        try:
            payload = {
                'request_id': request_id
            }
            
            response = requests.post(
                f"{self.api_url}/v1/upload/complete",
                headers=self.headers,
                json=payload,
                timeout=TIMEOUT
            )
            
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get('status') == 'upload_verified':
                    size_match = response_data.get('size_match', False)
                    actual_size = response_data.get('actual_size', 0)
                    self.log_test("S3 Upload Complete", "PASS", 
                                f"Upload verified, size match: {size_match}, actual size: {actual_size}")
                    return True
                else:
                    self.log_test("S3 Upload Complete", "FAIL", f"Unexpected status: {response_data}")
                    return False
            else:
                self.log_test("S3 Upload Complete", "FAIL", f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("S3 Upload Complete", "FAIL", f"Exception: {str(e)}")
            return False
    
    def test_status_endpoint(self, request_id: str) -> bool:
        """Test status endpoint for any upload method"""
        try:
            response = requests.get(
                f"{self.api_url}/v1/status/{request_id}",
                headers=self.headers,
                timeout=TIMEOUT
            )
            
            if response.status_code == 200:
                status_data = response.json()
                current_status = status_data.get('status', 'unknown')
                stage = status_data.get('processing_stage', 'unknown')
                progress = status_data.get('progress_percentage', 0)
                
                self.log_test("Status Check", "PASS", 
                            f"Status: {current_status}, Stage: {stage}, Progress: {progress}%")
                return True
            else:
                self.log_test("Status Check", "FAIL", f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Status Check", "FAIL", f"Exception: {str(e)}")
            return False
    
    def test_formats_endpoint(self) -> bool:
        """Test formats endpoint"""
        try:
            response = requests.get(f"{self.api_url}/v1/formats", headers=self.headers, timeout=TIMEOUT)
            
            if response.status_code == 200:
                formats_data = response.json()
                input_formats = formats_data.get('supported_input_formats', [])
                output_formats = formats_data.get('output_formats', [])
                
                if input_formats and output_formats:
                    self.log_test("Formats Endpoint", "PASS", 
                                f"Input formats: {len(input_formats)}, Output formats: {len(output_formats)}")
                    return True
                else:
                    self.log_test("Formats Endpoint", "FAIL", "Missing format information")
                    return False
            else:
                self.log_test("Formats Endpoint", "FAIL", f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Formats Endpoint", "FAIL", f"Exception: {str(e)}")
            return False
    
    def run_full_test_suite(self) -> Dict[str, Any]:
        """Run complete test suite for both upload methods"""
        print("🚀 AutoSpec.AI Dual Upload System Test Suite")
        print("=" * 50)
        print()
        
        # Test 1: Health Check
        health_ok = self.test_health_check()
        
        # Test 2: Formats Endpoint
        formats_ok = self.test_formats_endpoint()
        
        # Test 3: JSON Upload Method
        json_request_id = self.test_json_upload()
        json_upload_ok = bool(json_request_id)
        
        # Test 4: JSON Upload Status Check
        json_status_ok = False
        if json_request_id:
            json_status_ok = self.test_status_endpoint(json_request_id)
        
        # Test 5: S3 Upload Method
        s3_initiate_data = self.test_s3_upload_initiate()
        s3_initiate_ok = bool(s3_initiate_data)
        
        s3_upload_ok = False
        s3_complete_ok = False
        s3_status_ok = False
        
        if s3_initiate_data:
            # Test 6: S3 Upload to S3
            s3_upload_ok = self.test_s3_upload_to_s3(s3_initiate_data)
            
            if s3_upload_ok:
                # Test 7: S3 Upload Complete
                s3_complete_ok = self.test_s3_upload_complete(s3_initiate_data['request_id'])
                
                # Test 8: S3 Upload Status Check
                s3_status_ok = self.test_status_endpoint(s3_initiate_data['request_id'])
        
        # Summary
        print()
        print("📊 Test Summary")
        print("=" * 30)
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['status'] == 'PASS'])
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        # Detailed results
        print()
        print("🔍 Detailed Results:")
        for result in self.test_results:
            status_icon = "✅" if result['status'] == 'PASS' else "❌"
            print(f"{status_icon} {result['test']}: {result['status']}")
            if result['details']:
                print(f"   └─ {result['details']}")
        
        return {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'success_rate': (passed_tests/total_tests)*100,
            'results': self.test_results,
            'json_upload_works': json_upload_ok and json_status_ok,
            's3_upload_works': s3_initiate_ok and s3_upload_ok and s3_complete_ok and s3_status_ok,
            'system_healthy': health_ok
        }

def main():
    parser = argparse.ArgumentParser(description='Test AutoSpec.AI dual upload system')
    parser.add_argument('--api-url', default=API_URL, help='API base URL')
    parser.add_argument('--api-key', default=API_KEY, help='API key for authentication')
    parser.add_argument('--output', help='Output file for test results (JSON)')
    
    args = parser.parse_args()
    
    tester = UploadTester(args.api_url, args.api_key)
    results = tester.run_full_test_suite()
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n📁 Results saved to: {args.output}")
    
    # Exit with appropriate code
    if results['success_rate'] >= 80:
        print(f"\n🎉 Tests completed successfully! ({results['success_rate']:.1f}% pass rate)")
        exit(0)
    else:
        print(f"\n❌ Tests failed! ({results['success_rate']:.1f}% pass rate)")
        exit(1)

if __name__ == "__main__":
    main()