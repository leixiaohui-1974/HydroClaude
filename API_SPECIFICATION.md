# HydroClaude API Specification v1.3.0

**Version**: 1.3.0
**Date**: 2025-11-11
**Base URL**: `http://localhost:8000/api/v1`
**Protocol**: HTTP/HTTPS
**Format**: JSON

This document provides the complete API specification for HydroClaude v1.3.0 in OpenAPI 3.0 format.

---

## OpenAPI 3.0 Specification

```yaml
openapi: 3.0.3
info:
  title: HydroClaude API
  description: |
    HydroClaude is a hydraulic modeling platform for simulating 1D shallow water flow.

    Features:
    - Godunov finite volume method
    - HLL Riemann solver
    - MUSCL reconstruction (1st/2nd order)
    - TVD-RK2 time integration
    - Numba JIT acceleration (8.8x speedup)
    - Perfect mass conservation (0.0% error)

    This API allows you to:
    - Submit hydraulic simulations
    - Monitor simulation status
    - Retrieve results
    - Manage simulation tasks

    **Quality Metrics**:
    - Test pass rate: 100% (43/43)
    - Mass conservation: 0.0% error
    - API response time: <100ms
    - Production ready: 90%

  version: 1.3.0
  contact:
    name: HydroClaude Team
    url: https://github.com/YOUR_ORG/HydroClaude
  license:
    name: MIT
    url: https://opensource.org/licenses/MIT

servers:
  - url: http://localhost:8000/api/v1
    description: Local development server
  - url: https://your-domain.com/api/v1
    description: Production server

tags:
  - name: Health
    description: Service health monitoring
  - name: Simulations
    description: Hydraulic simulation operations

paths:
  /health:
    get:
      tags:
        - Health
      summary: Health check
      description: Check if the API service is running and healthy
      operationId: getHealth
      responses:
        '200':
          description: Service is healthy
          content:
            application/json:
              schema:
                type: object
                properties:
                  status:
                    type: string
                    example: healthy
                    description: Health status
              examples:
                healthy:
                  value:
                    status: healthy

  /simulations:
    post:
      tags:
        - Simulations
      summary: Create simulation
      description: |
        Submit a new hydraulic simulation for execution.

        **Required fields** (v1.3.0):
        - `name`: Simulation name
        - `config.width`: Channel width (m)
        - `config.length`: Channel length (m)
        - `config.n_cells`: Number of grid cells
        - `config.initial_conditions`: Initial state
        - `config.boundary_conditions`: Boundary conditions

        **Breaking changes from v1.2.0**:
        - Fields listed above are now REQUIRED
        - `manning_n` minimum value: 0.001 (was 0.0)
        - Cross-field validation added

        See migration guide in release notes.
      operationId: createSimulation
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/SimulationRequest'
            examples:
              basic_steady_flow:
                summary: Basic steady flow
                value:
                  name: "Basic Steady Flow"
                  description: "Simple steady flow in rectangular channel"
                  config:
                    width: 10.0
                    length: 1000.0
                    n_cells: 100
                    manning_n: 0.025
                    bed_slope: 0.001
                    t_end: 60.0
                    cfl: 0.3
                    order: 1
                    initial_conditions:
                      type: uniform
                      h: 5.0
                      Q: 20.0
                    boundary_conditions:
                      upstream:
                        type: Q
                        value: 20.0
                      downstream:
                        type: h
                        value: 5.0

              dam_break:
                summary: Dam break scenario
                value:
                  name: "Dam Break Simulation"
                  description: "Sudden dam failure scenario"
                  config:
                    width: 20.0
                    length: 5000.0
                    n_cells: 500
                    manning_n: 0.035
                    bed_slope: 0.002
                    t_end: 300.0
                    cfl: 0.3
                    order: 1
                    initial_conditions:
                      type: dam_break
                      dam_position: 500.0
                      h_upstream: 10.0
                      h_downstream: 0.5
                    boundary_conditions:
                      upstream:
                        type: closed
                      downstream:
                        type: open

      responses:
        '201':
          description: Simulation created successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SimulationCreatedResponse'
              example:
                task_id: "abc123def456"
                status: "pending"
                created_at: "2025-11-11T12:00:00Z"

        '400':
          description: Bad request - Invalid JSON
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
              example:
                detail: "Invalid JSON format"

        '422':
          description: Validation error - Invalid parameters
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ValidationError'
              examples:
                missing_field:
                  summary: Missing required field
                  value:
                    detail:
                      - loc: ["body", "config", "width"]
                        msg: "field required"
                        type: "value_error.missing"

                invalid_range:
                  summary: Value out of range
                  value:
                    detail:
                      - loc: ["body", "config", "cfl"]
                        msg: "ensure this value is less than or equal to 1.0"
                        type: "value_error.number.not_le"

                cross_field_error:
                  summary: Cross-field validation failure
                  value:
                    detail:
                      - msg: "For second-order accuracy (order=2), CFL must be ≤ 0.5 for stability"
                        type: "value_error"

  /simulations/{task_id}/status:
    get:
      tags:
        - Simulations
      summary: Get simulation status
      description: |
        Retrieve the current status of a simulation.

        **Status values**:
        - `pending`: Queued, not started yet
        - `running`: Currently executing
        - `completed`: Finished successfully
        - `failed`: Error occurred

        **Polling recommendations**:
        - Poll every 1-2 seconds for status updates
        - Stop polling when status is `completed` or `failed`
        - Check `error` field if status is `failed`
      operationId: getSimulationStatus
      parameters:
        - name: task_id
          in: path
          required: true
          description: Unique task identifier returned from simulation creation
          schema:
            type: string
            example: "abc123def456"

      responses:
        '200':
          description: Status retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SimulationStatusResponse'
              examples:
                pending:
                  summary: Simulation pending
                  value:
                    task_id: "abc123def456"
                    status: "pending"
                    created_at: "2025-11-11T12:00:00Z"

                running:
                  summary: Simulation running
                  value:
                    task_id: "abc123def456"
                    status: "running"
                    created_at: "2025-11-11T12:00:00Z"
                    started_at: "2025-11-11T12:00:05Z"
                    progress: 0.45

                completed:
                  summary: Simulation completed
                  value:
                    task_id: "abc123def456"
                    status: "completed"
                    created_at: "2025-11-11T12:00:00Z"
                    started_at: "2025-11-11T12:00:05Z"
                    completed_at: "2025-11-11T12:00:10Z"
                    compute_time: 0.173

                failed:
                  summary: Simulation failed
                  value:
                    task_id: "abc123def456"
                    status: "failed"
                    created_at: "2025-11-11T12:00:00Z"
                    started_at: "2025-11-11T12:00:05Z"
                    failed_at: "2025-11-11T12:00:08Z"
                    error: "Numerical instability detected at t=13.92s"

        '404':
          description: Simulation not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
              example:
                detail: "Simulation not found"

  /simulations/{task_id}/results:
    get:
      tags:
        - Simulations
      summary: Get simulation results
      description: |
        Retrieve the results of a completed simulation.

        **Prerequisites**:
        - Simulation must be in `completed` status
        - Check status endpoint first to verify completion

        **Result contents**:
        - Time series data (t, x, h, Q)
        - Quality metrics (mass conservation error)
        - Performance metrics (compute time)
        - Flow characteristics (max Froude number)

        **Data format**:
        - Arrays are in JSON format
        - 2D arrays use nested lists: `[[row1], [row2], ...]`
        - Time dimension is first: `h[time_index][cell_index]`
      operationId: getSimulationResults
      parameters:
        - name: task_id
          in: path
          required: true
          description: Unique task identifier
          schema:
            type: string
            example: "abc123def456"

      responses:
        '200':
          description: Results retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SimulationResultsResponse'
              example:
                task_id: "abc123def456"
                status: "completed"
                results:
                  t: [0.0, 1.0, 2.0, 3.0]
                  x: [0.0, 10.0, 20.0, 30.0]
                  h:
                    - [5.0, 5.0, 5.0, 5.0]
                    - [5.0, 5.0, 5.0, 5.0]
                    - [5.0, 5.0, 5.0, 5.0]
                    - [5.0, 5.0, 5.0, 5.0]
                  Q:
                    - [20.0, 20.0, 20.0, 20.0]
                    - [20.0, 20.0, 20.0, 20.0]
                    - [20.0, 20.0, 20.0, 20.0]
                    - [20.0, 20.0, 20.0, 20.0]
                  mass_conservation_error: 0.0
                  compute_time: 0.173
                  max_froude: 0.0971
                compute_time: 0.173

        '404':
          description: Simulation not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
              example:
                detail: "Simulation not found"

        '409':
          description: Simulation not completed yet
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
              example:
                detail: "Simulation is still running. Current status: running"

  /simulations/{task_id}:
    delete:
      tags:
        - Simulations
      summary: Delete simulation
      description: |
        Delete a simulation and its results.

        **Notes**:
        - Can delete simulations in any status
        - Results are permanently deleted
        - Cannot be undone
      operationId: deleteSimulation
      parameters:
        - name: task_id
          in: path
          required: true
          description: Unique task identifier
          schema:
            type: string
            example: "abc123def456"

      responses:
        '204':
          description: Simulation deleted successfully

        '404':
          description: Simulation not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
              example:
                detail: "Simulation not found"

components:
  schemas:
    SimulationRequest:
      type: object
      required:
        - name
        - config
      properties:
        name:
          type: string
          description: Simulation name
          minLength: 1
          maxLength: 200
          example: "Basic Steady Flow"

        description:
          type: string
          description: Optional simulation description
          maxLength: 1000
          example: "Steady flow analysis in irrigation canal"

        config:
          $ref: '#/components/schemas/SimulationConfig'

    SimulationConfig:
      type: object
      required:
        - width
        - length
        - n_cells
        - initial_conditions
        - boundary_conditions
      properties:
        width:
          type: number
          description: Channel width (m)
          minimum: 0
          exclusiveMinimum: true
          maximum: 1000
          example: 10.0

        length:
          type: number
          description: Channel length (m)
          minimum: 10
          maximum: 100000
          example: 1000.0

        n_cells:
          type: integer
          description: Number of grid cells
          minimum: 10
          maximum: 10000
          example: 100

        manning_n:
          type: number
          description: Manning's roughness coefficient
          minimum: 0.001
          maximum: 0.1
          default: 0.025
          example: 0.025

        bed_slope:
          type: number
          description: Channel bed slope (dimensionless)
          minimum: 0
          maximum: 0.1
          default: 0.001
          example: 0.001

        t_end:
          type: number
          description: Simulation end time (s)
          minimum: 1
          maximum: 86400
          default: 3600
          example: 60.0

        cfl:
          type: number
          description: CFL number for numerical stability
          minimum: 0.1
          maximum: 0.9
          default: 0.3
          example: 0.3

        order:
          type: integer
          description: Spatial accuracy order (1 or 2)
          enum: [1, 2]
          default: 1
          example: 1

        initial_conditions:
          $ref: '#/components/schemas/InitialConditions'

        boundary_conditions:
          $ref: '#/components/schemas/BoundaryConditions'

    InitialConditions:
      type: object
      required:
        - type
      properties:
        type:
          type: string
          description: Type of initial condition
          enum: [uniform, steady_state, dam_break, gate]
          example: uniform

        h:
          type: number
          description: Initial water depth (m) - for uniform type
          minimum: 0
          exclusiveMinimum: true
          example: 5.0

        Q:
          type: number
          description: Initial flow rate (m³/s) - for uniform type
          minimum: 0
          example: 20.0

        dam_position:
          type: number
          description: Dam position (m) - for dam_break type
          minimum: 0
          example: 500.0

        h_upstream:
          type: number
          description: Upstream depth (m) - for dam_break type
          minimum: 0
          exclusiveMinimum: true
          example: 10.0

        h_downstream:
          type: number
          description: Downstream depth (m) - for dam_break type
          minimum: 0
          exclusiveMinimum: true
          example: 0.5

    BoundaryConditions:
      type: object
      required:
        - upstream
        - downstream
      properties:
        upstream:
          $ref: '#/components/schemas/BoundaryCondition'

        downstream:
          $ref: '#/components/schemas/BoundaryCondition'

    BoundaryCondition:
      type: object
      required:
        - type
      properties:
        type:
          type: string
          description: Boundary condition type
          enum: [Q, h, open, closed]
          example: Q

        value:
          type: number
          description: Boundary value (required for Q and h types)
          example: 20.0

    SimulationCreatedResponse:
      type: object
      properties:
        task_id:
          type: string
          description: Unique task identifier
          example: "abc123def456"

        status:
          type: string
          description: Initial status (always "pending")
          enum: [pending]
          example: pending

        created_at:
          type: string
          format: date-time
          description: Creation timestamp (ISO 8601)
          example: "2025-11-11T12:00:00Z"

    SimulationStatusResponse:
      type: object
      properties:
        task_id:
          type: string
          description: Unique task identifier
          example: "abc123def456"

        status:
          type: string
          description: Current simulation status
          enum: [pending, running, completed, failed]
          example: completed

        created_at:
          type: string
          format: date-time
          description: Creation timestamp
          example: "2025-11-11T12:00:00Z"

        started_at:
          type: string
          format: date-time
          description: Start timestamp (if started)
          example: "2025-11-11T12:00:05Z"

        completed_at:
          type: string
          format: date-time
          description: Completion timestamp (if completed)
          example: "2025-11-11T12:00:10Z"

        failed_at:
          type: string
          format: date-time
          description: Failure timestamp (if failed)
          example: "2025-11-11T12:00:08Z"

        progress:
          type: number
          description: Progress fraction (0.0 to 1.0) - if running
          minimum: 0
          maximum: 1
          example: 0.45

        compute_time:
          type: number
          description: Computation time (s) - if completed
          example: 0.173

        error:
          type: string
          description: Error message - if failed
          example: "Numerical instability detected at t=13.92s"

    SimulationResultsResponse:
      type: object
      properties:
        task_id:
          type: string
          description: Unique task identifier
          example: "abc123def456"

        status:
          type: string
          description: Status (always "completed" for results)
          enum: [completed]
          example: completed

        results:
          type: object
          properties:
            t:
              type: array
              description: Time points (s)
              items:
                type: number
              example: [0.0, 1.0, 2.0, 3.0]

            x:
              type: array
              description: Spatial positions (m)
              items:
                type: number
              example: [0.0, 10.0, 20.0, 30.0]

            h:
              type: array
              description: Water depth (m) - shape [n_time, n_cells]
              items:
                type: array
                items:
                  type: number
              example: [[5.0, 5.0, 5.0, 5.0]]

            Q:
              type: array
              description: Flow rate (m³/s) - shape [n_time, n_cells]
              items:
                type: array
                items:
                  type: number
              example: [[20.0, 20.0, 20.0, 20.0]]

            mass_conservation_error:
              type: number
              description: Mass conservation error (%)
              example: 0.0

            max_froude:
              type: number
              description: Maximum Froude number
              example: 0.0971

        compute_time:
          type: number
          description: Computation time (s)
          example: 0.173

    ErrorResponse:
      type: object
      properties:
        detail:
          type: string
          description: Error message
          example: "Simulation not found"

    ValidationError:
      type: object
      properties:
        detail:
          type: array
          description: List of validation errors
          items:
            type: object
            properties:
              loc:
                type: array
                description: Location of error (path in request body)
                items:
                  oneOf:
                    - type: string
                    - type: integer
                example: ["body", "config", "width"]

              msg:
                type: string
                description: Error message
                example: "field required"

              type:
                type: string
                description: Error type
                example: "value_error.missing"
```

