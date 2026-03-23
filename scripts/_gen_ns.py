import pathlib
content='"""非恒定流河网求解器 — 多 Reach + Junction 松弛迭代。"""\n\nimport numpy as np\nfrom dataclasses import dataclass, field\nimport sys\nimport os\n\nsys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))\n\nfrom solvers.unsteady_preissmann_solver import PreissmannSolver, UnsteadyReachData, UnsteadyState\n\n\n'
pathlib.Path(r'Z:/research/hydroclaude/solvers/unsteady_network_solver.py').write_text(content,encoding='utf-8')
print(len(content))