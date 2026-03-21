# `physics/structures/culvert.py` 差距分析（HEC-RAS / FHWA HDS-5）

## 结论

`physics/structures/culvert.py` 目前实现的是一个“简化孔口公式 + 简化满流能量方程”的涵洞模型，能够给出一个粗略流量，但**还不能视为 FHWA HDS-5 / HEC-RAS 意义上的标准涵洞求解器**。  

最核心的缺口有四个：

1. **进口控制方程族没有实现**：当前只用一个按进口类型切换的常数 `Cd`，没有 HDS-5 的 `K / M / c / Y` 系数体系。
2. **进口控制 / 出口控制的判定方法不正确**：当前并没有在同一个流量或同一个可用水头下真正比较两种控制的“所需上游水头”。
3. **淹没修正不符合 HDS-5**：当前没有按 HDS-5 处理“淹没进口”和“尾水淹没出口”，也没有关键的临界水深 / 正常水深 / 自由出流判据。
4. **材质系数体系缺失**：没有“管材 + 断面 + 进口形式”的标准系数库，导致无法对标 HEC-RAS / HDS-5 的 concrete / CMP / smooth / corrugated 等差异。

换句话说，当前代码可以当作“工程估算版”，但不能当作“标准对标版”。

---

## 1) 当前已实现的功能列表

以下内容在 `physics/structures/culvert.py` 中已经实现，但多数属于**简化版**：

- 支持 3 种几何类型：`circular`、`rectangular`、`arch`。
- 对圆形 / 矩形 / 拱形几何参数做了基本合法性校验。
- 提供了满流断面面积 `area()`。
- 提供了水力半径 `hydraulic_radius(depth)`，圆形支持部分充满，矩形支持按水深计算，拱形仍是近似算法。
- 提供了一个简化的进口类型参数 `inlet_type`，并用 `_get_discharge_coefficient()` 生成常数 `Cd`。
- 提供了一个简化的进口控制计算 `_inlet_control()`：
  - 用 `h_upstream < 1.2D` 作为未淹没 / 淹没进口分界。
  - 两个分支本质上都还是孔口公式 `Q = Cd * A * sqrt(2gH)`。
- 提供了一个简化的出口控制计算 `_outlet_control()`：
  - 假定满流断面。
  - 采用 Manning 摩阻 + 入口损失 + 出口损失的迭代能量方程。
- 提供了总水头损失计算 `compute_headloss()`。
- 提供了数值差分导数 `get_derivatives()`。
- 提供了便捷构造函数：
  - `create_circular_culvert()`
  - `create_rectangular_culvert()`
- 提供了一个简化的设计校核接口 `validate_culvert_design()`。

这些功能说明模块已经具备“涵洞对象 + 基本流量估算”的框架，但与 HDS-5 / HEC-RAS 的差距主要集中在**控制方程、淹没判定、材质系数和几何/水深状态求解**。

---

## 2) 缺失的关键功能

下面按优先级列出关键缺口。

