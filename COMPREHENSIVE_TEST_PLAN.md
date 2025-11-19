# HydroClaude 全面测试方案 (Comprehensive Test Plan)

**版本**: 1.0
**日期**: 2025-11-18
**作者**: Jules

---

## 1. 简介与目标

本方案旨在为 HydroClaude 项目建立一个世界级的、全面的、自动化的测试体系。其核心目标是：

- **确保软件质量**: 保证从底层算法到前端UI的每一行代码都正确、可靠。
- **提升开发效率**: 通过自动化测试，快速获得代码变更的反馈，减少手动回归测试的成本。
- **增强系统健-壮性**: 覆盖边界条件、异常处理和真实世界的复杂场景。
- **对标商业软件**: 建立与业界领先的商业软件相匹配的质量保证流程。

## 2. 测试策略：测试金字塔

我们将采用经典的“测试金字塔”模型，该模型将测试分为多个层次，从底层快速、廉价的单元测试到顶层缓慢、昂贵的端到-端测试。

```
      /▲\
     /   \   L5: UI 端到端测试 (E2E UI Tests)
    /-----\
   /       \ L4: 前端组件测试 (Component Tests)
  /---------\
 /           \ L3: API 端点测试 (E2E API Tests)
/-------------\
/               \ L2: 集成测试 (Integration Tests)
/-----------------\
/                   \ L1: 单元测试 (Unit Tests)
---------------------
```

- **投资重点**: 我们的时间和精力将主要投入在金字塔的底部（L1, L2），以建立一个快速、稳定和可靠的测试基础。
- **自动化**: 所有 L1 到 L5 的测试都应被设计为完全自动化的，并集成到CI/CD流程中。

---

## 3. L1 - 单元测试 (Unit Tests)

**目标**: 验证最小的可测试代码单元（单个函数、方法或类）的行为是否符合预期。

**范围**:
- **后端**:
    - `models/` 目录下的所有物理模型类（例如 `SluiceGateModel`）。
    - `core/` 目录下的核心算法和数据结构。
    - `utils/` 目录下的所有工具函数。
- **前端**:
    - 独立的React组件中的业务逻辑函数。
    - Redux/Zustand中的状态管理逻辑。

**工具**:
- **后端**: `pytest`
- **前端**: `Jest`, `React Testing Library`

**示例代码 (后端 - `pytest`)**:
这是验证 `SluiceGateModel` 在自由流条件下计算是否正确的测试。

```python
# tests/models/test_gate_model.py

import pytest
from models.gate import SluiceGateModel

def test_sluice_gate_free_flow():
    """测试平板闸门在自由流条件下的计算"""
    gate = SluiceGateModel(width=5.0, opening=1.0, discharge_coeff=0.6)
    result = gate.calculate_discharge(upstream_depth=4.0, downstream_depth=0.8)

    assert result["flow_regime"] == "free"
    # 理论计算: Q = 0.6 * 5.0 * 1.0 * sqrt(2 * 9.81 * 4.0) = 26.57
    assert result["discharge"] == pytest.approx(26.57, rel=1e-2)
    assert result["error"] is None
```

---

## 4. L2 - 集成测试 (Integration Tests)

**目标**: 验证多个单元协同工作时是否正确。

**范围**:
- **后端**:
    - **服务层与模型层**: 验证 `services/simulation_service.py` 能否正确调用 `models` 中的物理模型。
    - **API层与服务层**: 验证 `routers/structures.py` 中的API端点能否正确地调用 `services` 层。
    - **核心引擎与求解器**: 验证 `core/simulation_engine.py` 能否正确地加载和运行 `solvers/` 目录下的求解器。
- **前端**:
    - 验证包含多个子组件的复杂组件的行为。
    - 验证组件与状态管理库（如Redux）的交互。

**工具**: `pytest` (后端), `React Testing Library` (前端)

**示例代码 (后端 - `pytest`)**:
这是一个测试 `simulation_service` 是否能成功调用 `SimulationEngine` 并返回预期结果的集成测试。

