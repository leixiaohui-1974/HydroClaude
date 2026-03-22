"""测试涵洞位置映射：WSE 跳变检测法的正确性。

验证 _build_from_ref 使用 WSE 跳变法确定 us_xs_index，
以及 Ex3 Single Culvert 5yr 工况 MAE < 0.15m。
"""
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from hydroclaude_cli import _build_from_ref, _run_profile


EX3_PATH = ROOT / "reports/hecras_reference_data/example_3__single_culvert_TWINPIPE.p01.json"
EX4_PATH = ROOT / "reports/hecras_reference_data/example_4__multiple_culverts_MULTCULV.p01.json"


@pytest.fixture
def ex3_ref():
    """加载 Ex3 参考数据（单涵洞）。"""
    with EX3_PATH.open(encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def ex4_ref():
    """加载 Ex4 参考数据（多涵洞）。"""
    with EX4_PATH.open(encoding="utf-8") as f:
        return json.load(f)


class TestCulvertPositionMapping:
    """涵洞位置映射单元测试。"""

    def test_ex3_culvert_us_xs_index_via_wse_jump(self, ex3_ref):
        """Ex3 单涵洞：WSE 跳变检测应选中 XS4（涵洞上游断面）。

        Profile 0 WSE: XS4->XS5 有最大正向跳变 (~0.177m)，
        因此 us_xs_index 应为 4，而非之前错误的 3。
        """
        data = _build_from_ref(ex3_ref)
        culverts_param = data[12]  # culverts_param 是第 13 个返回值（索引 12）
        assert len(culverts_param) == 1, "Ex3 应有 1 个涵洞"
        assert culverts_param[0]["us_xs_index"] == 4, (
            f"涵洞上游断面应为 XS4（WSE 最大跳变位置），实际: {culverts_param[0]['us_xs_index']}"
        )

    def test_ex3_5yr_mae_below_threshold(self, ex3_ref):
        """Ex3 5yr 工况：MAE 应小于 0.15m。"""
        data = _build_from_ref(ex3_ref)
        _, _, errs, Q, name = _run_profile(ex3_ref, 0, *data)
        mae = float(np.mean(errs))
        assert mae < 0.15, f"Ex3 5yr MAE={mae:.4f}m 超过 0.15m 阈值（工况: {name}, Q={Q:.2f}）"

    def test_ex3_10yr_mae_below_threshold(self, ex3_ref):
        """Ex3 10yr 工况：MAE 应小于 0.15m。"""
        data = _build_from_ref(ex3_ref)
        _, _, errs, Q, name = _run_profile(ex3_ref, 1, *data)
        mae = float(np.mean(errs))
        assert mae < 0.15, f"Ex3 10yr MAE={mae:.4f}m 超过 0.15m 阈值（工况: {name}, Q={Q:.2f}）"

    def test_ex3_culvert_parameters_preserved(self, ex3_ref):
        """Ex3 涵洞参数应正确保留（尺寸、Manning n、桶数等）。"""
        data = _build_from_ref(ex3_ref)
        cv = data[12][0]
        raw_cv = ex3_ref["culverts"][0]

        assert cv["n_barrels"] == raw_cv["n_barrels"], "孔数不匹配"
        assert abs(cv["diameter_m"] - raw_cv["diameter_m"]) < 1e-6, "管径不匹配"
        assert abs(cv["us_invert_m"] - raw_cv["us_invert_m"]) < 1e-6, "上游底板高程不匹配"
        assert abs(cv["ds_invert_m"] - raw_cv["ds_invert_m"]) < 1e-6, "下游底板高程不匹配"
        assert abs(cv["manning_n"] - raw_cv["manning_n"]) < 1e-6, "Manning n 不匹配"


class TestCulvertMultiple:
    """多涵洞位置映射测试。"""

    def test_ex4_culverts_all_indexed(self, ex4_ref):
        """Ex4 多涵洞：每个涵洞都应有有效的 us_xs_index（在断面范围内）。"""
        data = _build_from_ref(ex4_ref)
        culverts_param = data[12]
        n_xs = data[-1]

        for i, cv in enumerate(culverts_param):
            idx = cv["us_xs_index"]
            assert 0 <= idx < n_xs, (
                f"涵洞{i} us_xs_index={idx} 超出有效范围 [0, {n_xs})"
            )

    def test_ex4_parallel_culverts_share_position(self, ex4_ref):
        """Ex4 两个涵洞属于同一断面位置（上层箱涵+下层圆管并联）。

        HEC-RAS Example 4 的两个涵洞在同一 RS=20.237 处叠置，
        因此 us_xs_index 相同是正确的并联处理。
        """
        data = _build_from_ref(ex4_ref)
        culverts_param = data[12]
        assert len(culverts_param) == 2, "Ex4 应有 2 个涵洞"
        # 两个涵洞在同一位置（并联）
        assert culverts_param[0]["us_xs_index"] == culverts_param[1]["us_xs_index"], (
            "Ex4 两个并联涵洞应共享同一 us_xs_index，"
            f"实际: {culverts_param[0]['us_xs_index']} 和 {culverts_param[1]['us_xs_index']}"
        )

    def test_ex4_5yr_mae_below_threshold(self, ex4_ref):
        """Ex4 5yr 工况：MAE 应小于 0.15m。"""
        data = _build_from_ref(ex4_ref)
        _, _, errs, Q, name = _run_profile(ex4_ref, 0, *data)
        mae = float(np.mean(errs))
        assert mae < 0.15, f"Ex4 5yr MAE={mae:.4f}m 超过 0.15m 阈值"


class TestWseJumpFallback:
    """WSE 跳变检测回退逻辑测试。"""

    def test_no_wse_jump_falls_back_to_bed_match(self):
        """当 profile 0 不存在时，应回退到床面高程匹配法。"""
        dummy_ref = {
            "n_cross_sections": 5,
            "geometry": {
                "cross_sections": [
                    {
                        "station_elevation": [[0, 10.0], [10, 9.0], [20, 10.0]],
                        "manning_n": [[5.0, 0.04]],
                        "left_bank_ft": 16.4,
                        "right_bank_ft": 49.2,
                        "len_channel_ft": 100.0,
                        "contraction": 0.1,
                        "expansion": 0.3,
                    }
                ] * 5,
            },
            "profiles": [],  # 无 profile 数据 -> 回退到 bed elevation 匹配
            "culverts": [
                {
                    "rs": "50",
                    "shape": "circular",
                    "diameter_m": 1.0,
                    "height_m": 1.0,
                    "width_m": 1.0,
                    "length_m": 10.0,
                    "us_invert_m": 9.0 / 3.281,
                    "ds_invert_m": 8.9 / 3.281,
                    "n_barrels": 1,
                    "manning_n": 0.013,
                    "entrance_loss_coef": 0.5,
                }
            ],
            "ineffective_areas": [],
        }
        # 不应抛出异常
        data = _build_from_ref(dummy_ref)
        culverts_param = data[12]
        assert len(culverts_param) == 1
        n_xs = data[-1]
        assert 0 <= culverts_param[0]["us_xs_index"] < n_xs

    def test_inlet_coeff_si_units(self):
        """涵洞入口控制系数应使用 HDS-5 SI 单位值（K<0.1），而非英制值（K>1）。"""
        import sys
        sys.path.insert(0, str(ROOT))
        from physics.structures.culvert import Culvert, CulvertGeometry

        geom = CulvertGeometry(
            shape="circular", length=15.0, slope=0.002,
            diameter=1.5, invert_elevation=5.0, n_barrels=1
        )
        culvert = Culvert(position=0.0, geometry=geom, manning_n=0.013, entrance_loss_coef=0.5)
        coeffs = culvert._lookup_inlet_coeffs()

        # HDS-5 SI 系数：K 应远小于 1（如 0.0078），而非英制的 K~1.5
        assert coeffs["K"] < 0.1, (
            f"入口控制系数 K={coeffs['K']:.4f} 疑似为英制值（应 < 0.1 的 SI 值），"
            "这会导致入口控制水头严重高估。"
        )
