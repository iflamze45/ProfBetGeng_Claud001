from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any

try:
    from pydantic import BaseModel
except ImportError:  # pragma: no cover - pydantic is a project dependency
    BaseModel = None


def to_json_safe(value: Any) -> Any:
    """Recursively convert common Python objects into JSON-safe values."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, Enum):
        return to_json_safe(value.value)

    if isinstance(value, Path):
        return str(value)

    if BaseModel is not None and isinstance(value, BaseModel):
        return to_json_safe(value.model_dump())

    if isinstance(value, dict):
        return {str(to_json_safe(key)): to_json_safe(item) for key, item in value.items()}

    if isinstance(value, (list, tuple, set, frozenset)):
        return [to_json_safe(item) for item in value]

    return str(value)