```python
# tests/services/test_simulation_service.py

from services.simulation_service import simulation_service

def test_service_runs_steady_simulation():
    """测试服务层能否成功运行一个稳态流仿真"""
    config = {
        "simulation": {"type": "steady", "mode": "standard"},
        "canal": {"length": 1000, "width": 10, ...},
        "structures": [{"type": "sluice_gate", ...}],
        "boundary_conditions": {...},
        ...
    }

    results = simulation_service.run_simulation_from_config(config)

    assert results["status"] == "completed"
    assert "hydro_result" in results
    assert results["simulation"]["type"] == "steady"
```

---

## 5. L3 - API 端点测试 (E2E API Tests)

**目标**: 从外部客户端的角度，验证API端点的请求和响应是否完全符合规范。这是对整个后端应用的“黑盒”测试。

**范围**:
- `web/backend/api_gateway/routers/` 目录下的所有API端点。
- 测试内容应包括：
    - 成功的请求 (`200 OK`)。
    - 错误的客户端输入 (`4xx Bad Request`)。
    - 服务器内部错误 (`5xx Internal Server Error`)。
    - 认证和授权（如果未来添加）。

**工具**: `pytest` + `httpx` (或 `fastapi.testclient.TestClient`)

**示例代码 (后端 - `pytest` + `httpx`)**:
这个测试模拟一个真实的HTTP客户端，向正在运行的API服务发送POST请求。

```python
# tests/api/test_api_endpoints.py

import pytest
import httpx

BASE_URL = "http://localhost:8000" # 假设API服务正在运行

def test_api_gate_endpoint():
    """测试 /api/structures/gate 端点"""
    request_data = {
        "gate": { "type": "sluice", "width": 5.0, "opening": 1.5, "discharge_coeff": 0.62 },
        "upstream_depth": 4.0,
        "downstream_depth": 2.0
    }

    with httpx.Client() as client:
        response = client.post(f"{BASE_URL}/api/structures/gate", json=request_data)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["metrics"]["discharge"] == pytest.approx(20.30, rel=1e-2)
```

---

## 6. L4 - 前端组件测试 (Component Tests)

**目标**: 在一个模拟的浏览器环境中，独立地测试React组件的渲染和交互行为。

**范围**:
- 所有位于 `frontend/components/` 目录下的React组件。
- 测试内容应包括：
    - 组件是否根据传入的 `props` 正确渲染。
    - 当用户与组件交互（如点击、输入）时，是否触发了预期的回调函数。
    - 组件是否能正确地处理从API获取的数据。

**工具**: `Jest` + `React Testing Library`

**示例代码 (前端 - `Jest`)**:
这个测试验证一个 `ParameterInput` 组件是否能正确地显示标签，并响应用户的输入。

```javascript
// frontend/components/ParameterInput.test.js

import { render, screen, fireEvent } from '@testing-library/react';
import ParameterInput from './ParameterInput';

test('renders input and responds to change', () => {
  const handleChange = jest.fn();

  render(<ParameterInput label="Flow Rate" value={10} onChange={handleChange} />);

  // 验证标签是否正确渲染
  const labelElement = screen.getByText(/Flow Rate/i);
  expect(labelElement).toBeInTheDocument();

  // 模拟用户输入
  const inputElement = screen.getByRole('textbox');
  fireEvent.change(inputElement, { target: { value: '20' } });

  // 验证 onChange 回调是否被正确调用
  expect(handleChange).toHaveBeenCalledWith('20');
});
```

---

## 7. L5 - UI 端到端测试 (E2E UI Tests)

**目标**: 模拟真实用户在浏览器中的完整操作流程，以验证整个系统（前端+后端）是否协同工作。

**范围**:
- 核心用户工作流，例如：
    1.  打开网页。
    2.  从下拉菜单中选择一个水工结构（如“闸门”）。
    3.  在表单中填写所有参数。
    4.  点击“运行仿真”按钮。
    5.  验证结果（如图表、数据显示）是否正确地显示在页面上。

**工具**: `Playwright` (推荐) 或 `Cypress`

**示例代码 (`Playwright`)**:

```javascript
// e2e_tests/simulation.spec.js

const { test, expect } = require('@playwright/test');

test('completes a full gate simulation workflow', async ({ page }) => {
  // 1. 访问网页
  await page.goto('http://localhost:8080/demo_webapp.html');

  // 2. 选择结构
  await page.selectOption('select#component-select', 'gate');

  // 3. 填写表单
  await page.fill('input#gate-width', '5.0');
  await page.fill('input#gate-opening', '1.5');
  // ... 填写其他参数

  // 4. 点击运行
  await page.click('button#run-simulation');

  // 5. 验证结果
  // 等待结果区域出现
  await page.waitForSelector('#results-container');

  // 验证结果中的某个关键数值是否正确显示
  const dischargeResult = await page.textContent('#result-discharge');
  expect(dischargeResult).toContain('20.30'); // 假设这是预期的流量结果
});

### 7.1. 视觉回归测试 (Visual Regression Testing)

**目标**: 自动捕捉用户界面的视觉变化（VRT），确保代码变更不会意外破坏页面布局、样式、颜色或图表渲染。

**原理**:
1.  **生成基准截图**: 在一个已知的、正确的版本上，运行测试并为关键页面或组件状态生成“基准”截图。
2.  **对比与差异分析**: 当代码发生变更后，重新运行测试，生成新的截图。
3.  **像素级对比**: 自动化工具会逐像素地对比新截图和基准截图。如果发现差异，测试将失败，并生成一个高亮显示差异的可视化报告。

**工具**: `Playwright` 内置的截图断言 (`toHaveScreenshot`)

**示例代码 (`Playwright`)**:
这个测试会在模拟用户操作后，对结果图表区域进行截图，并与之前存储的基准图片进行对比。

```javascript
// e2e_tests/visual_validation.spec.js

const { test, expect } = require('@playwright/test');

test('validates the visual appearance of the results chart', async ({ page }) => {
  // ... 执行与上面测试相同的仿真步骤 ...
  await page.goto('http://localhost:8080/demo_webapp.html');
  await page.selectOption('select#component-select', 'gate');
  await page.fill('input#gate-width', '5.0');
  await page.fill('input#gate-opening', '1.5');
  await page.click('button#run-simulation');
  await page.waitForSelector('#results-container');

  // 选取图表所在的容器元素
  const chartContainer = await page.$('#chart-container');

  // 断言该元素的截图与名为 'simulation-chart.png' 的基准截图匹配
  // 第一次运行时，Playwright 会提示找不到基准，并自动创建它。
  // 后续运行时，它将进行对比。
  // `maxDiffPixels` 允许有少量像素差异，以应对抗锯齿等渲染波动。
  await expect(chartContainer).toHaveScreenshot('simulation-chart.png', {
    maxDiffPixels: 100
  });
});
```
```

---

## 8. 性能与兼容性测试

### 性能测试
- **后端压力测试**: 使用 `locust` 或 `k6` 等工具，模拟大量并发用户向API发送请求，以测试系统的吞吐量（QPS）、响应时间和稳定性。
- **前端性能测试**: 使用 `Google Lighthouse` 或 `Playwright` 的性能追踪功能，分析页面的加载速度、首次内容绘制（FCP）等关键指标。

### 兼容性测试
- **操作系统兼容性**: 在CI/CD流程中，应包含在不同操作系统（Linux, Windows）上运行测试的步骤。特别注意Windows中文环境下的文件路径、编码和命令行执行。
- **浏览器兼容性**: E2E测试应配置为在主流浏览器（Chrome, Firefox, Safari）上运行，以确保跨浏览器的一致性。

---

## 9. 回归测试策略

**目标**: 确保新的代码变更没有破坏任何现有功能。

**策略**:
- **CI/CD 集成**: 所有测试（L1-L5）都应被集成到项目的CI/CD流程中（如 GitHub Actions）。
- **触发机制**:
    - **每次提交 (On Push)**: 自动运行所有 L1 单元测试和 L2 集成测试。这能提供最快速的反馈。
    - **创建合并请求 (On Pull Request)**: 自动运行所有 L1, L2, L3 (API) 和 L4 (组件) 测试。
    - **合并到主分支后/每日构建 (Nightly Build)**: 运行所有测试，包括最耗时的 L5 E2E UI 测试和性能测试。

通过实施这一全面的测试方案，HydroClaude 项目将能够建立起强大的质量壁垒，确保每一次发布都是高质量、高可靠性的。
