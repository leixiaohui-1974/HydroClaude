import pathlib
code=open("Z:/research/hydroclaude/_nsolver_code.txt",encoding="utf-8").read()
pathlib.Path("Z:/research/hydroclaude/solvers/network_steady_solver.py").write_text(code,encoding="utf-8")
print("done")