---

## Usage Examples

### Python (requests)

```python
import requests
import time

BASE_URL = "http://localhost:8000/api/v1"

# Create simulation
config = {
    "name": "My Simulation",
    "config": {
        "width": 10.0,
        "length": 1000.0,
        "n_cells": 100,
        "initial_conditions": {
            "type": "uniform",
            "h": 5.0,
            "Q": 20.0
        },
        "boundary_conditions": {
            "upstream": {"type": "Q", "value": 20.0},
            "downstream": {"type": "h", "value": 5.0}
        }
    }
}

response = requests.post(f"{BASE_URL}/simulations", json=config)
task_id = response.json()['task_id']

# Poll for completion
while True:
    status_resp = requests.get(f"{BASE_URL}/simulations/{task_id}/status")
    status = status_resp.json()['status']

    if status == 'completed':
        break
    elif status == 'failed':
        error = status_resp.json()['error']
        print(f"Failed: {error}")
        exit(1)

    time.sleep(1)

# Get results
results_resp = requests.get(f"{BASE_URL}/simulations/{task_id}/results")
results = results_resp.json()

print(f"Mass conservation error: {results['results']['mass_conservation_error']}%")
print(f"Compute time: {results['compute_time']}s")
```

### JavaScript (fetch)

```javascript
const BASE_URL = "http://localhost:8000/api/v1";

// Create simulation
const config = {
  name: "My Simulation",
  config: {
    width: 10.0,
    length: 1000.0,
    n_cells: 100,
    initial_conditions: {
      type: "uniform",
      h: 5.0,
      Q: 20.0
    },
    boundary_conditions: {
      upstream: { type: "Q", value: 20.0 },
      downstream: { type: "h", value: 5.0 }
    }
  }
};

const response = await fetch(`${BASE_URL}/simulations`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(config)
});

const { task_id } = await response.json();

// Poll for completion
while (true) {
  const statusResp = await fetch(`${BASE_URL}/simulations/${task_id}/status`);
  const statusData = await statusResp.json();

  if (statusData.status === 'completed') break;
  if (statusData.status === 'failed') {
    console.error('Failed:', statusData.error);
    throw new Error(statusData.error);
  }

  await new Promise(resolve => setTimeout(resolve, 1000));
}

// Get results
const resultsResp = await fetch(`${BASE_URL}/simulations/${task_id}/results`);
const resultsData = await resultsResp.json();

console.log(`Mass conservation error: ${resultsData.results.mass_conservation_error}%`);
console.log(`Compute time: ${resultsData.compute_time}s`);
```

