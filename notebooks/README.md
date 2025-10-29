# HydroClaude Jupyter Notebooks

**Version**: 1.0
**Date**: 2025-10-29
**Status**: Initial Release

## Overview

This directory contains interactive Jupyter notebooks for learning and using HydroClaude. Each notebook provides hands-on examples with explanations, visualizations, and exercises.

## Available Notebooks

### Beginner Level

| Notebook | Topic | Duration | Prerequisites |
|----------|-------|----------|---------------|
| `01_getting_started.ipynb` | Basic simulation setup | 20-30 min | Python basics |
| `02_dam_break.ipynb` | Transient flow | 30 min | Notebook 01 |
| `03_backwater_curve.ipynb` | Subcritical flow profiles | 30 min | Notebook 01 |

### Intermediate Level

| Notebook | Topic | Duration | Prerequisites |
|----------|-------|----------|---------------|
| `04_supercritical_flow.ipynb` | Supercritical BC | 40 min | Notebooks 01-03 |
| `05_boundary_conditions.ipynb` | BC types and setup | 40 min | Notebook 01 |
| `06_grid_convergence.ipynb` | Numerical accuracy | 45 min | Notebooks 01-03 |

### Advanced Level

| Notebook | Topic | Duration | Prerequisites |
|----------|-------|----------|---------------|
| `07_macdonald_tests.ipynb` | Validation suite | 60 min | All previous |
| `08_custom_scenarios.ipynb` | Custom simulations | 60 min | All previous |

**Note**: Notebooks 02-08 are planned for future development.

## Getting Started

### Installation

1. **Install Jupyter** (if not already installed):
```bash
pip install jupyter notebook matplotlib
```

2. **Install HydroClaude dependencies**:
```bash
cd /path/to/HydroClaude
pip install -r requirements.txt
```

### Running Notebooks

1. **Start Jupyter**:
```bash
cd /path/to/HydroClaude/notebooks
jupyter notebook
```

2. **Open a notebook** in your browser (usually opens automatically at `http://localhost:8888`)

3. **Run cells** by pressing `Shift+Enter` or clicking the "Run" button

### Alternative: JupyterLab

For a more modern interface:
```bash
pip install jupyterlab
jupyter lab
```

## Notebook Structure

Each notebook follows this structure:

1. **Introduction**: Overview and learning objectives
2. **Setup**: Import libraries and configure environment
3. **Theory**: Relevant physics and mathematics
4. **Implementation**: Step-by-step code examples
5. **Visualization**: Plots and analysis
6. **Exercises**: Optional practice problems
7. **Summary**: Key takeaways and next steps

## Tips for Learning

### For Beginners

1. **Start with 01_getting_started.ipynb**
2. **Run all cells in order** - don't skip!
3. **Experiment** - modify parameters and see what happens
4. **Read the comments** - they explain the code
5. **Ask questions** - open GitHub issues if stuck

### For Advanced Users

1. **Jump to relevant notebooks** based on your needs
2. **Use as templates** for your own projects
3. **Contribute improvements** via pull requests

## Common Issues

### Import Error: "No module named 'engine'"

**Solution**: Make sure you're running from the notebooks directory and the notebook includes:
```python
import sys
sys.path.insert(0, '..')
```

### Kernel Crashes or Slow Performance

**Solution**:
1. Restart kernel: `Kernel` → `Restart`
2. Reduce grid resolution: `'n_cells': 50` instead of 200
3. Enable Numba: `'use_numba': True`

### Plots Don't Show

**Solution**: Add at the beginning:
```python
%matplotlib inline
```

### "Working tree clean" Git Warning

This is normal - it's from checking git status, not an error.

## Notebook Dependencies

Required Python packages:
- `numpy` (≥1.20)
- `matplotlib` (≥3.3)
- `scipy` (optional, for advanced notebooks)
- `numba` (optional but recommended, 10-100x speedup)

Install all:
```bash
pip install numpy matplotlib scipy numba
```

