# 🤝 Contributing to HydroClaude

Thank you for considering contributing to HydroClaude! This document provides guidelines for contributing to the project.

---

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Pull Request Process](#pull-request-process)
- [Release Process](#release-process)

---

## 📜 Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for all contributors.

### Our Standards

- Use welcoming and inclusive language
- Be respectful of differing viewpoints
- Accept constructive criticism gracefully
- Focus on what's best for the community
- Show empathy towards other community members

---

## 🚀 Getting Started

### Ways to Contribute

1. **Report Bugs** 🐛
   - Use GitHub Issues
   - Include detailed reproduction steps
   - Provide system information

2. **Suggest Features** 💡
   - Use GitHub Discussions
   - Explain the use case
   - Consider implementation details

3. **Improve Documentation** 📝
   - Fix typos and clarify content
   - Add examples
   - Translate to other languages

4. **Submit Code** 🔧
   - Fix bugs
   - Implement features
   - Optimize performance

5. **Review Pull Requests** 👀
   - Test changes
   - Provide feedback
   - Approve quality contributions

---

## 💻 Development Setup

### Prerequisites

- Python 3.8+
- Git
- Text editor or IDE

### Initial Setup

```bash
# 1. Fork and clone the repository
git clone https://github.com/YOUR_USERNAME/HydroClaude.git
cd HydroClaude

# 2. Create a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements_engine.txt

# 4. Install development dependencies
pip install pytest pytest-cov flake8 black isort

# 5. Run tests to verify setup
python3 test_basic.py
```

### Directory Structure

```
HydroClaude/
├── core/                   # Core engine modules
├── solvers/                # Solver implementations
├── utils/                  # Utility functions
├── templates/              # Web viewer templates
├── examples_config/        # Example configurations
├── tests/                  # Test files
└── docs/                   # Documentation
```

---

## 🎯 How to Contribute

### 1. Find an Issue

- Browse [GitHub Issues](https://github.com/HydroClaude/HydroClaude/issues)
- Look for issues tagged `good first issue` or `help wanted`
- Comment on the issue to claim it

### 2. Create a Branch

```bash
# Create a feature branch
git checkout -b feature/your-feature-name

# Or a bugfix branch
git checkout -b fix/your-bugfix-name
```

### 3. Make Changes

- Follow the [Coding Standards](#coding-standards)
- Write or update tests
- Update documentation if needed

### 4. Test Your Changes

```bash
# Run basic tests
python3 test_basic.py

# Run specific test
python3 -m pytest tests/test_your_feature.py

# Check code formatting
black --check .
flake8 .
isort --check .
```

### 5. Commit Your Changes

```bash
# Stage your changes
git add .

# Commit with a descriptive message
git commit -m "feat: add support for X"

# Or for bug fixes
git commit -m "fix: resolve issue with Y"
```

**Commit Message Format**:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting, etc.)
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks

### 6. Push and Create Pull Request

```bash
# Push to your fork
git push origin feature/your-feature-name

# Create PR on GitHub
# Fill in the PR template
```

---

## 📏 Coding Standards

### Python Style Guide

We follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) with some modifications:

```python
# Use 4 spaces for indentation
# Maximum line length: 100 characters
# Use double quotes for strings

# Good
def calculate_flow(width, depth, velocity):
    """Calculate flow rate.
    
    Args:
        width (float): Channel width in meters
        depth (float): Flow depth in meters
        velocity (float): Flow velocity in m/s
    
    Returns:
        float: Flow rate in m³/s
    """
    return width * depth * velocity

# Bad
def calculate_flow(w,d,v):
    return w*d*v  # No docstring, unclear variables
```

### Documentation

```python
# Use Google-style docstrings

def function_name(param1, param2):
    """Brief description.
    
    Longer description if needed.
    
    Args:
        param1 (type): Description
        param2 (type): Description
    
    Returns:
        type: Description
    
    Raises:
        ExceptionType: Description
    
    Example:
        >>> function_name(1, 2)
        3
    """
    pass
```

### Code Organization

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module description

Author: Your Name
Date: YYYY-MM-DD
"""

# 1. Standard library imports
import sys
import os

# 2. Third-party imports
import numpy as np
import pandas as pd

# 3. Local imports
from core.config_parser import ConfigParser
from utils.canal_utils import compute_steady_uniform_flow

# 4. Constants
DEFAULT_MANNING = 0.025
GRAVITY = 9.81

# 5. Classes and functions
class MyClass:
    pass

def my_function():
    pass

# 6. Main execution
if __name__ == '__main__':
    main()
```

### Formatting Tools

```bash
# Auto-format with black
black .

# Sort imports with isort
isort .

# Check style with flake8
flake8 .
```

---

## 🧪 Testing Guidelines

### Test Structure

```python
def test_feature_name():
    """Test specific functionality."""
    # Arrange
    input_data = setup_test_data()
    
    # Act
    result = function_to_test(input_data)
    
    # Assert
    assert result == expected_value
    assert result > 0
```

### Test Coverage

- Aim for >80% code coverage
- Test edge cases
- Test error handling
- Include integration tests

### Running Tests

```bash
# Run all tests
python3 test_basic.py

# Run with coverage
pytest --cov=core --cov=solvers --cov=utils

# Run specific test file
pytest tests/test_config_parser.py

# Run specific test
pytest tests/test_config_parser.py::test_parse_valid_config
```

---

## 🔄 Pull Request Process

### Before Submitting

- [ ] Code follows style guidelines
- [ ] Tests pass locally
- [ ] Documentation updated
- [ ] Commit messages are clear
- [ ] Branch is up to date with main

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
How has this been tested?

## Checklist
- [ ] Code follows style guidelines
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] All tests pass
```

### Review Process

1. **Automated Checks**
   - CI tests must pass
   - Code coverage maintained
   - No linting errors

2. **Code Review**
   - At least one approval required
   - Address review comments
   - Keep discussions constructive

3. **Merge**
   - Squash commits if needed
   - Update CHANGELOG
   - Celebrate! 🎉

---

## 📦 Release Process

### Version Numbering

We use [Semantic Versioning](https://semver.org/):

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes

Example: `1.2.3`

### Creating a Release

```bash
# 1. Update version number
# Edit relevant files

# 2. Update CHANGELOG.md
# Document all changes

# 3. Create tag
git tag -a v1.2.3 -m "Release version 1.2.3"

# 4. Push tag
git push origin v1.2.3

# 5. GitHub Actions will handle the rest
```

---

## 🎓 Best Practices

### Core Library Usage

**Always use existing libraries**:

```python
# ✅ Good - Use existing library
from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
from utils.canal_utils import compute_steady_uniform_flow
from utils.result_validator import quick_validate_steady_state

# ❌ Bad - Don't reimplement
def my_own_solver():  # Don't do this!
    pass
```

### Error Handling

```python
# ✅ Good
try:
    result = risky_operation()
except SpecificException as e:
    logger.error(f"Operation failed: {e}")
    raise

# ❌ Bad
try:
    result = risky_operation()
except:  # Too broad
    pass  # Silent failure
```

### Performance

- Profile before optimizing
- Use NumPy for array operations
- Avoid premature optimization
- Document performance requirements

---

## 📞 Getting Help

### Resources

- **Documentation**: See `*.md` files in repository
- **Issues**: [GitHub Issues](https://github.com/HydroClaude/HydroClaude/issues)
- **Discussions**: [GitHub Discussions](https://github.com/HydroClaude/HydroClaude/discussions)

### Questions?

- Check existing documentation first
- Search closed issues
- Ask in GitHub Discussions
- Be specific and include context

---

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

## 🙏 Recognition

Contributors are recognized in:
- CONTRIBUTORS.md
- Release notes
- GitHub contributors page

Thank you for contributing to HydroClaude! 🌊

---

<p align="center">
  <b>Happy Contributing!</b> ❤️
</p>

<p align="center">
  Made with ❤️ by HydroClaude Development Team
</p>