| 优先级 | 缺失功能 | HDS-5 / HEC-RAS 要求 | 当前实现问题 | 影响 |
| --- | --- | --- | --- | --- |
| P0 | 标准进口控制方程族 | 采用 HDS-5 入口控制经验方程与 `K / M / c / Y` 系数表 | 当前仅按 `inlet_type` 选一个常数 `Cd`，对所有形状 / 材质都套孔口公式 | 无法复现标准 headwater-discharge 曲线 |
| P0 | 正确的进口/出口控制判定 | 应在“同一流量下比较所需上游水头”，或“同一可用上游水头下比较可过流能力” | `compute_discharge()` 当前并未真正比较两条标准控制曲线 | `control_type` 可能错误，且控制切换点不可信 |
| P0 | 淹没进口处理 | HDS-5 要有“未淹没入口”和“淹没入口”两套入口控制关系 | 当前只用 `1.2D` 门槛后把驱动头改成 `h_upstream - D/2` | 淹没进口时流量偏差可能很大 |
| P0 | 尾水淹没 / 出口控制深度处理 | HDS-5 需用 `TW`、临界水深 `y_c`、自由出流出口深度 `h_o` 共同决定出口控制 | 当前直接把 `h_downstream` 线性加进能量方程，没有 `y_c` / `h_o` 逻辑 | 高尾水、自由出流、近满流工况都会失真 |
| P0 | 材质系数体系 | 管材不仅影响 Manning `n`，还影响入口控制系数族 | 当前只有一个手填 `manning_n` 和 4 个全局 `Cd`，没有 material/corrugation 维度 | concrete、CMP、smooth plastic 等无法区分 |
| P1 | 临界水深 / 正常水深 / 部分充满流 | HEC-RAS/HDS-5 出口控制需要 `y_c`、必要时 `y_n`，区分满流与非满流 | 当前出口控制总是假定满流面积和满流水力半径 | 低尾水、陡坡、短管、部分充满工况误差大 |
| P1 | 精确几何水力函数 | 需要 `area(depth)`、`top_width(depth)`、`wetted_perimeter(depth)`，至少圆管/箱涵/拱涵要精确 | 当前 `area()` 只给满流面积；拱涵几何为粗略近似 | 无法可靠求临界水深、正常水深和部分充满损失 |
| P1 | 多孔涵洞 | HEC-RAS 常见多孔并联，数据模型里也已有 `n_barrels` | 当前 `physics/structures/culvert.py` 不支持 `n_barrels` | 多孔能力被低估，且无法对接已有数据模型 |
| P1 | 进口类型标准化 | HDS-5 入口类型应和系数表一一对应 | `hydromind_data_format.py` 中 `headwall/mitered/projecting` 与当前 `groove_end/groove_headwall/beveled` 不一致 | 适配器无法无损映射到物理模型 |
| P1 | 反算所需壅水深 | HDS-5 设计通常是给定 `Q` 反算 `HW` | 当前只有 `Q(HW, TW)`，没有可靠的 `HW(Q, TW)` 标准接口 | 设计校核与对标报告难做 |
| P2 | 进口速度头 / 接近段修正 | HEC-RAS 会考虑 approach velocity head、上游接近断面条件 | 当前 API 只有水深，没有 approach energy correction | 高流速接近段时 headwater 偏差增大 |
| P2 | 更完整的 HEC-RAS crossing 功能 | 包括道路漫顶、多个 opening、复杂 crossing 组合 | 当前仅是单个 barrel 级别模型 | 无法直接对标完整道路涵洞 crossing 结果 |

### 2.1 重点问题一：进口控制 / 出口控制判定目前并不符合标准

标准做法有两种等价形式：

- **给定流量 `Q`**：分别计算入口控制和出口控制所需上游水头，谁需要的水头更高，谁就是控制工况。
- **给定上游水头 `HW` 与尾水 `TW`**：分别求入口控制和出口控制所允许的流量，谁允许的流量更小，谁就是控制工况。

当前代码并没有做这件事。

具体问题：

- `_inlet_control()` 返回的是 `(Q, h_upstream)`，第二个返回值本质上只是把输入原样回传。
- `_outlet_control()` 会迭代 `Q_guess`，直到 `H_required ≈ h_upstream`。
- `compute_discharge()` 再拿这两个“头”比较：
  - `H_inlet = h_upstream`
  - `H_outlet ≈ h_upstream`

这意味着当前所谓“控制判定”大多只是比较两个非常接近的数，而不是比较两条标准控制曲线。  
这也是当前文件里**最根本的物理逻辑问题**。

### 2.2 重点问题二：淹没修正目前不是 HDS-5 的做法

对于涵洞，**不能用堰流那种统一的 `submergence_factor` 乘子去替代标准处理**。  
HDS-5/HEC-RAS 对“淹没”的处理至少分三类：

- **淹没进口（submerged inlet）**：入口控制应改用 HDS-5 的淹没入口方程，而不是简单改成 `H = h_upstream - D/2`。
- **尾水淹没出口（submerged outlet）**：出口控制应使用 `h_o = max(TW, h_o_free)` 之类的出口控制深度逻辑，其中 `h_o_free` 依赖临界水深 / 满流状态。
- **自由出流与近满流过渡**：需要用 `y_c`、必要时 `y_n` 判断 barrel 是部分充满还是满流，而不能始终按满流处理。

当前代码缺失：

- 没有临界水深 `y_c` 求解。
- 没有正常水深 `y_n` 求解。
- 没有自由出流出口深度 `h_o_free` 规则。
- 没有尾水是否真正控制出口断面的标准判据。
- 没有满流 / 非满流的转换逻辑。

### 2.3 重点问题三：管道材质系数目前只实现了很小一部分

当前文件里只有：

- 一个手工输入的 `manning_n`
- 一个与材质无关的 `Cd` 映射表