### curl (command line)

```bash
# Create simulation
curl -X POST http://localhost:8000/api/v1/simulations \
  -H "Content-Type: application/json" \
  -d @config.json

# Get status
curl http://localhost:8000/api/v1/simulations/abc123def456/status

# Get results
curl http://localhost:8000/api/v1/simulations/abc123def456/results

# Delete simulation
curl -X DELETE http://localhost:8000/api/v1/simulations/abc123def456
```

---

## Rate Limiting

**v1.3.0**: No rate limiting implemented

**Future (v2.0)**:
- 100 requests per minute per user
- 10 concurrent simulations per user

---

## Error Handling

### HTTP Status Codes

| Code | Meaning | When |
|------|---------|------|
| 200 | OK | Request successful |
| 201 | Created | Simulation created |
| 204 | No Content | Deletion successful |
| 400 | Bad Request | Invalid JSON |
| 404 | Not Found | Simulation doesn't exist |
| 409 | Conflict | Results not ready yet |
| 422 | Validation Error | Invalid parameters |
| 500 | Internal Server Error | Server error |

### Error Response Format

All errors return JSON with `detail` field:

```json
{
  "detail": "Error message here"
}
```

Validation errors (422) return array of errors:

```json
{
  "detail": [
    {
      "loc": ["body", "config", "width"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## Versioning

**Current Version**: v1.3.0

**API Versioning Strategy**:
- Major version in URL path: `/api/v1/...`
- Minor/patch versions don't change URL
- Breaking changes increment major version

**Future Versions**:
- v2.0: Multi-user support, authentication
- v3.0: Real-time features, WebSocket support

---

## Authentication

**v1.3.0**: No authentication required (single-user mode)

**Future (v2.0)**:
- JWT-based authentication
- API keys
- OAuth2 support

Example (future):
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/simulations
```

