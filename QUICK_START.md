# 🚀 HydroClaude Quick Start

**Get up and running in 5 minutes!**

---

## Step 1: Install Dependencies (1 minute)

### Option A: Quick Install (Recommended)

```bash
pip install numpy pandas matplotlib jsonschema
```

### Option B: Use Installation Script

```bash
chmod +x install.sh
./install.sh
```

### Option C: Install Everything (including optional)

```bash
pip install numpy pandas matplotlib jsonschema h5py scipy
```

---

## Step 2: Generate a Configuration (30 seconds)

```bash
python3 hydro_engine.py --template steady_canal
```

This creates `config_template_steady_canal.json` with default parameters.

---

## Step 3: Run Your First Simulation (1 minute)

```bash
python3 hydro_engine.py config_template_steady_canal.json
```

You'll see:

```
================================================================================
  HydroClaude Hydraulic Simulation Engine
  Version: 1.0.0
================================================================================

✅ Configuration loaded: config_template_steady_canal.json
✅ Simulation completed: steady state
✅ Results saved to: results/steady_canal

📊 Output Files:
   - results.json        (Universal data model)
   - data/*.csv          (Data tables)
   - plots/*.png         (Figures)
   - reports/*.txt       (Validation reports)
   - web/index.html      (Interactive viewer)

✅ Simulation completed successfully
```

---

## Step 4: View Results (1 minute)

### Option A: Web Viewer (Recommended)

```bash
# macOS
open results/steady_canal/web/index.html

# Linux
xdg-open results/steady_canal/web/index.html

# Windows
start results/steady_canal/web/index.html
```

### Option B: Check Output Files

```bash
# View results summary
cat results/steady_canal/results.json

# View validation report
cat results/steady_canal/reports/validation_report.txt

# View data
head results/steady_canal/data/spatial_profile.csv
```

---

## Step 5: Customize Your Simulation (2 minutes)

Edit the generated `config_template_steady_canal.json`:

```json
{
  "simulation": {
    "type": "steady",
    "mode": "single_canal"
  },
  "canal": {
    "length": 1000,        // Change this
    "width": 10,           // Change this
    "slope": 0.001,        // Change this
    "manning_n": 0.025
  },
  "boundary_conditions": {
    "upstream": {
      "type": "flow",
      "value": 8.0         // Change this
    },
    "downstream": {
      "type": "depth",
      "method": "uniform_flow"
    }
  },
  "output": {
    "directory": "results/my_custom_case"  // Change this
  }
}
```

Then run again:

```bash
python3 hydro_engine.py config_template_steady_canal.json
```

---

## 🎉 Congratulations!

You've successfully:
- ✅ Installed HydroClaude
- ✅ Generated a configuration
- ✅ Run your first simulation
- ✅ Viewed the results
- ✅ Customized parameters

---

## Next Steps

### Try More Examples

```bash
# Sluice gate simulation
python3 hydro_engine.py --template gate
python3 hydro_engine.py config_template_gate.json

# Unsteady flow simulation
python3 hydro_engine.py --template unsteady_canal
python3 hydro_engine.py config_template_unsteady_canal.json
```

### Explore Example Configurations

```bash
cd examples_config/
cat README.md

# Run pre-made examples
python3 ../hydro_engine.py 01_steady_canal.json
python3 ../hydro_engine.py 02_gate_flow.json
python3 ../hydro_engine.py 03_unsteady_flow.json
```

### Read the Documentation

- **README.md** - Complete project overview
- **COMMERCIAL_ARCHITECTURE_V2.md** - Architecture details
- **LIBRARY_REFERENCE.md** - Solver API reference
- **CONTRIBUTING.md** - How to contribute

---

## Common Commands Cheat Sheet

```bash
# Generate templates
python3 hydro_engine.py --template steady_canal
python3 hydro_engine.py --template gate
python3 hydro_engine.py --template unsteady_canal

# Run simulation
python3 hydro_engine.py config.json

# Validate configuration only
python3 hydro_engine.py config.json --validate

# View configuration summary
python3 hydro_engine.py config.json --summary

# Verbose output
python3 hydro_engine.py config.json --verbose

# Custom output directory
python3 hydro_engine.py config.json -o my_results

# Version information
python3 hydro_engine.py --version

# Help
python3 hydro_engine.py -h
```