但在 HDS-5 / HEC-RAS 里，**材质不是单独只影响 Manning `n`**，还会影响：

- 入口控制所使用的系数表族
- 入口形式可选项
- 某些默认的入口损失建议值
- corrugated / smooth 不同 barrel 的水力行为

也就是说，当前实现无法表达下面这些常见标准差异：

- 混凝土圆管 vs 波纹金属管
- smooth interior vs corrugated interior
- projecting inlet vs headwall vs mitered to slope
- box culvert vs circular barrel 的不同经验系数

### 2.4 其他重要但次一级的缺口

- `arch` 断面目前只有粗略几何近似，无法支撑标准级计算。
- `validate_culvert_design()` 不是标准设计思路里最常用的“给定 `Q_design` 反算 `HW_required`”接口。
- 当前测试 `tests/test_culvert.py` 基本是在验证“当前简化公式能运行”，而不是在验证“是否符合 HDS-5 / HEC-RAS”。

---

## 3) 具体的修复方案（含代码伪代码）

建议按照“**先做到 HDS-5 最小合规，再向 HEC-RAS 完整 crossing 靠拢**”的顺序修。

### 3.1 先扩展数据结构与系数库

当前最需要补的不是一个新公式，而是**系数与配置层**。

建议新增：

```python
from dataclasses import dataclass
from typing import Literal, Optional


@dataclass(frozen=True)
class InletCoefficients:
    K: float
    M: float
    c: float
    Y: float
    slope_coef: float = 0.0  # 不同 HDS-5 系数族可使用不同坡度修正
    default_ke: Optional[float] = None


@dataclass(frozen=True)
class MaterialProperties:
    default_n: float
    inlet_family: str   # 用来索引 HDS-5 入口控制系数表


BARREL_MATERIALS = {
    # 数值只是示意；正式实现必须以 HDS-5 / HEC-RAS 表值为准
    "concrete": MaterialProperties(default_n=0.012, inlet_family="concrete"),
    "corrugated_metal": MaterialProperties(default_n=0.024, inlet_family="cmp"),
    "smooth_steel": MaterialProperties(default_n=0.012, inlet_family="smooth_pipe"),
    "plastic_smooth": MaterialProperties(default_n=0.011, inlet_family="smooth_pipe"),
}


INLET_COEFF_TABLE = {
    # key 示例：(shape, inlet_family, inlet_type)
    # 实际应按 HDS-5 表完整录入
    ("circular", "concrete", "projecting"): InletCoefficients(...),
    ("circular", "concrete", "headwall"): InletCoefficients(...),
    ("circular", "cmp", "projecting"): InletCoefficients(...),
    ("rectangular", "concrete", "headwall"): InletCoefficients(...),
    ("arch", "concrete", "projecting"): InletCoefficients(...),
}
```

建议同步修改 `CulvertGeometry` / `Culvert`：

```python
@dataclass
class CulvertGeometry:
    shape: Literal["circular", "rectangular", "arch"]
    length: float
    diameter: float | None = None
    width: float | None = None
    height: float | None = None
    invert_elevation_us: float = 0.0
    invert_elevation_ds: float | None = None
    slope: float | None = None
    n_barrels: int = 1


class Culvert:
    def __init__(
        self,
        position: float,
        geometry: CulvertGeometry,
        material: str = "concrete",
        inlet_type: str = "projecting",
        manning_n: float | None = None,
        entrance_loss_coef: float | None = None,
        exit_loss_coef: float = 1.0,
    ):
        ...
```

同时做一个**入口类型统一映射**，避免 `hydromind_data_format.py` 和当前 `culvert.py` 的命名不一致。  
这里要注意：**不要在没有 HDS-5 表项依据时，把 `square_edge`、`projecting`、`headwall` 粗暴合并成同一个入口类型**。

```python
INLET_TYPE_ALIASES = {
    "square_edge": "square_edge",
    "projecting": "projecting",
    "headwall": "headwall_square_edge",
    "groove_end": "groove_end",
    "groove_headwall": "groove_headwall",
    "mitered": "mitered_to_slope",
    "beveled": "beveled",
}
```

### 3.2 补齐精确几何函数：`area(depth)` / `top_width(depth)` / `perimeter(depth)`

没有这一步，就无法可靠求：

- 临界水深 `y_c`
- 正常水深 `y_n`
- 部分充满流的 `A(y)`、`R(y)`

