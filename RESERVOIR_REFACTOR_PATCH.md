# Reservoir类重构补丁

## 需要修改的位置

### 1. 添加导入 (第25行后)
```python
from core.constants import PhysicsConstants, ReservoirDefaults
```

### 2. 修改__init__参数 (第90行)
```python
turbine_efficiency: float = None,  # 改为可选
# 新增参数:
spillway_coefficient: float = None,
spillway_length: float = None,
g: float = None,
```

### 3. 添加初始化代码 (第115行后)
```python
# 物理常数 - 使用默认值或用户指定值
self.g = g if g is not None else PhysicsConstants.GRAVITY

# 溢洪道参数
self.spillway_coefficient = spillway_coefficient if spillway_coefficient is not None else ReservoirDefaults.SPILLWAY_COEFFICIENT
self.spillway_length = spillway_length if spillway_length is not None else ReservoirDefaults.SPILLWAY_LENGTH

# 水轮机效率
turbine_efficiency = turbine_efficiency if turbine_efficiency is not None else ReservoirDefaults.TURBINE_EFFICIENCY
```

### 4. 修改_calculate_spillway_discharge (第319-320行)
```python
# 替换:
discharge_coefficient = 2.0
weir_length = 50.0

# 为:
# 使用实例变量
discharge = self.spillway_coefficient * self.spillway_length * opening * (head ** 1.5)
```

### 5. 修改发电计算 (第242行)
```python
# 替换 9.81 为 self.g
power = self.g * turbine_discharge * head * self.turbine_efficiency / 1000.0
```

### 6. 修改_constrain_turbine_discharge (第360行)
```python
# 替换 9.81 为 self.g
max_turbine_flow = self.turbine_capacity * 1000.0 / (self.g * head * self.turbine_efficiency)
```

### 7. 修改_get_max_turbine_flow (第386行)
```python
# 替换 9.81 为 self.g
return self.turbine_capacity * 1000.0 / (self.g * head * self.turbine_efficiency)
```

## 总结
这些更改将消除所有硬编码，使Reservoir类完全可配置化。
