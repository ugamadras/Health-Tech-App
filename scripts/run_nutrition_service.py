#!/usr/bin/env python3
"""Launch the nutrition service with the correct project import paths."""

from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "nutrition-service" / "src"))
sys.path.insert(0, str(ROOT))


def main() -> None:
    try:
        import uvicorn
    except ImportError as error:  # pragma: no cover
        raise SystemExit(
            "uvicorn is not installed. Run `python3 -m pip install -r services/nutrition-service/requirements.txt` first."
        ) from error

    os.environ.setdefault("PYTHONPATH", str(ROOT))
    host = os.environ.get("NUTRITION_SERVICE_HOST", "127.0.0.1")
    port = int(os.environ.get("NUTRITION_SERVICE_PORT", "8001"))
    uvicorn.run("nutrition_service.api:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
