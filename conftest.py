"""HydroClaude pytest 配置：自动将关联仓库路径加入 sys.path。"""
import sys
import os

# 关联仓库路径（与 HydroClaude 同级目录）
_base = os.path.dirname(os.path.abspath(__file__))
_repos = [
    os.path.join(_base, '..', 'pipedream-hydrology-integration-lab'),
    os.path.join(_base, '..', 'HydroClaw'),   # HydroMind（已更名，本地目录保留旧名）
    os.path.join(_base, '..', 'HydroMind'),   # 如果已重命名
]
for p in _repos:
    p = os.path.normpath(p)
    if os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)
