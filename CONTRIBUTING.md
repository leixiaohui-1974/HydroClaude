# Contributing to HydroClaude

Thank you for your interest in contributing to HydroClaude! 🎉

We welcome contributions of all kinds: bug reports, feature suggestions, documentation improvements, code contributions, and plugin development.

---

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How to Contribute](#how-to-contribute)
- [Development Setup](#development-setup)
- [Coding Standards](#coding-standards)
- [Pull Request Process](#pull-request-process)
- [Plugin Development](#plugin-development)
- [Community](#community)

---

## 📜 Code of Conduct

This project adheres to a [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

**TL;DR**: Be respectful, inclusive, and constructive.

---

## 🚀 Getting Started

### Prerequisites

- **Node.js** 18+ and npm
- **Python** 3.11+
- **Git**
- A code editor (VS Code recommended)

### Fork and Clone

```bash
# Fork the repository on GitHub
# Then clone your fork
git clone https://github.com/YOUR_USERNAME/hydroclaude.git
cd hydroclaude

# Add upstream remote
git remote add upstream https://github.com/hydroclaude/hydroclaude.git
```

---

## 🤝 How to Contribute

### 1. Reporting Bugs 🐛

**Before submitting**:
- Check if the bug has already been reported
- Collect information about your environment

**Submit a bug report**:
- Use the [Bug Report template](.github/ISSUE_TEMPLATE/bug_report.md)
- Include steps to reproduce
- Add screenshots if applicable
- Mention your OS and version

**Example**:
```markdown
**Environment**:
- OS: Windows 11
- HydroClaude Version: 2.0.0
- Node Version: 18.17.0

**Steps to Reproduce**:
1. Open Configuration Editor
2. Switch to JSON mode
3. Paste invalid JSON
4. Click Save

**Expected**: Error message
**Actual**: Application crashes

**Screenshots**: [attached]
```

---

### 2. Suggesting Features 💡

**Before suggesting**:
- Check existing feature requests
- Consider if it fits the project scope

**Submit a feature request**:
- Use the [Feature Request template](.github/ISSUE_TEMPLATE/feature_request.md)
- Explain the problem it solves
- Provide use cases
- Suggest implementation if possible

**Example**:
```markdown
**Feature**: Export to PDF

**Problem**: Users need to create reports for clients

**Proposed Solution**:
- Add "Export to PDF" button in Results page
- Include all charts and data tables
- Add optional text descriptions

**Use Case**: Engineering reports, academic papers

**Alternatives**: Manual screenshot collection (tedious)
```

---

### 3. Improving Documentation 📚

Documentation improvements are always welcome!

**Areas to improve**:
- Fix typos and grammar
- Add missing information
- Improve clarity
- Add examples
- Translate to other languages

**How to contribute**:
```bash
# 1. Find documentation file (*.md)
# 2. Make changes
# 3. Submit PR with clear description
```

---

### 4. Contributing Code 💻

See [Development Setup](#development-setup) below.

---

## 🛠️ Development Setup

### Backend (Python)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest
```

---

### Frontend (React)

```bash
# Navigate to webapp
cd webapp

# Install dependencies
npm install

# Start development server
npm run dev
# Visit: http://localhost:5173

# Run linter
npm run lint

# Type check
npm run type-check

# Build for production
npm run build
```

---

### Desktop App (Electron)

```bash
cd webapp

# Development mode
npm run dev:electron

# Build for current platform
npm run build:electron

# Build for all platforms (requires appropriate OS)
npm run build:electron -- --win --mac --linux
```

---

### Backend API (FastAPI)

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Run server
python run.py
# Visit: http://localhost:8000/docs

# Run tests
pytest tests/
```

---

## 📏 Coding Standards

### TypeScript/JavaScript

**Style**:
- Use TypeScript for all new code
- Follow ESLint rules (`.eslintrc.cjs`)
- Use Prettier for formatting
- Prefer functional components and hooks

**Naming**:
- `PascalCase` for components
- `camelCase` for functions and variables
- `UPPER_CASE` for constants

**Example**:
```typescript
// Good ✅
interface SimulationConfig {
  length: number;
  width: number;
}

export const ConfigEditor: React.FC = () => {
  const [config, setConfig] = useState<SimulationConfig>();
  
  const handleSave = async () => {
    // ...
  };
  
  return <div>{/* ... */}</div>;
};

// Bad ❌
function configEditor() {  // Should be PascalCase
  var Config;  // Use const/let, not var
  // ...
}
```

---

### Python

**Style**:
- Follow PEP 8
- Use type hints
- Add docstrings

**Example**:
```python
# Good ✅
from typing import Optional

def compute_depth(
    flow_rate: float,
    width: float,
    slope: float,
    roughness: float
) -> Optional[float]:
    """
    Compute water depth for given flow parameters.
    
    Args:
        flow_rate: Flow rate in m³/s
        width: Channel width in m
        slope: Channel slope (dimensionless)
        roughness: Manning's n
    
    Returns:
        Water depth in m, or None if computation fails
    """
    # Implementation...
    return depth

# Bad ❌
def compute_depth(Q, B, S, n):  # No type hints
    return depth  # No docstring
```

---

### Git Commit Messages

**Format**:
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting
- `refactor`: Code refactoring
- `test`: Tests
- `chore`: Maintenance

**Example**:
```
feat(config): add JSON schema validation

Add JSON schema validation to Configuration Editor to catch
errors before simulation starts. Includes:
- Schema definition
- Validation on save
- Error message display

Closes #123
```

---

## 🔄 Pull Request Process

### 1. Create a Branch

```bash
# Update your fork
git checkout main
git fetch upstream
git merge upstream/main

# Create feature branch
git checkout -b feature/my-awesome-feature
# or
git checkout -b fix/bug-description
```

---

### 2. Make Changes

- Write clean, well-documented code
- Add tests if applicable
- Update documentation
- Follow coding standards

---

### 3. Test Thoroughly

```bash
# Frontend
cd webapp
npm run lint
npm run type-check
npm run build

# Backend
cd backend
pytest
```

---

### 4. Commit Changes

```bash
git add .
git commit -m "feat: add awesome feature"
```

---

### 5. Push and Create PR

```bash
# Push to your fork
git push origin feature/my-awesome-feature
```

**On GitHub**:
1. Go to your fork
2. Click "Compare & pull request"
3. Fill in the PR template
4. Submit!

---

### 6. PR Review

**What happens next**:
- Maintainers will review your PR
- CI checks will run automatically
- You may be asked to make changes
- Once approved, your PR will be merged!

**Tips**:
- Respond to feedback promptly
- Be open to suggestions
- Keep the PR focused on one feature/fix

---

## 🔌 Plugin Development

Developing plugins is a great way to contribute!

### Plugin Structure

```
my-plugin/
├── plugin.json          # Manifest
├── src/
│   └── index.ts         # Entry point
├── README.md            # Documentation
└── examples/            # Usage examples
```

---

### Plugin Manifest

```json
{
  "id": "my-awesome-plugin",
  "name": "My Awesome Plugin",
  "version": "1.0.0",
  "description": "Does awesome things",
  "author": "Your Name",
  "homepage": "https://github.com/you/plugin",
  "repository": "https://github.com/you/plugin",
  "license": "MIT",
  "keywords": ["optimization", "analysis"],
  "permissions": [
    "simulation:read",
    "data:write",
    "ui:modify"
  ],
  "contributes": {
    "commands": [
      {
        "id": "my-plugin.doSomething",
        "title": "Do Something Awesome"
      }
    ]
  }
}
```

---

### Plugin Code

```typescript
import type { Plugin, PluginAPI } from '@/types/plugin';

class MyPlugin implements Plugin {
  manifest = { /* ... */ };
  
  async onActivate(api: PluginAPI) {
    // Register commands
    api.commands.register('my-plugin.doSomething', async () => {
      // Do something awesome
      api.ui.showMessage('Success!');
    });
    
    // Add UI button
    api.ui.addButton({
      id: 'my-button',
      label: 'Click Me',
      icon: 'star',
      onClick: () => {
        api.commands.execute('my-plugin.doSomething');
      }
    });
  }
  
  async onDeactivate() {
    // Cleanup
  }
}

export default new MyPlugin();
```

---

### Testing Your Plugin

```bash
# Copy to plugins directory
cp -r my-plugin plugins/examples/

# Restart application
npm run dev:electron
```

---

### Publishing Your Plugin

1. **Test thoroughly**
2. **Write documentation**
3. **Create GitHub repository**
4. **Submit to plugin marketplace** (coming soon)

See [Plugin Development Guide](./docs/plugins/getting-started.md) for details.

---

## 🌐 Community

### Communication Channels

- **GitHub Discussions**: General discussions, Q&A
- **GitHub Issues**: Bug reports, feature requests
- **Email**: dev@hydroclaude.com
- **Twitter**: @hydroclaude
- **WeChat**: HydroClaude

---

### Getting Help

**For users**:
- Check [documentation](./README.md)
- Search [existing issues](https://github.com/hydroclaude/hydroclaude/issues)
- Ask in [Discussions](https://github.com/hydroclaude/hydroclaude/discussions)

**For developers**:
- Read [development docs](./docs/)
- Check [API reference](./docs/plugins/api-reference.md)
- Ask in [Discussions](https://github.com/hydroclaude/hydroclaude/discussions)

---

## 🎉 Recognition

Contributors will be:
- Listed in [CONTRIBUTORS.md](./CONTRIBUTORS.md)
- Mentioned in release notes
- Featured on our website (with permission)

---

## 📄 License

By contributing, you agree that your contributions will be licensed under the [MIT License](./LICENSE).

---

<p align="center">
  <b>Thank you for contributing to HydroClaude! 🙏</b>
</p>

<p align="center">
  <i>Together, we're making hydraulic simulation better for everyone</i>
</p>

---

**© 2025 HydroClaude Development Team**