## Contributing

Want to contribute a notebook? Great! Please follow these guidelines:

### Notebook Requirements

1. **Clear title and description**
2. **Step-by-step explanations**
3. **Working code examples**
4. **Visualizations** using matplotlib
5. **Comments** for all non-obvious code
6. **Estimated duration**
7. **Prerequisites list**

### Style Guide

- Use descriptive variable names
- Include docstrings for functions
- Add markdown cells for explanations
- Keep code cells focused (one concept per cell)
- Test thoroughly before submitting

### Submission Process

1. Fork the repository
2. Create notebook in `notebooks/` directory
3. Test completely (restart kernel and run all)
4. Update this README with your notebook info
5. Submit pull request

## Additional Resources

### Documentation
- [Godunov FVM User Guide](../docs/GODUNOV_FVM_USER_GUIDE.md) - Complete solver documentation
- [Project Status](../docs/PROJECT_STATUS_2025_10_29.md) - Current project state
- [Test Documentation](../tests/diagnostic/README.md) - Validation and diagnostics

### Code Examples
- [MacDonald Tests](../tests/standard_tests/test_macdonald.py) - Benchmark validation cases
- [Examples Directory](../examples/) - 24+ application examples
- [Diagnostic Tests](../tests/diagnostic/) - 53 verification tests

### Theory and Background
- Saint-Venant Equations: See main README.md
- Godunov Method: Toro, "Riemann Solvers and Numerical Methods for Fluid Dynamics"
- Open Channel Hydraulics: Chow, "Open Channel Hydraulics"

## Future Notebooks (Planned)

### Short-term (1-2 weeks)
- `02_dam_break.ipynb` - Transient flow and shock waves
- `03_backwater_curve.ipynb` - Gradually varied flow
- `04_supercritical_flow.ipynb` - High-speed flow regime

### Medium-term (1-2 months)
- `05_boundary_conditions.ipynb` - BC types and relaxation method
- `06_grid_convergence.ipynb` - Numerical accuracy analysis
- `07_macdonald_tests.ipynb` - Complete validation suite

### Long-term (3+ months)
- `08_custom_scenarios.ipynb` - Build your own simulations
- `09_parameter_sensitivity.ipynb` - Uncertainty quantification
- `10_advanced_techniques.ipynb` - MUSCL, WENO, shock-capturing

## Feedback

We'd love to hear from you!

- **Found a bug?** Open an issue on GitHub
- **Have a suggestion?** Create a feature request
- **Want to contribute?** Submit a pull request

## FAQ

### Q: Do I need to know hydraulics to use these notebooks?

A: The beginner notebooks include basic hydraulics explanations, but some background helps. We recommend:
- Basic fluid mechanics
- Open channel flow concepts (depth, discharge, Froude number)
- Differential equations (helpful but not required)

### Q: Can I use these notebooks for my research/project?

A: Yes! HydroClaude is open-source. Please cite the project if you use it in publications.

### Q: How accurate are the simulations?

A: For subcritical flows: typically 2-5% error. For complex flows: 15-20% (acceptable for engineering). See validation tests for details.

### Q: Can I run these on Google Colab?

A: Yes! Upload the notebook to Colab and add at the beginning:
```python
# Install HydroClaude (only first time)
!git clone https://github.com/your-username/HydroClaude.git
import sys
sys.path.insert(0, 'HydroClaude')
```

### Q: Where can I find more examples?

A: Check the `examples/` directory - it has 24+ complete application examples including:
- Canal flow
- Pump systems
- Control strategies
- Water resource optimization

## License

These notebooks are part of the HydroClaude project and share the same license. See main repository LICENSE file.

## Acknowledgments

These notebooks were created as part of the HydroClaude development effort (2025-10-29) to provide accessible, interactive learning materials for hydraulic modeling.

---

**Happy Learning! 🌊📓**

*For questions or support, please open an issue on GitHub.*
