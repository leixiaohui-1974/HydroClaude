# ⚡ HydroClaude Quick Reference

**Essential commands and patterns at your fingertips**

---

## 🚀 Installation

```bash
# Minimal (core only)
pip install numpy pandas matplotlib jsonschema

# Standard (recommended)
pip install numpy pandas matplotlib jsonschema h5py scipy

# Full (everything)
pip install numpy pandas matplotlib jsonschema h5py scipy flask flask-cors requests psutil
```

---

## 📝 Command Line Interface

### Basic Commands

```bash
# Show version
python3 hydro_engine.py --version

# Show help
python3 hydro_engine.py --help

# Generate template
python3 hydro_engine.py --template steady_canal
python3 hydro_engine.py --template gate
python3 hydro_engine.py --template unsteady_canal

# Run simulation
python3 hydro_engine.py config.json

# Validate config only
python3 hydro_engine.py config.json --validate

# View config summary
python3 hydro_engine.py config.json --summary

# Verbose output
python3 hydro_engine.py config.json --verbose

# Custom output directory
python3 hydro_engine.py config.json -o my_results
```

---

## 📋 Configuration File Structure

### Minimal Configuration

```json
{
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
```

### With Hydraulic Structure

```json
{
  "simulation": {...},
  "canal": {...},
  "structures": [
    {
      "type": "sluice_gate",
      "position": 500,
      "parameters": {
        "width": 10,
        "opening": 2.0,
        "discharge_coeff": 0.6
      }
    }
  ]
}
```

---

## 🎯 Common Use Cases

### 1. Quick Simulation

```bash
python3 hydro_engine.py --template steady_canal
python3 hydro_engine.py config_template_steady_canal.json
open results/steady_canal/web/index.html
```

### 2. Batch Simulations

```bash
# Sequential
python batch_simulator.py examples_config/

# Parallel (4 workers)
python batch_simulator.py examples_config/ --parallel --workers 4

# Custom output
python batch_simulator.py examples_config/ -o batch_results/
```

### 3. Parameter Sweep

```python
from batch_simulator import BatchSimulator

batch = BatchSimulator()
batch.add_parameter_sweep(
    base_config,
    parameter_path='canal.manning_n',
    values=[0.020, 0.025, 0.030, 0.035, 0.040]
)
batch.run_parallel(workers=4)
```

### 4. Parameter Optimization

```python
from core.parameter_optimizer import optimize_manning_n

results = optimize_manning_n(
    config,
    observed_depth=depths,
    observed_positions=positions
)
print(f"Optimal Manning n: {results['optimal_parameters']['canal.manning_n']}")
```

---

## 🌐 REST API

### Start Server

```bash
python api/rest_server.py --host 0.0.0.0 --port 5000
```

### API Endpoints

```bash
# Health check
curl http://localhost:5000/api/health

# Create job
curl -X POST http://localhost:5000/api/jobs \
  -H "Content-Type: application/json" \
  -d @config.json

# List jobs
curl http://localhost:5000/api/jobs

# Get job details
curl http://localhost:5000/api/jobs/{job_id}

# Run job
curl -X POST http://localhost:5000/api/jobs/{job_id}/run

# Get results
curl http://localhost:5000/api/jobs/{job_id}/results

# Delete job
curl -X DELETE http://localhost:5000/api/jobs/{job_id}
```

---

## 🐍 Python SDK

### Basic Usage

```python
from sdk.hydroclaude_sdk import HydroClaudeClient

# Create client
client = HydroClaudeClient('http://localhost:5000')

# Check health
health = client.health()

# Submit and wait
results = client.submit_and_wait(config, name='my_sim')

# Step-by-step
job_id = client.create_job(config)
client.run_job(job_id, wait=True)
results = client.get_results(job_id)
client.delete_job(job_id)
```

### Job Wrapper

```python
from sdk.hydroclaude_sdk import Job

job = Job(client, job_id)
job.run(wait=True)
print(job.status)
print(job.results)
job.delete()
```

---

## 💾 Database

### Basic Operations

```python
from core.database_manager import DatabaseManager

db = DatabaseManager('hydroclaude.db')

# Create simulation
sim_id = db.create_simulation('test', config, tags=['dev', 'test'])

# Update status
db.update_simulation_status(sim_id, 'running')
db.update_simulation_status(sim_id, 'completed', completed_at='...')

# Save results
db.save_results(sim_id, results)

# Query
sims = db.list_simulations(status='completed', limit=10)
sim = db.get_simulation(sim_id)
results = db.get_results(sim_id)

# Statistics
stats = db.get_statistics()

# Search
results = db.search_simulations('channel')

# Close
db.close()
```

