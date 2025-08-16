from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime, timedelta
import json
import random
import pandas as pd
import numpy as np
from collections import defaultdict, Counter
import asyncio

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# ===== MODELS =====

# Original Models
class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StatusCheckCreate(BaseModel):
    client_name: str

# Cold Start Prediction Models
class JobExecution(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    job_id: str
    timestamp: datetime
    duration_ms: int
    retries: int
    status: str  # success, failed, timeout
    compute_time_sec: float
    job_type: str  # cron, on_demand, bursty

class JobExecutionCreate(BaseModel):
    job_id: str
    timestamp: datetime
    duration_ms: int
    retries: int
    status: str
    compute_time_sec: float
    job_type: str

class PredictionResult(BaseModel):
    job_id: str
    predicted_run_time_window: str
    confidence_score: float
    action: str  # prewarm or skip
    reasoning: str

# API Connector Models
class APISpec(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    base_url: str
    endpoints: List[Dict[str, Any]]
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ConnectorRequest(BaseModel):
    api_name: str
    api_spec: Dict[str, Any]

class ConnectorResult(BaseModel):
    connector_code: str
    config_template: str
    documentation: str
    directory_structure: Dict[str, Any]

# ===== COLD START PREDICTION ENGINE =====

class ColdStartPredictor:
    def __init__(self):
        self.job_patterns = defaultdict(list)
        self.cron_patterns = {}
        self.burst_detection = defaultdict(list)
        
    async def analyze_job_history(self, job_executions: List[JobExecution]) -> Dict[str, Any]:
        """Analyze historical job data to find patterns"""
        analysis = {
            "total_jobs": len(job_executions),
            "job_types": Counter([job.job_type for job in job_executions]),
            "success_rate": len([job for job in job_executions if job.status == "success"]) / len(job_executions) if job_executions else 0,
            "patterns": {}
        }
        
        # Group by job_id for pattern analysis
        jobs_by_id = defaultdict(list)
        for job in job_executions:
            jobs_by_id[job.job_id].append(job)
            
        # Analyze patterns for each job
        for job_id, executions in jobs_by_id.items():
            executions.sort(key=lambda x: x.timestamp)
            analysis["patterns"][job_id] = self._analyze_job_pattern(executions)
            
        return analysis
    
    def _analyze_job_pattern(self, executions: List[JobExecution]) -> Dict[str, Any]:
        """Analyze pattern for a specific job"""
        if len(executions) < 2:
            return {"type": "insufficient_data", "confidence": 0.1}
            
        # Calculate intervals between executions
        intervals = []
        for i in range(1, len(executions)):
            diff = (executions[i].timestamp - executions[i-1].timestamp).total_seconds()
            intervals.append(diff)
            
        if not intervals:
            return {"type": "insufficient_data", "confidence": 0.1}
            
        # Detect pattern type
        avg_interval = np.mean(intervals)
        std_interval = np.std(intervals)
        
        # Cron pattern detection (regular intervals)
        if std_interval < avg_interval * 0.1 and len(executions) >= 3:
            return {
                "type": "cron",
                "interval_seconds": avg_interval,
                "confidence": 0.9,
                "next_predicted": executions[-1].timestamp + timedelta(seconds=avg_interval)
            }
            
        # Burst pattern detection (clusters of activity)
        if self._detect_burst_pattern(executions):
            return {
                "type": "bursty",
                "confidence": 0.7,
                "burst_indicators": True
            }
            
        # On-demand pattern (irregular but with some predictability)
        return {
            "type": "on_demand",
            "avg_interval": avg_interval,
            "confidence": 0.4,
            "variability": std_interval / avg_interval if avg_interval > 0 else 1
        }
    
    def _detect_burst_pattern(self, executions: List[JobExecution]) -> bool:
        """Detect if job shows burst behavior"""
        if len(executions) < 5:
            return False
            
        # Check for clusters of executions within short time windows
        time_windows = []
        window_size = timedelta(minutes=10)
        
        for exec in executions:
            window_start = exec.timestamp
            window_end = window_start + window_size
            count = sum(1 for e in executions if window_start <= e.timestamp <= window_end)
            time_windows.append(count)
            
        # If any window has 3+ executions, consider it bursty
        return max(time_windows) >= 3
    
    async def predict_next_jobs(self, current_time: datetime = None) -> List[PredictionResult]:
        """Predict which jobs are likely to run in the next 5 minutes"""
        if current_time is None:
            current_time = datetime.utcnow()
            
        # Get recent job history
        job_executions = await db.job_executions.find({
            "timestamp": {"$gte": current_time - timedelta(days=7)}
        }).to_list(1000)
        
        if not job_executions:
            return []
            
        executions = [JobExecution(**job) for job in job_executions]
        analysis = await self.analyze_job_history(executions)
        
        predictions = []
        
        for job_id, pattern in analysis["patterns"].items():
            prediction = self._generate_prediction(job_id, pattern, current_time)
            if prediction:
                predictions.append(prediction)
                
        return sorted(predictions, key=lambda x: x.confidence_score, reverse=True)
    
    def _generate_prediction(self, job_id: str, pattern: Dict[str, Any], current_time: datetime) -> Optional[PredictionResult]:
        """Generate prediction for a specific job"""
        if pattern["type"] == "cron" and "next_predicted" in pattern:
            next_run = pattern["next_predicted"]
            time_diff = (next_run - current_time).total_seconds()
            
            if 0 <= time_diff <= 300:  # Within next 5 minutes
                return PredictionResult(
                    job_id=job_id,
                    predicted_run_time_window=f"{int(time_diff/60)}:{int(time_diff%60):02d} minutes",
                    confidence_score=pattern["confidence"],
                    action="prewarm" if pattern["confidence"] > 0.7 else "skip",
                    reasoning=f"Cron pattern detected with {pattern['interval_seconds']:.0f}s intervals"
                )
        
        elif pattern["type"] == "bursty" and pattern["confidence"] > 0.6:
            return PredictionResult(
                job_id=job_id,
                predicted_run_time_window="1-3 minutes",
                confidence_score=pattern["confidence"],
                action="prewarm",
                reasoning="Burst pattern detected - high activity expected"
            )
            
        return None

# ===== API CONNECTOR GENERATOR =====

class APIConnectorGenerator:
    def __init__(self):
        self.mock_apis = self._create_mock_api_specs()
        
    def _create_mock_api_specs(self) -> Dict[str, Dict[str, Any]]:
        """Create mock API specifications for demo"""
        return {
            "user_management": {
                "name": "User Management API",
                "description": "Manage users, authentication, and profiles",
                "base_url": "https://api.internal.company.com/users",
                "endpoints": [
                    {
                        "method": "POST",
                        "path": "/users",
                        "name": "createUser",
                        "description": "Create a new user",
                        "request_body": {
                            "email": "string",
                            "name": "string",
                            "role": "string"
                        },
                        "response": {
                            "id": "string",
                            "email": "string",
                            "name": "string",
                            "created_at": "datetime"
                        }
                    },
                    {
                        "method": "GET",
                        "path": "/users",
                        "name": "listUsers",
                        "description": "List all users",
                        "query_params": {
                            "limit": "number",
                            "offset": "number"
                        },
                        "response": {
                            "users": "array",
                            "total": "number"
                        }
                    },
                    {
                        "method": "DELETE",
                        "path": "/users/{id}",
                        "name": "deleteUser",
                        "description": "Delete a user by ID",
                        "path_params": {
                            "id": "string"
                        },
                        "response": {
                            "success": "boolean"
                        }
                    }
                ]
            },
            "billing": {
                "name": "Billing API",
                "description": "Handle invoicing and billing operations",
                "base_url": "https://api.internal.company.com/billing",
                "endpoints": [
                    {
                        "method": "POST",
                        "path": "/invoices",
                        "name": "createInvoice",
                        "description": "Create a new invoice",
                        "request_body": {
                            "customer_id": "string",
                            "amount": "number",
                            "items": "array"
                        },
                        "response": {
                            "invoice_id": "string",
                            "amount": "number",
                            "status": "string"
                        }
                    },
                    {
                        "method": "GET",
                        "path": "/balance/{customer_id}",
                        "name": "getBalance",
                        "description": "Get customer balance",
                        "path_params": {
                            "customer_id": "string"
                        },
                        "response": {
                            "balance": "number",
                            "currency": "string"
                        }
                    }
                ]
            },
            "monitoring": {
                "name": "Monitoring API",
                "description": "System monitoring and health checks",
                "base_url": "https://api.internal.company.com/monitoring",
                "endpoints": [
                    {
                        "method": "GET",
                        "path": "/health",
                        "name": "getServiceHealth",
                        "description": "Get service health status",
                        "response": {
                            "status": "string",
                            "services": "array",
                            "timestamp": "datetime"
                        }
                    },
                    {
                        "method": "GET",
                        "path": "/errors",
                        "name": "listErrors",
                        "description": "List recent errors",
                        "query_params": {
                            "since": "datetime",
                            "severity": "string"
                        },
                        "response": {
                            "errors": "array",
                            "count": "number"
                        }
                    }
                ]
            },
            "crm": {
                "name": "CRM API",
                "description": "Customer relationship management",
                "base_url": "https://api.internal.company.com/crm",
                "endpoints": [
                    {
                        "method": "POST",
                        "path": "/leads",
                        "name": "createLead",
                        "description": "Create a new lead",
                        "request_body": {
                            "name": "string",
                            "email": "string",
                            "company": "string",
                            "source": "string"
                        },
                        "response": {
                            "lead_id": "string",
                            "status": "string",
                            "created_at": "datetime"
                        }
                    },
                    {
                        "method": "PUT",
                        "path": "/contacts/{id}",
                        "name": "updateContact",
                        "description": "Update contact information",
                        "path_params": {
                            "id": "string"
                        },
                        "request_body": {
                            "name": "string",
                            "email": "string",
                            "phone": "string"
                        },
                        "response": {
                            "contact": "object",
                            "updated_at": "datetime"
                        }
                    }
                ]
            }
        }
        
    def generate_connector(self, api_name: str) -> ConnectorResult:
        """Generate a complete connector package for the specified API"""
        if api_name not in self.mock_apis:
            raise HTTPException(status_code=404, message=f"API '{api_name}' not found")
            
        api_spec = self.mock_apis[api_name]
        
        connector_code = self._generate_typescript_connector(api_spec)
        config_template = self._generate_config_template(api_spec)
        documentation = self._generate_documentation(api_spec)
        directory_structure = self._generate_directory_structure(api_name, api_spec)
        
        return ConnectorResult(
            connector_code=connector_code,
            config_template=config_template,
            documentation=documentation,
            directory_structure=directory_structure
        )
        
    def _generate_typescript_connector(self, api_spec: Dict[str, Any]) -> str:
        """Generate TypeScript connector code"""
        class_name = api_spec["name"].replace(" ", "").replace("API", "Client")
        
        # Generate interfaces for each endpoint
        interfaces = []
        methods = []
        
        for endpoint in api_spec["endpoints"]:
            # Request interface
            if "request_body" in endpoint:
                interface_name = f"{endpoint['name'].title()}Request"
                interface_props = []
                for prop, prop_type in endpoint["request_body"].items():
                    ts_type = self._convert_to_ts_type(prop_type)
                    interface_props.append(f"  {prop}: {ts_type};")
                    
                interfaces.append(f"interface {interface_name} {{\n" + "\n".join(interface_props) + "\n}")
            
            # Response interface
            interface_name = f"{endpoint['name'].title()}Response"
            interface_props = []
            for prop, prop_type in endpoint["response"].items():
                ts_type = self._convert_to_ts_type(prop_type)
                interface_props.append(f"  {prop}: {ts_type};")
                
            interfaces.append(f"interface {interface_name} {{\n" + "\n".join(interface_props) + "\n}")
            
            # Generate method
            method = self._generate_method(endpoint)
            methods.append(method)
            
        connector_template = f"""import axios, {{ AxiosInstance, AxiosResponse }} from 'axios';

// Type definitions
{chr(10).join(interfaces)}

interface ClientConfig {{
  baseUrl: string;
  apiKey: string;
  timeout?: number;
}}

class {class_name} {{
  private client: AxiosInstance;
  
  constructor(config: ClientConfig) {{
    this.client = axios.create({{
      baseURL: config.baseUrl,
      timeout: config.timeout || 30000,
      headers: {{
        'Authorization': `Bearer ${{config.apiKey}}`,
        'Content-Type': 'application/json'
      }}
    }});
  }}

{chr(10).join(methods)}
}}

export default {class_name};
export * from './{api_spec["name"].lower().replace(" ", "_")}_types';
"""
        return connector_template
        
    def _generate_method(self, endpoint: Dict[str, Any]) -> str:
        """Generate a TypeScript method for an endpoint"""
        method_name = endpoint["name"]
        http_method = endpoint["method"].lower()
        path = endpoint["path"]
        
        # Parameters
        params = []
        if "path_params" in endpoint:
            for param in endpoint["path_params"].keys():
                params.append(f"{param}: string")
                
        if "request_body" in endpoint:
            params.append(f"data: {method_name.title()}Request")
            
        if "query_params" in endpoint:
            query_props = []
            for param, param_type in endpoint["query_params"].items():
                ts_type = self._convert_to_ts_type(param_type)
                query_props.append(f"{param}?: {ts_type}")
            if query_props:
                params.append(f"query?: {{ {'; '.join(query_props)} }}")
        
        param_str = ", ".join(params)
        
        # URL construction
        url_construction = f"const url = `{path}`;"
        if "path_params" in endpoint:
            for param in endpoint["path_params"].keys():
                url_construction = url_construction.replace(f"{{{param}}}", f"${{{param}}}")
        
        # Method body
        if http_method == "get":
            method_body = f"""
  async {method_name}({param_str}): Promise<{method_name.title()}Response> {{
    {url_construction}
    const response: AxiosResponse<{method_name.title()}Response> = await this.client.{http_method}(url, {{ params: query }});
    return response.data;
  }}"""
        else:
            method_body = f"""
  async {method_name}({param_str}): Promise<{method_name.title()}Response> {{
    {url_construction}
    const response: AxiosResponse<{method_name.title()}Response> = await this.client.{http_method}(url, data);
    return response.data;
  }}"""
        
        return method_body
        
    def _convert_to_ts_type(self, python_type: str) -> str:
        """Convert Python type hints to TypeScript types"""
        type_mapping = {
            "string": "string",
            "number": "number",
            "boolean": "boolean",
            "array": "any[]",
            "object": "any",
            "datetime": "string"  # ISO string format
        }
        return type_mapping.get(python_type, "any")
        
    def _generate_config_template(self, api_spec: Dict[str, Any]) -> str:
        """Generate configuration template"""
        return f"""# {api_spec["name"]} Configuration

# Environment Variables
{api_spec["name"].upper().replace(" ", "_")}_BASE_URL={api_spec["base_url"]}
{api_spec["name"].upper().replace(" ", "_")}_API_KEY=your_api_key_here
{api_spec["name"].upper().replace(" ", "_")}_TIMEOUT=30000

# Usage in your application
import {{ {api_spec["name"].replace(" ", "").replace("API", "Client")} }} from './{api_spec["name"].lower().replace(" ", "_")}_client';

const client = new {api_spec["name"].replace(" ", "").replace("API", "Client")}({{
  baseUrl: process.env.{api_spec["name"].upper().replace(" ", "_")}_BASE_URL!,
  apiKey: process.env.{api_spec["name"].upper().replace(" ", "_")}_API_KEY!,
  timeout: parseInt(process.env.{api_spec["name"].upper().replace(" ", "_")}_TIMEOUT || '30000')
}});
"""
        
    def _generate_documentation(self, api_spec: Dict[str, Any]) -> str:
        """Generate documentation markdown"""
        endpoint_docs = []
        for endpoint in api_spec["endpoints"]:
            doc = f"""
### {endpoint["name"]}

**{endpoint["method"]} {endpoint["path"]}**

{endpoint["description"]}

```typescript
await client.{endpoint["name"]}(/* parameters */);
```
"""
            endpoint_docs.append(doc)
            
        return f"""# {api_spec["name"]} Connector

{api_spec["description"]}

## Installation

```bash
npm install axios
```

## Usage

```typescript
import {{ {api_spec["name"].replace(" ", "").replace("API", "Client")} }} from './{api_spec["name"].lower().replace(" ", "_")}_client';

const client = new {api_spec["name"].replace(" ", "").replace("API", "Client")}({{
  baseUrl: 'your_base_url',
  apiKey: 'your_api_key'
}});
```

## API Endpoints

{chr(10).join(endpoint_docs)}

## Error Handling

All methods throw errors for HTTP error status codes. Wrap calls in try-catch blocks:

```typescript
try {{
  const result = await client.someMethod(data);
  console.log(result);
}} catch (error) {{
  console.error('API call failed:', error);
}}
```
"""
        
    def _generate_directory_structure(self, api_name: str, api_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Generate the complete directory structure"""
        safe_name = api_name.lower().replace(" ", "_")
        
        return {
            f"{safe_name}_connector": {
                "type": "directory",
                "files": {
                    f"{safe_name}_client.ts": {
                        "type": "file",
                        "description": "Main TypeScript client class"
                    },
                    f"{safe_name}_types.ts": {
                        "type": "file", 
                        "description": "TypeScript type definitions"
                    },
                    ".env.template": {
                        "type": "file",
                        "description": "Environment variable template"
                    },
                    "README.md": {
                        "type": "file",
                        "description": "API connector documentation"
                    },
                    "package.json": {
                        "type": "file",
                        "description": "NPM package configuration"
                    },
                    "examples": {
                        "type": "directory",
                        "files": {
                            "basic_usage.ts": {
                                "type": "file",
                                "description": "Basic usage examples"
                            },
                            "trigger_dev_integration.ts": {
                                "type": "file",
                                "description": "Trigger.dev workflow integration"
                            }
                        }
                    }
                }
            }
        }

# Initialize global instances
predictor = ColdStartPredictor()
connector_generator = APIConnectorGenerator()

# ===== MOCK DATA GENERATOR =====

async def generate_mock_job_data():
    """Generate realistic mock job execution data"""
    current_time = datetime.utcnow()
    jobs_data = []
    
    # Define job types with different patterns
    job_configs = [
        # Cron jobs (regular intervals)
        {"job_id": "backup_daily", "type": "cron", "interval_minutes": 1440, "success_rate": 0.95},
        {"job_id": "cleanup_logs", "type": "cron", "interval_minutes": 360, "success_rate": 0.98},
        {"job_id": "health_check", "type": "cron", "interval_minutes": 15, "success_rate": 0.99},
        
        # On-demand jobs (irregular but predictable)
        {"job_id": "user_report", "type": "on_demand", "avg_per_day": 5, "success_rate": 0.90},
        {"job_id": "data_export", "type": "on_demand", "avg_per_day": 3, "success_rate": 0.85},
        
        # Bursty jobs (AI/video processing)
        {"job_id": "ai_video_process", "type": "bursty", "burst_size": 8, "success_rate": 0.80},
        {"job_id": "ml_training", "type": "bursty", "burst_size": 12, "success_rate": 0.75},
        {"job_id": "image_analysis", "type": "bursty", "burst_size": 15, "success_rate": 0.82}
    ]
    
    # Generate data for the past 7 days
    for days_ago in range(7):
        day_start = current_time - timedelta(days=days_ago)
        
        for job_config in job_configs:
            if job_config["type"] == "cron":
                # Generate cron jobs at regular intervals
                interval = timedelta(minutes=job_config["interval_minutes"])
                job_time = day_start.replace(hour=0, minute=0, second=0, microsecond=0)
                
                while job_time < day_start + timedelta(days=1):
                    if random.random() < job_config["success_rate"]:
                        status = "success"
                        duration = random.randint(1000, 5000)
                        retries = 0
                    else:
                        status = random.choice(["failed", "timeout"])
                        duration = random.randint(500, 15000)
                        retries = random.randint(1, 3)
                    
                    jobs_data.append(JobExecution(
                        job_id=job_config["job_id"],
                        timestamp=job_time,
                        duration_ms=duration,
                        retries=retries,
                        status=status,
                        compute_time_sec=duration / 1000 * (1 + retries * 0.5),
                        job_type=job_config["type"]
                    ))
                    
                    job_time += interval
                    
            elif job_config["type"] == "on_demand":
                # Generate on-demand jobs at random times
                num_jobs = max(0, int(random.gauss(job_config["avg_per_day"], 2)))
                
                for _ in range(num_jobs):
                    job_time = day_start + timedelta(
                        hours=random.randint(8, 18),
                        minutes=random.randint(0, 59)
                    )
                    
                    if random.random() < job_config["success_rate"]:
                        status = "success"
                        duration = random.randint(2000, 8000)
                        retries = 0
                    else:
                        status = random.choice(["failed", "timeout"])
                        duration = random.randint(1000, 20000)
                        retries = random.randint(1, 2)
                    
                    jobs_data.append(JobExecution(
                        job_id=job_config["job_id"],
                        timestamp=job_time,
                        duration_ms=duration,
                        retries=retries,
                        status=status,
                        compute_time_sec=duration / 1000 * (1 + retries * 0.3),
                        job_type=job_config["type"]
                    ))
                    
            elif job_config["type"] == "bursty":
                # Generate bursty jobs (clusters of activity)
                if random.random() < 0.7:  # 70% chance of burst per day
                    burst_start = day_start + timedelta(
                        hours=random.randint(9, 16),
                        minutes=random.randint(0, 59)
                    )
                    
                    for i in range(job_config["burst_size"]):
                        job_time = burst_start + timedelta(
                            minutes=random.randint(0, 30),
                            seconds=random.randint(0, 59)
                        )
                        
                        if random.random() < job_config["success_rate"]:
                            status = "success"
                            duration = random.randint(5000, 25000)
                            retries = 0
                        else:
                            status = random.choice(["failed", "timeout"])
                            duration = random.randint(3000, 40000)
                            retries = random.randint(1, 4)
                        
                        jobs_data.append(JobExecution(
                            job_id=job_config["job_id"],
                            timestamp=job_time,
                            duration_ms=duration,
                            retries=retries,
                            status=status,
                            compute_time_sec=duration / 1000 * (1 + retries * 0.4),
                            job_type=job_config["type"]
                        ))
    
    return jobs_data

# ===== API ROUTES =====

# Original routes
@api_router.get("/")
async def root():
    return {"message": "DevOps Automation API - Cold Start Prediction & Connector Generator"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.dict()
    status_obj = StatusCheck(**status_dict)
    _ = await db.status_checks.insert_one(status_obj.dict())
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find().to_list(1000)
    return [StatusCheck(**status_check) for status_check in status_checks]

# Cold Start Prediction Routes
@api_router.post("/jobs/generate-mock-data")
async def generate_and_store_mock_data():
    """Generate and store mock job execution data"""
    try:
        # Clear existing data
        await db.job_executions.delete_many({})
        
        # Generate new mock data
        jobs_data = await generate_mock_job_data()
        
        # Store in database
        jobs_dict = [job.dict() for job in jobs_data]
        await db.job_executions.insert_many(jobs_dict)
        
        return {
            "message": f"Generated and stored {len(jobs_data)} job execution records",
            "total_records": len(jobs_data),
            "job_types": Counter([job.job_type for job in jobs_data]),
            "date_range": {
                "start": min([job.timestamp for job in jobs_data]).isoformat(),
                "end": max([job.timestamp for job in jobs_data]).isoformat()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate mock data: {str(e)}")

@api_router.get("/jobs/executions", response_model=List[JobExecution])
async def get_job_executions(limit: int = 100):
    """Get recent job executions"""
    jobs = await db.job_executions.find().sort("timestamp", -1).limit(limit).to_list(limit)
    return [JobExecution(**job) for job in jobs]

@api_router.get("/jobs/predictions", response_model=List[PredictionResult])
async def get_job_predictions():
    """Get predictions for jobs likely to run in the next 5 minutes"""
    try:
        predictions = await predictor.predict_next_jobs()
        return predictions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

@api_router.get("/jobs/analytics")
async def get_job_analytics():
    """Get comprehensive job analytics and patterns"""
    try:
        # Get all job executions from the past week
        current_time = datetime.utcnow()
        jobs = await db.job_executions.find({
            "timestamp": {"$gte": current_time - timedelta(days=7)}
        }).to_list(1000)
        
        if not jobs:
            return {"message": "No job data available. Generate mock data first."}
        
        job_executions = [JobExecution(**job) for job in jobs]
        analysis = await predictor.analyze_job_history(job_executions)
        predictions = await predictor.predict_next_jobs()
        
        return {
            "analytics": analysis,
            "predictions": [pred.dict() for pred in predictions],
            "summary": {
                "total_jobs_analyzed": len(job_executions),
                "unique_job_ids": len(set(job.job_id for job in job_executions)),
                "prediction_confidence_avg": sum(pred.confidence_score for pred in predictions) / len(predictions) if predictions else 0,
                "recommended_prewarms": len([pred for pred in predictions if pred.action == "prewarm"])
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analytics failed: {str(e)}")

# API Connector Generator Routes
@api_router.get("/connectors/available-apis")
async def get_available_apis():
    """Get list of available mock APIs for connector generation"""
    return {
        "available_apis": list(connector_generator.mock_apis.keys()),
        "api_specs": {
            name: {
                "name": spec["name"],
                "description": spec["description"],
                "endpoint_count": len(spec["endpoints"])
            }
            for name, spec in connector_generator.mock_apis.items()
        }
    }

@api_router.get("/connectors/{api_name}/spec")
async def get_api_spec(api_name: str):
    """Get detailed specification for a specific API"""
    if api_name not in connector_generator.mock_apis:
        raise HTTPException(status_code=404, detail=f"API '{api_name}' not found")
    
    return connector_generator.mock_apis[api_name]

@api_router.post("/connectors/{api_name}/generate", response_model=ConnectorResult)
async def generate_connector(api_name: str):
    """Generate a complete connector package for the specified API"""
    try:
        result = connector_generator.generate_connector(api_name)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Connector generation failed: {str(e)}")

@api_router.get("/connectors/{api_name}/download")
async def download_connector_package(api_name: str):
    """Download the complete connector package as a structured response"""
    try:
        result = connector_generator.generate_connector(api_name)
        
        # Create downloadable package structure
        package = {
            "package_name": f"{api_name}_connector",
            "files": {
                f"{api_name}_client.ts": result.connector_code,
                ".env.template": result.config_template,
                "README.md": result.documentation,
                "package.json": json.dumps({
                    "name": f"{api_name}-connector",
                    "version": "1.0.0",
                    "description": f"Auto-generated connector for {api_name} API",
                    "main": f"{api_name}_client.ts",
                    "dependencies": {
                        "axios": "^1.6.0"
                    },
                    "devDependencies": {
                        "typescript": "^5.0.0",
                        "@types/node": "^20.0.0"
                    }
                }, indent=2)
            },
            "directory_structure": result.directory_structure,
            "installation_commands": [
                "npm install axios",
                "npm install -D typescript @types/node"
            ]
        }
        
        return package
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Package generation failed: {str(e)}")

# Dashboard data endpoint
@api_router.get("/dashboard")
async def get_dashboard_data():
    """Get comprehensive dashboard data for both systems"""
    try:
        # Get job analytics and predictions
        current_time = datetime.utcnow()
        jobs = await db.job_executions.find({
            "timestamp": {"$gte": current_time - timedelta(days=1)}
        }).to_list(1000)
        
        predictions = []
        analytics = {"message": "No job data available"}
        
        if jobs:
            job_executions = [JobExecution(**job) for job in jobs]
            analytics = await predictor.analyze_job_history(job_executions)
            predictions = await predictor.predict_next_jobs()
        
        # Get available APIs
        available_apis = connector_generator.mock_apis
        
        return {
            "cold_start_system": {
                "analytics": analytics,
                "predictions": [pred.dict() for pred in predictions],
                "recent_jobs": len(jobs),
                "active_prewarms": len([pred for pred in predictions if pred.action == "prewarm"])
            },
            "connector_generator": {
                "available_apis": list(available_apis.keys()),
                "total_endpoints": sum(len(spec["endpoints"]) for spec in available_apis.values()),
                "api_categories": ["user_management", "billing", "monitoring", "crm"]
            },
            "system_status": {
                "timestamp": current_time.isoformat(),
                "services_online": True,
                "prediction_engine": "operational",
                "connector_generator": "operational"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dashboard data failed: {str(e)}")

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()