建议把现有：

- `area()` 改成 `full_area()`
- 新增 `area_at_depth(y)`
- 新增 `wetted_perimeter(y)`
- 新增 `top_width(y)`
- 新增 `hydraulic_radius_at_depth(y)`

伪代码：

```python
class CulvertGeometry:
    def rise(self) -> float:
        return self.diameter if self.shape == "circular" else self.height

    def full_area(self) -> float:
        ...

    def area_at_depth(self, y: float) -> float:
        if self.shape == "circular":
            # 精确圆弧面积
            ...
        elif self.shape == "rectangular":
            return self.width * min(max(y, 0.0), self.height)
        elif self.shape == "arch":
            # 不能再用当前的矩形近似，必须实现 arch 的标准几何
            ...

    def top_width(self, y: float) -> float:
        ...

    def wetted_perimeter(self, y: float) -> float:
        ...

    def hydraulic_radius_at_depth(self, y: float) -> float:
        A = self.area_at_depth(y)
        P = self.wetted_perimeter(y)
        return A / P if P > 0 else 0.0
```

### 3.3 进口控制：改为 HDS-5 的“所需上游水头”计算

不要再让 `_inlet_control()` 直接返回“一个简化孔口流量”。  
建议改成：

- `required_headwater_inlet(Q_per_barrel)`：给定单孔流量，返回入口控制所需上游水头
- `solve_discharge_inlet(HW_available)`：给定可用上游水头，反求入口控制可过流量

入口控制更适合按“**headwater requirement**”组织，因为这样才能和出口控制做标准比较。

伪代码：

```python
def _lookup_inlet_coeffs(self) -> InletCoefficients:
    material_props = BARREL_MATERIALS[self.material]
    inlet_key = (self.geom.shape, material_props.inlet_family, self.inlet_type)
    return INLET_COEFF_TABLE[inlet_key]


def _required_headwater_inlet(self, q_per_barrel: float) -> tuple[float, dict]:
    coeffs = self._lookup_inlet_coeffs()
    A = self.geom.full_area()
    D = self.geom.rise()
    q_star = q_per_barrel / (A * (D ** 0.5))

    slope_term = coeffs.slope_coef * self.geom.slope

    # HDS-5 公式形式：
    # HW/D = (q*/K)^(1/M) + Y + slope_term      # 未淹没入口
    # HW/D = c * q*^2 + Y + slope_term          # 淹没入口
    hw_unsub = D * ((q_star / coeffs.K) ** (1.0 / coeffs.M) + coeffs.Y + slope_term)
    hw_sub = D * (coeffs.c * q_star**2 + coeffs.Y + slope_term)

    # 对于给定 Q，谁要求的 HW 更高，谁控制
    if hw_sub >= hw_unsub:
        return hw_sub, {"inlet_branch": "submerged"}
    return hw_unsub, {"inlet_branch": "unsubmerged"}


def _solve_discharge_inlet(self, hw_available: float) -> tuple[float, dict]:
    if hw_available <= 0.0:
        return 0.0, {"inlet_branch": "dry"}

    def residual(q):
        hw_req, _info = self._required_headwater_inlet(q)
        return hw_req - hw_available

    q_upper = self._bracket_q_upper(hw_available)
    q = brentq(residual, 0.0, q_upper)
    hw_req, info = self._required_headwater_inlet(q)
    info["hw_required_inlet"] = hw_req
    return q, info
```

这一步会直接修掉当前三个核心问题：

- 不再用固定 `Cd` 代替 HDS-5
- 不再用 `1.2D + centerline head` 伪装淹没入口
- 不再让入口控制“只返回输入水深”

### 3.4 出口控制：补上 `TW / y_c / y_n / h_o` 逻辑

当前 `_outlet_control()` 最大的问题不是公式形式，而是**缺少出口控制深度判定**。  
标准出口控制至少需要这几步：

1. 给定 `Q` 计算临界水深 `y_c`
2. 必要时计算正常水深 `y_n`
3. 判断 barrel 在出口附近是部分充满还是满流
4. 求自由出流情况下的出口控制深度 `h_o_free`
5. 用 `h_o = max(TW, h_o_free)` 进入能量方程
6. 再把所需 `HW_outlet(Q)` 与入口控制进行比较

伪代码：