---

## 📊 Real-Time Monitoring

### Basic Usage

```python
from monitor.realtime_monitor import get_monitor

monitor = get_monitor()

# Log events
monitor.log_event('start', {'name': 'test'})

# Update metrics
monitor.update_metric('progress', 50.0)

# Add alerts
monitor.add_alert(
    'high_error',
    lambda e: e['data'].get('error', 0) > 0.1,
    'Error > 10%'
)

# Progress tracking
tracker = monitor.create_progress_tracker(100)
for i in range(100):
    tracker.update(i+1, f"Processing {i+1}")
tracker.complete()

# Get data
metrics = monitor.get_metrics()
events = monitor.get_events(limit=10)
alerts = monitor.get_triggered_alerts()
```

---

## 🔧 Performance Tips

### 1. Use HDF5 for Large Data

```json
{
  "output": {
    "save_hdf5": true,
    "hdf5_compression": "gzip"
  }
}
```

### 2. Disable Unnecessary Outputs

```json
{
  "output": {
    "save_plots": false,
    "generate_web": false
  }
}
```

### 3. Adjust Numerical Parameters

```json
{
  "numerical": {
    "n_cells": 100,
    "cfl": 0.5,
    "max_iterations": 100,
    "convergence_tol": 0.1
  }
}
```

### 4. Use Parallel Batch Processing

```bash
python batch_simulator.py configs/ --parallel --workers 8
```

---

## 🐛 Troubleshooting

### Check Dependencies

```python
python3 -c "import numpy, pandas, matplotlib, jsonschema; print('Core OK')"
python3 -c "import h5py, scipy; print('Advanced OK')"
python3 -c "import flask, requests; print('Enterprise OK')"
```

### Validate Configuration

```bash
python3 hydro_engine.py config.json --validate
```

### Enable Verbose Mode

```bash
python3 hydro_engine.py config.json --verbose
```

### Check API Health

```bash
curl http://localhost:5000/api/health
```

---

## 📁 Output Structure

```
results/[case_name]/
├── results.json              # Universal data model
├── data/
│   ├── spatial_profile.csv   # Spatial data
│   ├── temporal_series.csv   # Temporal data (if unsteady)
│   └── results.h5            # HDF5 (if enabled)
├── plots/
│   ├── water_surface_profile.png
│   ├── velocity_profile.png
│   └── ...
├── reports/
│   └── validation_report.txt
└── web/
    ├── index.html            # Web viewer
    ├── hydro_viewer.js
    ├── styles.css
    └── results.json          # Copy for web
```

---

## 🎯 Key File Locations

```
hydro_engine.py                  Main entry point
core/                            Core modules
  ├── config_parser.py           Configuration parser
  ├── simulation_engine.py       Simulation engine
  ├── output_manager.py          Output manager
  ├── hdf5_manager.py            HDF5 support
  ├── parameter_optimizer.py     Optimization
  ├── database_manager.py        Database
  └── performance_monitor.py     Profiling
templates/                       Web viewer
  ├── hydro_viewer.js
  ├── index_template.html
  └── styles.css
api/                             REST API
  └── rest_server.py
sdk/                             Python SDK
  └── hydroclaude_sdk.py
monitor/                         Monitoring
  └── realtime_monitor.py
batch_simulator.py               Batch processing
examples_config/                 Example configs
```

---

## 📚 Documentation Links

- **Quick Start**: `QUICK_START.md` - 5-minute tutorial
- **Complete Guide**: `README.md` - Full documentation
- **API Reference**: `API_DOCUMENTATION.md` - REST API & SDK
- **Features**: `FEATURES_MATRIX.md` - Feature comparison
- **Architecture**: `COMMERCIAL_ARCHITECTURE_V2.md` - Design docs
- **Contributing**: `CONTRIBUTING.md` - How to contribute

---

## 💡 Pro Tips

1. **Use templates** - Always start with `--template`
2. **Enable HDF5** - For datasets >100K points
3. **Batch parallel** - Use all CPU cores
4. **Monitor progress** - Real-time monitoring for long runs
5. **Database history** - Track all simulations
6. **SDK for automation** - Python SDK for workflows
7. **Validate first** - Use `--validate` before running
8. **Read docs** - `⭐_START_HERE.md` → `QUICK_START.md` → `README.md`

---

<p align="center">
  <b>HydroClaude Quick Reference v1.2.0</b>
</p>

<p align="center">
  <i>Keep this handy!</i> 🌊
</p>
