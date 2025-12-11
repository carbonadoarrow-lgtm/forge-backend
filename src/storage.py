import json
from pathlib import Path
from typing import List, Type, TypeVar

from .config import settings
from . import schemas

T = TypeVar("T", bound=schemas.BaseModel)


DATA_DIR = Path(settings.data_dir)


def load_list(model: Type[T], filename: str) -> List[T]:
    """Load a list of objects from a JSON file."""
    path = DATA_DIR / filename
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    return [model.model_validate(item) for item in raw]


def save_list(items: List[schemas.BaseModel], filename: str) -> None:
    """Save a list of objects to a JSON file."""
    path = DATA_DIR / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump([item.model_dump() for item in items], f, indent=2)


def load_single(model: Type[T], filename: str) -> T:
    """Load a single object from a JSON file."""
    path = DATA_DIR / filename
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    return model.model_validate(raw)


def save_single(item: schemas.BaseModel, filename: str) -> None:
    """Save a single object to a JSON file."""
    path = DATA_DIR / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(item.model_dump(), f, indent=2)
