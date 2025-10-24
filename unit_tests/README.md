# 单元测试文档

## 概述

HydroClaude单元测试套件使用pytest框架，提供全面的测试覆盖。

## 安装测试依赖

```bash
# 方法1: 直接安装pytest
pip install pytest pytest-cov

# 方法2: 从requirements.txt安装
pip install -r requirements.txt

# 方法3: 使用setup.py安装开发依赖
pip install -e .[dev]
```

## 运行测试

### 运行所有测试

```bash
# 基本运行
pytest

# 详细输出
pytest -v

# 显示测试覆盖率
pytest --cov=. --cov-report=html
```

### 运行特定测试文件

```bash
# 运行数据导出器测试
pytest unit_tests/test_data_exporter.py -v

# 运行配置模块测试
pytest unit_tests/test_modeling_config.py -v

# 运行求解器测试
pytest unit_tests/test_solver_basic.py -v
```

### 使用标记过滤测试

```bash
# 只运行快速测试（排除slow标记）
pytest -m "not slow"

# 只运行单元测试
pytest -m unit

# 只运行求解器相关测试
pytest -m solver
```

### 运行特定测试

```bash
# 运行特定测试类
pytest unit_tests/test_data_exporter.py::TestDataExporter -v

# 运行特定测试方法
pytest unit_tests/test_data_exporter.py::TestDataExporter::test_export_time_series_csv -v

# 使用关键字过滤
pytest -k "export" -v
```

## 测试结构

```
unit_tests/
├── __init__.py                  # 包初始化
├── conftest.py                  # 共享fixtures
├── test_data_exporter.py        # 数据导出器测试
├── test_modeling_config.py      # 配置模块测试
├── test_solver_basic.py         # 求解器基础测试
└── README.md                    # 本文件
```

## Fixtures

共享的测试fixtures在`conftest.py`中定义：

- `simple_canal_params`: 简单渠道参数字典
- `sample_grid`: 示例空间网格
- `sample_water_depth`: 示例水深数据
- `sample_flow`: 示例流量数据
- `temp_output_dir`: 临时输出目录
- `canal_solver`: 预配置的渠道求解器实例
- `data_exporter`: 数据导出器实例

## 测试标记

- `@pytest.mark.unit`: 单元测试
- `@pytest.mark.integration`: 集成测试
- `@pytest.mark.slow`: 运行缓慢的测试
- `@pytest.mark.benchmark`: 性能基准测试
- `@pytest.mark.solver`: 求解器测试
- `@pytest.mark.control`: 控制系统测试
- `@pytest.mark.structures`: 水工结构测试

## 编写新测试

### 基本测试结构

```python
import pytest
from module_to_test import ClassToTest

class TestClassName:
    """测试类文档"""

    def test_method_name(self):
        """测试方法文档"""
        # Arrange (准备)
        obj = ClassToTest(param=value)

        # Act (执行)
        result = obj.method()

        # Assert (断言)
        assert result == expected_value
```

### 使用fixtures

```python
def test_with_fixture(canal_solver):
    """使用fixture的测试"""
    result = canal_solver.solve_steady_state(10.0, 2.0)
    assert result['converged']
```

### 参数化测试

```python
@pytest.mark.parametrize("input,expected", [
    (1, 2),
    (2, 4),
    (3, 6),
])
def test_double(input, expected):
    assert input * 2 == expected
```

### 异常测试

```python
def test_raises_exception():
    with pytest.raises(ValueError):
        function_that_raises()
```

## 覆盖率报告

### 生成HTML报告

```bash
pytest --cov=. --cov-report=html
```

然后在浏览器中打开 `htmlcov/index.html`

### 显示未覆盖的行

```bash
pytest --cov=. --cov-report=term-missing
```

## 持续集成

测试会在以下情况自动运行：

- Git push到远程仓库
- 创建Pull Request
- 每日定时任务

查看`.github/workflows/tests.yml`了解CI配置详情。

## 最佳实践

1. **测试命名**: 使用描述性名称，如`test_export_time_series_csv`
2. **测试独立性**: 每个测试应该独立运行
3. **使用fixtures**: 共享设置代码
4. **参数化**: 避免重复的测试代码
5. **标记**: 使用标记分类测试
6. **文档**: 为测试类和方法添加文档字符串

## 故障排查

### pytest未找到

```bash
# 确保pytest已安装
pip install pytest

# 验证安装
pytest --version
```

### 模块导入错误

```bash
# 确保项目路径在PYTHONPATH中
export PYTHONPATH=/path/to/HydroClaude:$PYTHONPATH

# 或使用-e安装
pip install -e .
```

### fixture未找到

确保在正确的目录运行pytest，或者fixture在`conftest.py`中正确定义。

## 参考资料

- [Pytest官方文档](https://docs.pytest.org/)
- [Pytest fixtures文档](https://docs.pytest.org/en/latest/fixture.html)
- [Pytest参数化文档](https://docs.pytest.org/en/latest/parametrize.html)