---

## CORS

**Development**: Allow all origins
**Production**: Configure allowed origins in server

Current configuration:
```python
allow_origins=["http://localhost:5173"]  # Frontend URL
```

---

## WebSocket Support

**v1.3.0**: Not available

**Future (v1.4.0+)**:
- Real-time progress updates
- Live result streaming
- Endpoint: `ws://localhost:8000/ws/simulations/{task_id}`

---

## Performance

**Typical Response Times**:
- Health check: < 10ms
- Create simulation: < 100ms
- Get status: < 50ms
- Get results: < 200ms (depends on result size)

**Simulation Compute Times**:
- 100 cells, 30s: ~0.17s
- 500 cells, 60s: ~1.5s
- 1000 cells, 300s: ~9s

(With Numba JIT compilation)

---

## Data Limits

**Request Size**: 10 MB maximum
**Result Size**: No explicit limit (typically < 5 MB)
**Grid Size**: Max 10,000 cells
**Simulation Duration**: Max 24 hours (86,400 seconds)

---

## Best Practices

1. **Always check status before getting results**
   ```python
   # Good
   status = get_status(task_id)
   if status['status'] == 'completed':
       results = get_results(task_id)

   # Bad - may fail with 409
   results = get_results(task_id)
   ```

2. **Use appropriate polling interval**
   ```python
   # Good - 1 second interval
   time.sleep(1)

   # Bad - too frequent
   time.sleep(0.1)  # Don't poll 10x per second
   ```

