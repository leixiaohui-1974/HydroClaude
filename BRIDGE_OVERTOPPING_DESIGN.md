# Bridge Overtopping Weir Flow 最小化修改方案

基于当前 `solvers/steady_profile_solver.py`（你给出的版本行号）设计，目标是在**尽量少改动**现有结构的前提下补齐桥面板溢顶分流能力：

1. 检测 `WSE > deck_elev`  
2. 计算堰流量 `Q_weir`  
3. 分流 `Q_under = Q - Q_weir`  
4. 用 `Q_under` 计算桥孔（under-bridge opening）水力学

---

## 现状问题（针对两个方法）

- `_solve_bridge_momentum` 目前通过“扣减过水面积”近似壅水，但没有真正把总流量拆分成 `Q_weir` 与 `Q_under`。
- `_solve_bridge_energy` 同样缺少显式分流，导致桥孔速度头、摩阻损失、局部损失都仍按总流量 `Q` 计算。
- 两处对 deck 的触发判据有 EGL 逻辑（`EGL > deck_elev`），与你要求的 `WSE > deck_elev` 不一致。

---

## 修改点 A：新增通用分流辅助函数

### A1) 插入位置

- 在 `L426`（`def _solve_bridge_momentum` 之前）插入新方法。

### A2) 新增代码片段

```python
    def _split_deck_overtopping_flow(
        self,
        Q_total: float,
        WSE: float,
        deck_elev: float,
        weir_len: float,
        weir_coef: float,
    ) -> Tuple[float, float]:
        """Return (Q_weir, Q_under) for deck overtopping."""
        if (
            Q_total <= 0.0
            or weir_len <= 0.0
            or deck_elev >= 1e8
            or WSE <= deck_elev
        ):
            return 0.0, float(max(Q_total, 0.0))

        H = max(float(WSE) - float(deck_elev), 0.0)
        Q_weir = float(weir_coef) * float(weir_len) * H ** 1.5
        Q_weir = float(np.clip(Q_weir, 0.0, max(float(Q_total), 0.0)))
        Q_under = float(Q_total - Q_weir)
        return Q_weir, Q_under
```

### A3) 参数约定（无需改数据结构）

- `bridge["deck_weir_coef"]`：可选，默认 `1.70`（SI 下宽顶堰常用量级，单位一致时可直接用）。
- `bridge["deck_weir_length_m"]`：可选；若缺省则用 `min(T2, T3)` 作为有效堰长。

---

## 修改点 B：`_solve_bridge_momentum`（L426-L539）

### B1) 新增堰流参数读取（插入在 L463-L465 之后）

```python
        deck_weir_coef = float(bridge.get("deck_weir_coef", 1.70))
        deck_weir_len_cfg = float(bridge.get("deck_weir_length_m", 0.0))
```

### B2) 触发判据从 EGL 改为 WSE（替换 L476-L480）

```python
        if W_downstream > deck_elev > bed_ds:
            A2_eff = max(A2_eff - (W_downstream - deck_elev) * T2, A2 * 0.1)
```

> 说明：这里仍保留“面积扣减”逻辑，只把触发条件统一到 `WSE > deck_elev`，属于最小侵入改动。

### B3) 上游断面同样改为 WSE 判据（替换 L494-L499）

```python
            if W3_trial > deck_elev > bed_us:
                A3_eff = max(A3_eff - (W3_trial - deck_elev) * T3, A3 * 0.1)
```

### B4) 在迭代内加入分流，并统一改用 `Q_under`（插入在上段之后）

```python
            weir_len = (
                deck_weir_len_cfg
                if deck_weir_len_cfg > 0.0
                else max(min(T2, T3), 1e-6)
            )
            Q_weir, Q_under = self._split_deck_overtopping_flow(
                Q_total=Q,
                WSE=W3_trial,
                deck_elev=deck_elev,
                weir_len=weir_len,
                weir_coef=deck_weir_coef,
            )
```

### B5) 将桥孔水力学中用到 `Q` 的位置替换为 `Q_under`

