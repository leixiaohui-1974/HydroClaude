
import pathlib

lines = [
    'from __future__ import annotations',
]
pathlib.Path("Z:/research/hydroclaude/_lines.txt").write_text(
    chr(10).join(lines), encoding="utf-8"
)
print("bootstrap ok")
