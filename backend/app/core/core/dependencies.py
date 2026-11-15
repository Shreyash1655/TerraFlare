from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.core.config import settings
from app.utils.data_repository import DataRepository


@lru_cache
def get_repository() -> DataRepository:
    return DataRepository(settings.data_dir, settings.data_mode, settings.data_version)


RepoDep = Annotated[DataRepository, Depends(get_repository)]