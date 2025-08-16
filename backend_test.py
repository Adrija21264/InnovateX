#!/usr/bin/env python3

import requests
import sys
import json
from datetime import datetime
from typing import Dict, Any

class DevOpsAutomationTester:
    def __init__(self, base_url="https://coldstart-solver.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name: str, success: bool, details: str = ""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED")
        else:
            print(f"❌ {name} - FAILED: {details}")
        
        self.test_results.append({
            "name": name,
            "success": success,
            "details": details
        })

    def test_api_endpoint(self, name: str, method: str, endpoint: str, expected_status: int = 200, data: Dict = None) -> tuple:
        """Test a single API endpoint"""
        url = f"{self.api_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method.upper() == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            else:
                self.log_test(name, False, f"Unsupported method: {method}")
                return False, {}

            success = response.status_code == expected_status
            response_data = {}
            
            if success:
                try:
                    response_data = response.json()
                    self.log_test(name, True, f"Status: {response.status_code}")
                except json.JSONDecodeError:
                    self.log_test(name, False, f"Invalid JSON response, Status: {response.status_code}")
                    return False, {}
            else:
                error_msg = f"Expected {expected_status}, got {response.status_code}"
                try:
                    error_detail = response.json()
                    error_msg += f" - {error_detail}"
                except:
                    error_msg += f" - {response.text[:200]}"
                self.log_test(name, False, error_msg)
                
            return success, response_data

        except requests.exceptions.Timeout:
            self.log_test(name, False, "Request timeout (30s)")
            return False, {}
        except requests.exceptions.ConnectionError:
            self.log_test(name, False, "Connection error - server may be down")
            return False, {}
        except Exception as e:
            self.log_test(name, False, f"Unexpected error: {str(e)}")
            return False, {}

    def test_root_endpoint(self):
        """Test the root API endpoint"""
        success, data = self.test_api_endpoint("Root API Endpoint", "GET", "")
        if success and "message" in data:
            print(f"   📝 Message: {data['message']}")
        return success

    def test_dashboard_endpoint(self):
        """Test dashboard data endpoint"""
        success, data = self.test_api_endpoint("Dashboard Data", "GET", "dashboard")
        if success:
            # Validate dashboard structure
            required_keys = ["cold_start_system", "connector_generator", "system_status"]
            missing_keys = [key for key in required_keys if key not in data]
            if missing_keys:
                self.log_test("Dashboard Structure Validation", False, f"Missing keys: {missing_keys}")
                return False
            else:
                self.log_test("Dashboard Structure Validation", True)
                print(f"   📊 Cold Start System - Recent Jobs: {data['cold_start_system']['recent_jobs']}")
                print(f"   🔌 Connector Generator - Available APIs: {len(data['connector_generator']['available_apis'])}")
                print(f"   🟢 System Status: {data['system_status']['prediction_engine']}")
        return success

    def test_mock_data_generation(self):
        """Test mock data generation"""
        success, data = self.test_api_endpoint("Generate Mock Data", "POST", "jobs/generate-mock-data")
        if success:
            if "total_records" in data and data["total_records"] > 0:
                print(f"   📈 Generated {data['total_records']} job records")
                if "job_types" in data:
                    print(f"   📋 Job Types: {dict(data['job_types'])}")
                if "date_range" in data:
                    print(f"   📅 Date Range: {data['date_range']['start']} to {data['date_range']['end']}")
                return True
            else:
                self.log_test("Mock Data Content Validation", False, "No records generated")
                return False
        return success

    def test_job_predictions(self):
        """Test job predictions endpoint"""
        success, data = self.test_api_endpoint("Job Predictions", "GET", "jobs/predictions")
        if success:
            if isinstance(data, list):
                print(f"   🔮 Found {len(data)} predictions")
                for i, pred in enumerate(data[:3]):  # Show first 3 predictions
                    if all(key in pred for key in ["job_id", "confidence_score", "action"]):
                        print(f"   📊 Prediction {i+1}: {pred['job_id']} - {pred['action']} ({pred['confidence_score']:.2f})")
                    else:
                        self.log_test("Prediction Structure Validation", False, f"Invalid prediction structure: {pred}")
                        return False
                self.log_test("Prediction Structure Validation", True)
            else:
                self.log_test("Predictions Response Type", False, "Expected list, got " + str(type(data)))
                return False
        return success

    def test_job_analytics(self):
        """Test job analytics endpoint"""
        success, data = self.test_api_endpoint("Job Analytics", "GET", "jobs/analytics")
        if success:
            if "analytics" in data and "summary" in data:
                analytics = data["analytics"]
                summary = data["summary"]
                print(f"   📊 Total Jobs Analyzed: {analytics.get('total_jobs', 0)}")
                print(f"   ✅ Success Rate: {analytics.get('success_rate', 0):.2%}")
                print(f"   🎯 Avg Prediction Confidence: {summary.get('prediction_confidence_avg', 0):.2%}")
                print(f"   🔥 Recommended Prewarms: {summary.get('recommended_prewarms', 0)}")
                
                if "job_types" in analytics:
                    print(f"   📋 Job Types Distribution: {dict(analytics['job_types'])}")
                
                self.log_test("Analytics Structure Validation", True)
            else:
                self.log_test("Analytics Structure Validation", False, "Missing analytics or summary")
                return False
        return success

    def test_available_apis(self):
        """Test available APIs endpoint"""
        success, data = self.test_api_endpoint("Available APIs", "GET", "connectors/available-apis")
        if success:
            if "available_apis" in data and "api_specs" in data:
                apis = data["available_apis"]
                specs = data["api_specs"]
                expected_apis = ["user_management", "billing", "monitoring", "crm"]
                
                print(f"   🔌 Found {len(apis)} APIs: {apis}")
                
                # Validate expected APIs are present
                missing_apis = [api for api in expected_apis if api not in apis]
                if missing_apis:
                    self.log_test("Expected APIs Validation", False, f"Missing APIs: {missing_apis}")
                    return False
                else:
                    self.log_test("Expected APIs Validation", True)
                
                # Validate API specs structure
                for api_name, spec in specs.items():
                    if not all(key in spec for key in ["name", "description", "endpoint_count"]):
                        self.log_test("API Spec Structure Validation", False, f"Invalid spec for {api_name}")
                        return False
                    print(f"   📋 {spec['name']}: {spec['endpoint_count']} endpoints")
                
                self.log_test("API Spec Structure Validation", True)
            else:
                self.log_test("Available APIs Structure", False, "Missing available_apis or api_specs")
                return False
        return success

    def test_connector_generation(self):
        """Test connector generation for each API"""
        apis_to_test = ["user_management", "billing", "monitoring", "crm"]
        all_success = True
        
        for api_name in apis_to_test:
            success, data = self.test_api_endpoint(f"Generate {api_name} Connector", "POST", f"connectors/{api_name}/generate")
            if success:
                # Validate connector structure
                required_fields = ["connector_code", "config_template", "documentation", "directory_structure"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_test(f"{api_name} Connector Structure", False, f"Missing fields: {missing_fields}")
                    all_success = False
                else:
                    self.log_test(f"{api_name} Connector Structure", True)
                    
                    # Check if connector code contains TypeScript
                    if "class" in data["connector_code"] and "TypeScript" in data["connector_code"]:
                        print(f"   💻 {api_name} connector contains TypeScript class")
                    
                    # Check documentation length
                    if len(data["documentation"]) > 100:
                        print(f"   📚 {api_name} documentation: {len(data['documentation'])} characters")
            else:
                all_success = False
        
        return all_success

    def test_connector_download(self):
        """Test connector download functionality"""
        success, data = self.test_api_endpoint("Download Connector Package", "GET", "connectors/user_management/download")
        if success:
            if "package_name" in data and "files" in data:
                print(f"   📦 Package: {data['package_name']}")
                print(f"   📁 Files: {len(data['files'])} files included")
                
                # Check for essential files
                essential_files = ["README.md", "package.json"]
                files = data["files"]
                missing_files = [f for f in essential_files if f not in files]
                
                if missing_files:
                    self.log_test("Download Package Files", False, f"Missing files: {missing_files}")
                    return False
                else:
                    self.log_test("Download Package Files", True)
                    
                # Validate package.json structure
                try:
                    package_json = json.loads(files["package.json"])
                    if "dependencies" in package_json and "axios" in package_json["dependencies"]:
                        print(f"   ✅ Package.json includes axios dependency")
                        self.log_test("Package.json Validation", True)
                    else:
                        self.log_test("Package.json Validation", False, "Missing axios dependency")
                        return False
                except json.JSONDecodeError:
                    self.log_test("Package.json Validation", False, "Invalid JSON in package.json")
                    return False
            else:
                self.log_test("Download Package Structure", False, "Missing package_name or files")
                return False
        return success

    def run_comprehensive_test(self):
        """Run all tests in sequence"""
        print("🚀 Starting DevOps Automation Platform API Tests")
        print(f"🌐 Testing against: {self.base_url}")
        print("=" * 60)
        
        # Test sequence - order matters for some tests
        test_sequence = [
            ("Root API", self.test_root_endpoint),
            ("Dashboard Data", self.test_dashboard_endpoint),
            ("Mock Data Generation", self.test_mock_data_generation),
            ("Job Predictions", self.test_job_predictions),
            ("Job Analytics", self.test_job_analytics),
            ("Available APIs", self.test_available_apis),
            ("Connector Generation", self.test_connector_generation),
            ("Connector Download", self.test_connector_download),
        ]
        
        for test_name, test_func in test_sequence:
            print(f"\n🔍 Testing {test_name}...")
            try:
                test_func()
            except Exception as e:
                self.log_test(test_name, False, f"Test execution error: {str(e)}")
            
        # Print final results
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"✅ Tests Passed: {self.tests_passed}")
        print(f"❌ Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"📈 Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        # Show failed tests
        failed_tests = [test for test in self.test_results if not test["success"]]
        if failed_tests:
            print(f"\n❌ FAILED TESTS ({len(failed_tests)}):")
            for test in failed_tests:
                print(f"   • {test['name']}: {test['details']}")
        
        return self.tests_passed == self.tests_run

def main():
    """Main test execution"""
    tester = DevOpsAutomationTester()
    
    try:
        success = tester.run_comprehensive_test()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Unexpected error during testing: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())