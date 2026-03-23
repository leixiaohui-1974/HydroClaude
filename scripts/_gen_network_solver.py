import pathlib
lines = ['"""非恒定流河网求解器 — 多 Reach + Junction 松弛迭代。"""', '', 'import numpy as np', 'from dataclasses import dataclass, field', 'import sys', 'import os', '', 'sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))', '', 'from solvers.unsteady_preissmann_solver import PreissmannSolver, UnsteadyReachData, UnsteadyState']
pathlib.Path('Z:/research/hydroclaude/solvers/unsteady_network_solver.py').write_text(chr(10).join(lines), encoding='utf-8')
print("partial ok")