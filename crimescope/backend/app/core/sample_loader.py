import json
from pathlib import Path
from typing import Any

_SAMPLES_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data_samples"


def load_sample(filename: str) -> dict[str, Any]:
    path = _SAMPLES_DIR / filename
    with open(path) as f:
        return json.load(f)