- `L499`：`V3 = Q / ...` -> `V3 = Q_under / ...`
- `L481` 的 `V2` 建议挪到循环内并改为 `V2 = Q_under / max(A2_eff, 1e-9)`（与每次迭代分流一致）
- `L505`：`V_avg = Q / ...` -> `V_avg = Q_under / ...`
- `L506`：`Sf_avg = min((Q * n_br / ...)**2, 1.0)` -> `Sf_avg = min((Q_under * n_br / ...)**2, 1.0)`
- `L513`：`beta2*rho*Q*V2` -> `beta2*rho*Q_under*V2`
- `L514`：`beta3*rho*Q*V3` -> `beta3*rho*Q_under*V3`

### B6) 导数段也要同步分流（替换 L519-L531）

```python
            dW = 1e-3
            W3p = W3_trial + dW
            h3p = max(W3p - bed_us, 0.01)
            A3p, _P3pw, _R3p, T3p = self._get_geometry(h3p, us_xs_index)
            A_pier3p = pier_w_total * min(h3p, pier_height)
            A3p_eff = max(A3p - A_pier3p, A3p * 0.3)
            if W3p > deck_elev > bed_us:
                A3p_eff = max(A3p_eff - (W3p - deck_elev) * T3p, A3p * 0.1)

            weir_len_p = (
                deck_weir_len_cfg
                if deck_weir_len_cfg > 0.0
                else max(min(T2, T3p), 1e-6)
            )
            _Q_weir_p, Q_under_p = self._split_deck_overtopping_flow(
                Q_total=Q,
                WSE=W3p,
                deck_elev=deck_elev,
                weir_len=weir_len_p,
                weir_coef=deck_weir_coef,
            )

            V2p = Q_under_p / max(A2_eff, 1e-9)
            V3p = Q_under_p / max(A3p_eff, 1e-9)
            P3p_force = self._hydrostatic_pressure_force(h3p, us_xs_index)

            A_avgp = 0.5 * (A2_eff + A3p_eff)
            P_wet_avgp = 0.5 * (P2_wet + _P3pw)
            R_avgp = A_avgp / max(P_wet_avgp, 1e-6)
            V_avgp = Q_under_p / max(A_avgp, 1e-9)
            Sf_avgp = min((Q_under_p * n_br / max(A_avgp * R_avgp ** (2.0 / 3.0), 1e-9)) ** 2, 1.0)

            F_fp = gamma * A_avgp * Sf_avgp * L_bridge
            A_pier_avgp = 0.5 * (A_pier2 + A_pier3p)
            F_pierp = 0.5 * rho * C_D * A_pier_avgp * V_avgp ** 2
            W_xp = gamma * A_avgp * S0_bridge * L_bridge

            momentum_rhs_p = beta2 * rho * Q_under_p * V2p + P2_force + F_fp + F_pierp + W_xp
            imbalance_p = (beta3 * rho * Q_under_p * V3p + P3p_force) - momentum_rhs_p
            d_imb_dW = (imbalance_p - imbalance) / dW
```

---

## 修改点 C：`_solve_bridge_energy`（L541-L683）

### C1) 新增堰流参数读取（插入在 L573 之后）

```python
        deck_weir_coef = float(bridge.get("deck_weir_coef", 1.70))
        deck_weir_len_cfg = float(bridge.get("deck_weir_length_m", 0.0))
```

### C2) `_eff_area` 中触发判据改为 WSE（替换 L608-L619）

```python
                # 桥面板压顶面积扣减（使用 WSE 判据）
                A_deck = 0.0
                if W_trial > deck_elev > bed_elev:
                    A_deck = (W_trial - deck_elev) * T
                A_open = max(A - A_pier - A_deck, A * 0.3)
                P_open = P_wet
```

### C3) Section 2 仅保留几何量，`V2/E2` 放到迭代内按 `Q_under` 计算

- 保留 `L625` 的 `A2_eff, P2_wet, alpha2 = _eff_area(...)`
- 删除/替换 `L626-L627`，改为在循环内实时计算：

