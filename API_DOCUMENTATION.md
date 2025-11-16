# 📡 HydroClaude API Documentation

**REST API and Python SDK Reference**

Version: 1.2.0
Last Updated: 2025-11-15

---

## 📋 Table of Contents

- [Overview](#overview)
- [REST API](#rest-api)
  - [Authentication](#authentication)
  - [Endpoints](#endpoints)
  - [Error Handling](#error-handling)
- [Python SDK](#python-sdk)
  - [Installation](#installation)
  - [Quick Start](#quick-start)
  - [API Reference](#api-reference)
- [Examples](#examples)
- [Best Practices](#best-practices)

---

## 🌐 Overview

HydroClaude provides two ways to interact with the simulation engine:

1. **REST API**: HTTP-based API for language-agnostic integration
2. **Python SDK**: Convenient Python client library

### Base URL

```
http://localhost:5000
```

### Supported Formats

- Request: `application/json`
- Response: `application/json`

---

## 🔧 REST API

### Authentication

**Current version**: No authentication required (development mode)

**Future versions**: API key or OAuth2 authentication

###endpoints

#### 1. Health Check

**GET** `/api/health`

Check API health and status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-11-15T10:00:00",
  "jobs": {
    "total": 10,
    "pending": 2,
    "running": 1,
    "completed": 6,
    "failed": 1
  }
}
```

**Example:**
```bash
curl http://localhost:5000/api/health
```

---

#### 2. Create Job

**POST** `/api/jobs`

Create a new simulation job.

**Request Body:**
```json
{
  "name": "my_simulation",
  "config": {
    "simulation": {
      "type": "steady",
      "mode": "single_canal"
    },
    "canal": {
      "length": 1000,
      "width": 10,
      "slope": 0.001,
      "manning_n": 0.025
    },
    "solver": {
      "method": "hydrostatic"
    },
    "boundary_conditions": {
      "upstream": {
        "type": "flow",
        "value": 8.0
      },
      "downstream": {
        "type": "depth",
        "method": "uniform_flow"
      }
    }
  }
}
```

**Response (201):**
```json
{
  "success": true,
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "job": {
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "my_simulation",
    "status": "pending",
    "created_at": "2025-11-15T10:00:00"
  }
}
```

**Example:**
```bash
curl -X POST http://localhost:5000/api/jobs \
  -H "Content-Type: application/json" \
  -d @config.json
```

---

#### 3. List Jobs

**GET** `/api/jobs`

List all simulation jobs.

**Query Parameters:**
- `status` (optional): Filter by status (`pending`, `running`, `completed`, `failed`)

**Response:**
```json
{
  "success": true,
  "total": 10,
  "jobs": [
    {
      "job_id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "my_simulation",
      "status": "completed",
      "created_at": "2025-11-15T10:00:00",
      "completed_at": "2025-11-15T10:05:00"
    }
  ]
}
```

**Example:**
```bash
# List all jobs
curl http://localhost:5000/api/jobs

# List completed jobs
curl "http://localhost:5000/api/jobs?status=completed"
```

---

#### 4. Get Job Details

**GET** `/api/jobs/{job_id}`

Get detailed information about a job.

**Response:**
```json
{
  "success": true,
  "job": {
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "my_simulation",
    "status": "completed",
    "created_at": "2025-11-15T10:00:00",
    "started_at": "2025-11-15T10:00:05",
    "completed_at": "2025-11-15T10:05:00",
    "error": null
  }
}
```

**Example:**
```bash
curl http://localhost:5000/api/jobs/550e8400-e29b-41d4-a716-446655440000
```

---

#### 5. Run Job

**POST** `/api/jobs/{job_id}/run`

Execute a simulation job.

**Response (200):**
```json
{
  "success": true,
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "message": "Simulation completed successfully"
}
```

**Response (500 - if failed):**
```json
{
  "success": false,
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "failed",
  "error": "Error message here"
}
```

**Example:**
```bash
curl -X POST http://localhost:5000/api/jobs/550e8400-e29b-41d4-a716-446655440000/run
```

---

#### 6. Get Results

**GET** `/api/jobs/{job_id}/results`

Get simulation results (only available for completed jobs).

**Response:**
```json
{
  "success": true,
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "results": {
    "simulation": {...},
    "canal": {...},
    "solver": {...},
    "universal_data_model": {
      "dimensions": {...},
      "data": {...}
    },
    "validation": {...}
  }
}
```

**Example:**
```bash
curl http://localhost:5000/api/jobs/550e8400-e29b-41d4-a716-446655440000/results
```

---

#### 7. Delete Job

**DELETE** `/api/jobs/{job_id}`

Delete a job and its data.

**Response:**
```json
{
  "success": true,
  "message": "Job 550e8400-e29b-41d4-a716-446655440000 deleted"
}
```

**Example:**
```bash
curl -X DELETE http://localhost:5000/api/jobs/550e8400-e29b-41d4-a716-446655440000
```

---

#### 8. Download File

**GET** `/api/jobs/{job_id}/files/{filename}`

Download a file from job output directory.

**Example:**
```bash
curl http://localhost:5000/api/jobs/550e8400-e29b-41d4-a716-446655440000/files/results.json \
  --output results.json
```

---

### Error Handling

All errors return appropriate HTTP status codes:

- `400` - Bad Request (invalid parameters)
- `404` - Not Found (resource doesn't exist)
- `500` - Internal Server Error (simulation failed)

**Error Response Format:**
```json
{
  "error": "Error message description"
}
```

---

## 🐍 Python SDK

### Installation

```bash
pip install requests  # Required dependency
```

The SDK is included in the HydroClaude package:
```python
from sdk.hydroclaude_sdk import HydroClaudeClient
```

### Quick Start

```python
from sdk.hydroclaude_sdk import HydroClaudeClient

# Create client
client = HydroClaudeClient('http://localhost:5000')

# Check health
health = client.health()
print(f"API Status: {health['status']}")

# Create configuration
config = {
    'simulation': {'type': 'steady', 'mode': 'single_canal'},
    'canal': {'length': 1000, 'width': 10, 'slope': 0.001, 'manning_n': 0.025},
    'solver': {'method': 'hydrostatic'},
    'boundary_conditions': {
        'upstream': {'type': 'flow', 'value': 8.0},
        'downstream': {'type': 'depth', 'method': 'uniform_flow'}
    }
}

# Submit and wait for results (one-liner)
results = client.submit_and_wait(config, name='test_simulation')
print("Simulation completed!")
print(f"Mass error: {results['validation']['mass_error_percent']:.6f}%")
```

### API Reference

#### HydroClaudeClient

**Constructor:**
```python
client = HydroClaudeClient(base_url='http://localhost:5000', timeout=300)
```

**Parameters:**
- `base_url` (str): API base URL
- `timeout` (int): Request timeout in seconds

---

**Methods:**

##### `health()` → Dict

Check API health.

```python
health = client.health()
# Returns: {'status': 'healthy', 'timestamp': '...', 'jobs': {...}}
```

---

##### `create_job(config, name=None)` → str

Create a new job.

```python
job_id = client.create_job(config, name='my_simulation')
# Returns: job_id (str)
```

---

##### `get_job(job_id)` → Dict

Get job information.

```python
job_info = client.get_job(job_id)
# Returns: job info dictionary
```

---

##### `list_jobs(status=None)` → List[Dict]

List all jobs.

```python
# All jobs
jobs = client.list_jobs()

# Completed jobs only
completed = client.list_jobs(status='completed')
```

---

##### `run_job(job_id, wait=False, poll_interval=1.0)` → Dict

Run a job.

```python
# Async execution
result = client.run_job(job_id)

# Wait for completion
result = client.run_job(job_id, wait=True, poll_interval=2.0)
```

---

##### `wait_for_completion(job_id, poll_interval=1.0, max_wait=None)` → Dict

Wait for job completion.

```python
job_info = client.wait_for_completion(job_id, poll_interval=1.0, max_wait=600)
```

---

##### `get_results(job_id)` → Dict

Get simulation results.

```python
results = client.get_results(job_id)
```

---

##### `delete_job(job_id)` → bool

Delete a job.

```python
success = client.delete_job(job_id)
```

---

##### `download_file(job_id, filename, output_path)` → bool

Download a file.

```python
success = client.download_file(job_id, 'results.json', 'local_results.json')
```

---

##### `submit_and_wait(config, name=None, poll_interval=1.0)` → Dict

Submit job and wait for results (convenience method).

```python
results = client.submit_and_wait(config, name='quick_sim')
```

---

##### `cleanup_completed_jobs(keep_recent=10)` → int

Clean up old completed jobs.

```python
deleted_count = client.cleanup_completed_jobs(keep_recent=5)
print(f"Deleted {deleted_count} old jobs")
```

---

#### Job Wrapper

Convenient wrapper for job operations:

```python
from sdk.hydroclaude_sdk import Job

# Create job wrapper
job = Job(client, job_id)

# Properties
print(job.status)      # Get current status
print(job.info)        # Get job info (cached)
print(job.results)     # Get results (if completed)

# Methods
job.run(wait=True)     # Run and wait
job.wait()             # Wait for completion
job.delete()           # Delete job
job.download('file.json', 'local.json')  # Download file
```

---

## 💡 Examples

### Example 1: Basic Simulation

```python
from sdk.hydroclaude_sdk import HydroClaudeClient

client = HydroClaudeClient('http://localhost:5000')

config = {
    'simulation': {'type': 'steady', 'mode': 'single_canal'},
    'canal': {'length': 1000, 'width': 10, 'slope': 0.001, 'manning_n': 0.025},
    'solver': {'method': 'hydrostatic'},
    'boundary_conditions': {
        'upstream': {'type': 'flow', 'value': 8.0},
        'downstream': {'type': 'depth', 'method': 'uniform_flow'}
    }
}

# Submit and get results
results = client.submit_and_wait(config)
print(f"✅ Simulation complete!")
print(f"   Mass error: {results['validation']['mass_error_percent']:.6f}%")
```

### Example 2: Batch Simulations

```python
from sdk.hydroclaude_sdk import HydroClaudeClient

client = HydroClaudeClient()

# Create multiple jobs
job_ids = []
for i, manning_n in enumerate([0.020, 0.025, 0.030]):
    config = {...}  # Base config
    config['canal']['manning_n'] = manning_n
    
    job_id = client.create_job(config, name=f'manning_{manning_n}')
    job_ids.append(job_id)

# Run all jobs
for job_id in job_ids:
    client.run_job(job_id)

# Wait for all to complete
for job_id in job_ids:
    client.wait_for_completion(job_id)
    results = client.get_results(job_id)
    print(f"Job {job_id}: Done")
```

### Example 3: Using Job Wrapper

```python
from sdk.hydroclaude_sdk import HydroClaudeClient, Job

client = HydroClaudeClient()

# Create and wrap job
job_id = client.create_job(config, name='wrapper_example')
job = Job(client, job_id)

# Use job wrapper
job.run(wait=True)

if job.status == 'completed':
    print(f"✅ {job.results['validation']}")
    job.download('plots/water_surface_profile.png', 'profile.png')
```

### Example 4: Error Handling

```python
from sdk.hydroclaude_sdk import HydroClaudeClient, APIError

client = HydroClaudeClient()

try:
    job_id = client.create_job(config)
    result = client.run_job(job_id, wait=True, poll_interval=1.0)
    
    if result['success']:
        results = client.get_results(job_id)
        print("Success!")
    else:
        print(f"Failed: {result['error']}")
        
except APIError as e:
    print(f"API Error: {e}")
except TimeoutError as e:
    print(f"Timeout: {e}")
```

---

## 🎯 Best Practices

### 1. Use Connection Pooling

```python
# Reuse client instance
client = HydroClaudeClient()

# Run multiple simulations
for config in configs:
    results = client.submit_and_wait(config)
```

### 2. Handle Timeouts

```python
# Set appropriate timeout
client = HydroClaudeClient(timeout=600)  # 10 minutes

# Or use max_wait
job_info = client.wait_for_completion(job_id, max_wait=300)
```

### 3. Clean Up Resources

```python
# Delete job after getting results
results = client.get_results(job_id)
client.delete_job(job_id)

# Or clean up old jobs periodically
client.cleanup_completed_jobs(keep_recent=10)
```

### 4. Check Status Before Getting Results

```python
job_info = client.get_job(job_id)

if job_info['status'] == 'completed':
    results = client.get_results(job_id)
elif job_info['status'] == 'failed':
    print(f"Job failed: {job_info['error']}")
```

### 5. Use Polling Wisely

```python
# Adjust poll interval based on simulation duration
# Fast simulations: poll_interval=0.5
# Slow simulations: poll_interval=5.0

result = client.run_job(job_id, wait=True, poll_interval=2.0)
```

---

## 🚀 Performance Tips

1. **Batch Processing**: Submit multiple jobs before waiting
2. **Parallel Execution**: API server can handle multiple concurrent jobs
3. **Cleanup**: Regularly delete old jobs to save disk space
4. **Caching**: Reuse client instance for multiple requests
5. **Timeouts**: Set appropriate timeouts for long simulations

---

## 📞 Support

- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions
- **Email**: support@hydroclaude.org (coming soon)

---

<p align="center">
  <b>HydroClaude API v1.2.0</b>
</p>

<p align="center">
  Made with ❤️ by HydroClaude Development Team
</p>
