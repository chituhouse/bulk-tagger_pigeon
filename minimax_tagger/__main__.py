"""MiniMax Tagger 包的主入口点。

使用方式:
    python -m minimax_tagger --help
    python -m minimax_tagger manifest.csv --prompt "反推英文提示词..."
"""
from __future__ import annotations

from .cli import main

if __name__ == "__main__":
    main() 