```python
            h3_now = max(W3_trial - bed_us, 0.01)
            _A3_raw, _P3_raw, _R3_raw, T3_now = self._get_geometry(h3_now, us_xs_index)
            h2_now = max(W_downstream - bed_ds, 0.01)
            _A2_raw, _P2_raw, _R2_raw, T2_now = self._get_geometry(h2_now, ds_xs_index)

            weir_len = (
                deck_weir_len_cfg
                if deck_weir_len_cfg > 0.0
                else max(min(T2_now, T3_now), 1e-6)
            )
            Q_weir, Q_under = self._split_deck_overtopping_flow(
                Q_total=Q,
                WSE=W3_trial,
                deck_elev=deck_elev,
                weir_len=weir_len,
                weir_coef=deck_weir_coef,
            )

            V2 = Q_under / max(A2_eff, 1e-9)
            E2 = W_downstream + alpha2 * V2 ** 2 / (2.0 * self.g)
```

### C4) 循环内所有桥孔水力学用 `Q_under`

- `L636`：`V3 = Q / ...` -> `V3 = Q_under / ...`
- `L643`：`Sf_avg = min((Q * n_br / ...)**2, 1.0)` -> `Sf_avg = min((Q_under * n_br / ...)**2, 1.0)`

### C5) 导数段同步使用 `Q_under_p`（替换 L660-L671）

```python
            dW = 1e-3
            W3p = W3_trial + dW
            A3p, P3p, alpha3p = _eff_area(W3p, us_xs_index, bed_us)
            h3p = max(W3p - bed_us, 0.01)
            _A3p_raw, _P3p_raw, _R3p_raw, T3p = self._get_geometry(h3p, us_xs_index)
            h2p = max(W_downstream - bed_ds, 0.01)
            _A2p_raw, _P2p_raw, _R2p_raw, T2p = self._get_geometry(h2p, ds_xs_index)

            weir_len_p = (
                deck_weir_len_cfg
                if deck_weir_len_cfg > 0.0
                else max(min(T2p, T3p), 1e-6)
            )
            _Q_weir_p, Q_under_p = self._split_deck_overtopping_flow(
                Q_total=Q,
                WSE=W3p,
                deck_elev=deck_elev,
                weir_len=weir_len_p,
                weir_coef=deck_weir_coef,
            )

            V2p = Q_under_p / max(A2_eff, 1e-9)
            E2p = W_downstream + alpha2 * V2p ** 2 / (2.0 * self.g)
            V3p = Q_under_p / max(A3p, 1e-9)
            vh3p = alpha3p * V3p ** 2 / (2.0 * self.g)
            A_avgp = 0.5 * (A2_eff + A3p)
            P_avgp = 0.5 * (P2_wet + P3p)
            R_avgp = A_avgp / max(P_avgp, 1e-6)
            Sf_avgp = min((Q_under_p * n_br / max(A_avgp * R_avgp ** (2.0 / 3.0), 1e-9)) ** 2, 1.0)
            h_fp = L_bridge * Sf_avgp
            h_pierp = pier_k * vh3p
            h_contrp = cc * max(vh3p - alpha2 * V2p ** 2 / (2.0 * self.g), 0.0)
            f_valp = E2p - (W3p + vh3p + h_fp + h_pierp + h_contrp)
```

---

## 最小改动原则说明

- 不改现有方法签名，不改主调流程（`_solve_standard_step_variable_xs` 的桥梁调用保持原样）。
- 只新增 1 个类内辅助方法，并在两个桥梁求解器中局部替换 `Q` 为 `Q_under`。
- 保留原先的“桥面板面积扣减”框架，仅将触发条件统一为 `WSE > deck_elev`，避免大范围重构。

---

## 建议的快速校核（改完后）

1. `WSE <= deck_elev`：应得到 `Q_weir = 0`，结果与现有基本一致。  
2. `WSE > deck_elev` 小超高：`Q_weir > 0`，且桥孔速度/损失相对现状下降。  
3. 大超高：`Q_weir` 被 `Q` 上限截断，`Q_under` 不会负值。  
4. 对比 `tests/test_bridge_momentum.py`（若含桥例）确保无回归崩溃。  

---

## 备注

- 以上行号基于当前文件快照（`_solve_bridge_momentum` 起始于 `L426`，`_solve_bridge_energy` 起始于 `L541`）。若你先做了其它改动，请按“代码块语义位置”应用。