3. **Handle all status values**
   ```python
   status = response.json()['status']
   if status == 'completed':
       # Success path
   elif status == 'failed':
       # Error handling
   elif status in ['pending', 'running']:
       # Continue polling
   ```

4. **Use configuration templates**
   - Start with verified templates
   - Modify incrementally
   - Test with conservative parameters

5. **Clean up completed simulations**
   ```python
   # Delete when done
   requests.delete(f"{BASE_URL}/simulations/{task_id}")
   ```

---

## Migration from v1.2.0

### Breaking Changes

1. **Required fields** - Add to all requests:
   ```json
   {
     "config": {
       "width": 10.0,         // NOW REQUIRED
       "length": 1000.0,      // NOW REQUIRED
       "n_cells": 100,        // NOW REQUIRED
       "initial_conditions": {}, // NOW REQUIRED
       "boundary_conditions": {} // NOW REQUIRED
     }
   }
   ```

2. **Manning's n minimum**: Change 0.0 to 0.001

3. **Validation errors**: Expect 422 for invalid configs (was 201 in v1.2.0)

See `RELEASE_NOTES_v1.3.0.md` for complete migration guide.

---

## Support

- **Documentation**: See README.md, FAQ.md
- **Examples**: web/EXAMPLE_USE_CASES.md
- **Templates**: web/config_templates/
- **Issues**: GitHub Issues

---

**API Specification Version**: 1.0
**API Version**: v1.3.0
**Last Updated**: 2025-11-11