---

## Troubleshooting

### Issue: "python3: command not found"

**Solution**: Install Python 3.8+ from [python.org](https://www.python.org/)

### Issue: "ModuleNotFoundError: No module named 'numpy'"

**Solution**:

```bash
pip install numpy pandas matplotlib jsonschema
```

### Issue: "Permission denied: install.sh"

**Solution**:

```bash
chmod +x install.sh
./install.sh
```

### Issue: Configuration validation fails

**Solution**:

```bash
# Check your JSON syntax
python3 -m json.tool config.json

# Use verbose mode to see detailed errors
python3 hydro_engine.py config.json --verbose --validate
```

### Issue: Web viewer doesn't display

**Solution**:
- Use a modern browser (Chrome, Firefox, Edge, Safari)
- Check browser console for JavaScript errors
- Ensure `results.json` exists in the web directory

---

## Performance Tips

### For Large Simulations

```json
{
  "numerical": {
    "n_cells": 500,           // Reduce if too slow
    "cfl": 0.5,               // Increase for stability
    "max_iterations": 100     // Increase if not converging
  }
}
```

### For Faster Iterations

```json
{
  "output": {
    "save_plots": false,      // Skip plot generation
    "save_hdf5": false,       // Skip HDF5 (if installed)
    "generate_web": false     // Skip web viewer
  }
}
```

---

## Example Output Structure

```
results/steady_canal/
├── results.json              # Universal data model (main result)
├── data/
│   ├── spatial_profile.csv   # Water depth, velocity, etc.
│   └── results.h5            # HDF5 format (if h5py installed)
├── plots/
│   ├── water_surface_profile.png
│   ├── velocity_profile.png
│   └── froude_number_profile.png
├── reports/
│   └── validation_report.txt
└── web/
    ├── index.html            # Web viewer (open this!)
    ├── hydro_viewer.js
    ├── styles.css
    └── results.json          # Copy for web viewer
```

---

## Configuration File Structure

All configuration files follow this structure:

```json
{
  "simulation": {
    "type": "steady|unsteady",
    "mode": "single_canal|network"
  },
  "canal": {
    "length": 1000,
    "width": 10,
    "slope": 0.001,
    "manning_n": 0.025
  },
  "solver": {
    "method": "hydrostatic|godunov"
  },
  "boundary_conditions": {
    "upstream": {...},
    "downstream": {...}
  },
  "structures": [...],         // Optional
  "numerical": {...},          // Optional (uses defaults)
  "output": {...},             // Optional (uses defaults)
  "metadata": {...}            // Optional
}
```

See `examples_config/` for complete examples.

---

## Getting Help

### Quick Reference
- **⭐ START_HERE.md** - 30-second overview
- **This file** - 5-minute tutorial

### Detailed Documentation
- **README.md** - Complete project overview
- **COMMERCIAL_ARCHITECTURE_V2.md** - Architecture design
- **LIBRARY_REFERENCE.md** - API reference

### Community
- GitHub Issues - Report bugs
- GitHub Discussions - Ask questions
- CONTRIBUTING.md - Contribute code

---

## What's Next?

Now that you've completed the quick start, you can:

1. **Explore Advanced Features**
   - Add hydraulic structures (gates, weirs)
   - Run unsteady flow simulations
   - Optimize parameters

2. **Integrate into Your Workflow**
   - Create custom configuration templates
   - Automate batch simulations
   - Export data for further analysis

3. **Contribute**
   - Report bugs or suggest features
   - Improve documentation
   - Submit pull requests

---

<p align="center">
  <b>Welcome to HydroClaude!</b> 🌊
</p>

<p align="center">
  <a href="README.md">Full Documentation</a> •
  <a href="examples_config/README.md">Examples</a> •
  <a href="CONTRIBUTING.md">Contribute</a>
</p>

<p align="center">
  Made with ❤️ by HydroClaude Development Team
</p>
