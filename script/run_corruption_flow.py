from __future__ import annotations

import sys
from pathlib import Path

# Add src/ to path so modules resolve without installing the package
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pipelines.corruption_flow import main

if __name__ == "__main__":
    main()