```python
def _critical_depth(self, q_per_barrel: float) -> float:
    # 通用临界条件：Q^2 * T(y) / (g * A(y)^3) = 1
    def crit_residual(y):
        A = self.geom.area_at_depth(y)
        T = self.geom.top_width(y)
        return q_per_barrel**2 * T / (self.g * A**3) - 1.0

    return brentq(crit_residual, 1e-6, self.geom.rise())


def _normal_depth(self, q_per_barrel: float) -> float:
    # 通用 Manning 均匀流
    def normal_residual(y):
        A = self.geom.area_at_depth(y)
        R = self.geom.hydraulic_radius_at_depth(y)
        q_calc = (1.0 / self.n) * A * (R ** (2.0 / 3.0)) * (self.geom.slope ** 0.5)
        return q_calc - q_per_barrel

    return brentq(normal_residual, 1e-6, self.geom.rise())


def _free_outlet_control_depth(self, q_per_barrel: float, y_c: float) -> float:
    D = self.geom.rise()

    # HDS-5/HEC-RAS 常用 outlet-control depth 规则
    # 具体边界条件可再按手册细化
    if y_c >= D:
        return D
    return 0.5 * (y_c + D)


def _required_headwater_outlet(self, q_per_barrel: float, tw_depth: float) -> tuple[float, dict]:
    D = self.geom.rise()
    y_c = self._critical_depth(q_per_barrel)
    y_n = self._normal_depth(q_per_barrel) if self.geom.slope > 0 else D

    outlet_submerged = tw_depth >= D
    barrel_full = max(tw_depth, y_n, y_c) >= D
    flow_depth = D if barrel_full else max(y_c, y_n)

    A = self.geom.area_at_depth(flow_depth)
    R = self.geom.hydraulic_radius_at_depth(flow_depth)
    V = q_per_barrel / A

    h_e = self.K_e * V**2 / (2.0 * self.g)
    h_f = (self.n**2 * self.geom.length * V**2) / (R ** (4.0 / 3.0))
    h_x = self.K_exit * V**2 / (2.0 * self.g)

    h_o_free = self._free_outlet_control_depth(q_per_barrel, y_c)
    h_o = max(tw_depth, h_o_free)

    # 上游水头相对进口底板
    hw_required = h_o + h_e + h_f + h_x - self.geom.slope * self.geom.length

    return hw_required, {
        "critical_depth": y_c,
        "normal_depth": y_n,
        "barrel_full": barrel_full,
        "outlet_submerged": outlet_submerged,
        "hw_required_outlet": hw_required,
    }


def _solve_discharge_outlet(self, hw_available: float, tw_depth: float) -> tuple[float, dict]:
    if hw_available <= 0.0:
        return 0.0, {"barrel_full": False}

    def residual(q):
        hw_req, _info = self._required_headwater_outlet(q, tw_depth)
        return hw_req - hw_available

    q_upper = self._bracket_q_upper(hw_available)
    q = brentq(residual, 0.0, q_upper)
    hw_req, info = self._required_headwater_outlet(q, tw_depth)
    info["hw_required_outlet"] = hw_req
    return q, info
```

### 3.5 正确的控制判定：比较同一个 `HW_available` 下的 `Q_inlet` 与 `Q_outlet`

这一段是最终核心。

伪代码：

```python
def compute_discharge(
    self,
    h_upstream: float,
    h_downstream: float,
    approach_velocity_head: float = 0.0,
) -> tuple[float, str, dict]:
    # 输入仍可保持“相对进口/出口底板的水深”
    hw_available = max(0.0, h_upstream + approach_velocity_head)
    tw_depth = max(0.0, h_downstream)

    q_inlet_pb, inlet_info = self._solve_discharge_inlet(hw_available)
    q_outlet_pb, outlet_info = self._solve_discharge_outlet(hw_available, tw_depth)

    if q_inlet_pb <= q_outlet_pb:
        q_pb = q_inlet_pb
        control = "inlet"
    else:
        q_pb = q_outlet_pb
        control = "outlet"

    q_total = q_pb * self.geom.n_barrels

    diagnostics = {
        "Q_per_barrel": q_pb,
        "Q_total": q_total,
        "control_type": control,
        **inlet_info,
        **outlet_info,
    }
    return q_total, control, diagnostics
```

这才是 HDS-5/HEC-RAS 里“进口控制 / 出口控制自动判定”的正确组织方式。

### 3.6 淹没修正的实现原则：不要套堰流的统一折减因子

如果只想快速修“淹没修正”，最容易走错的一步就是直接写一个：

```python
Q *= submergence_factor
```

这对堰流有时可以近似，但对涵洞**不是标准做法**。  
对涵洞，正确实现是：

- **入口淹没**：切换到 HDS-5 的 submerged inlet equation
- **出口淹没**：在 outlet control 中用 `TW` 控制 `h_o`
- **部分充满 / 满流过渡**：依赖 `y_c`、`y_n`、`h_o_free`

所以“淹没修正”应当拆成三段逻辑，而不是一个统一乘子。

### 3.7 `validate_culvert_design()` 也要改成“反算所需壅水深”

当前校核函数更像“给定允许上游水深，看看能过多少流量”。  
标准设计里更常用的是反过来：

- 给定 `Q_design`
- 给定 `TW`
- 反算 `HW_required`
- 再与允许 `HW_max` 比较

建议新增：

```python
def compute_required_headwater(self, q_design: float, tw_depth: float) -> dict:
    q_pb = q_design / self.geom.n_barrels
    hw_inlet, inlet_info = self._required_headwater_inlet(q_pb)
    hw_outlet, outlet_info = self._required_headwater_outlet(q_pb, tw_depth)

    if hw_inlet >= hw_outlet:
        return {"HW_required": hw_inlet, "control_type": "inlet", **inlet_info}
    return {"HW_required": hw_outlet, "control_type": "outlet", **outlet_info}
```

然后 `validate_culvert_design()` 改成：

```python
def validate_culvert_design(self, q_design, hw_max, tw_depth):
    result = self.compute_required_headwater(q_design, tw_depth)
    passes = result["HW_required"] <= hw_max
    return {**result, "passes": passes}
```

### 3.8 建议的最小测试矩阵

仅改代码还不够，测试也必须改成“标准行为测试”。

建议至少补这些测试：

- 同一几何、同一 `HW/TW` 下：
  - `concrete` 与 `corrugated_metal` 的流量应不同
  - `projecting` 与 `headwall` 与 `beveled` 的流量应不同
- 同一 `Q` 下：
  - 入口控制所需 `HW` 应随更差入口形式增大
  - 出口控制所需 `HW` 应随更大 `n`、更长 `L` 增大
- `TW < h_o_free` 与 `TW > h_o_free` 两组案例：
  - 前者应是自由出流控制
  - 后者应体现尾水淹没
- 低尾水 + 陡坡 + 长度较长案例：
  - 必须验证 `y_c` / `y_n` / `barrel_full` 判定
- 双孔 / 三孔案例：
  - 总流量应随 `n_barrels` 近似线性增加
- 反算设计案例：
  - 给定 `Q_design` 时 `HW_required` 应能稳定收敛

---

## 推荐实施顺序

如果只允许分 3 个迭代完成，建议这样排：

### 第 1 阶段：先做到 HDS-5 最小合规

- 新增 `material`
- 新增 `n_barrels`
- 建立 `INLET_COEFF_TABLE`
- 重写 `_inlet_control()` 为“给定 Q 求 `HW_required`”
- 新增 `compute_required_headwater()`

### 第 2 阶段：补齐出口控制与淹没逻辑

- 新增 `area_at_depth()` / `top_width()` / `wetted_perimeter()`
- 新增 `critical_depth()` / `normal_depth()`
- 重写 `_outlet_control()` 为“给定 Q 求 `HW_required`”
- 用 `Q_inlet` vs `Q_outlet` 正式判定控制类型

### 第 3 阶段：向 HEC-RAS 行为靠拢

- 统一入口类型命名
- 完善 arch / box / pipe-arch 几何
- 增加 approach velocity head
- 增加多 opening / crossing 级别接口
- 增加对标 HEC-RAS 算例回归测试

---

## 最终判断

当前 `physics/structures/culvert.py` 的主要问题不是“某个系数取值不精确”，而是**求解框架本身还没有切换到 HDS-5 的组织方式**。  

真正要修到对标 HEC-RAS / FHWA HDS-5，必须完成下面三个结构性改造：

1. **把入口控制改成 HDS-5 的系数表驱动模型**
2. **把出口控制改成 `TW + y_c/y_n + h_o` 的标准能量方程模型**
3. **把控制判定改成“同一条件下比较两种控制能力/所需水头”**

这三步完成后，再补材质系数、几何精确函数和多孔支持，模块才算真正进入“标准级涵洞模型”的范围。
