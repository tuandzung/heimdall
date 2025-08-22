from __future__ import annotations

import uuid

from enum import Enum

from fastapi_users import schemas
from pydantic import BaseModel


class FlinkJobType(str, Enum):
    APPLICATION = "APPLICATION"
    SESSION = "SESSION"


class FlinkJobResources(BaseModel):
    replicas: int
    cpu: str
    mem: str


class FlinkJob(BaseModel):
    id: str
    name: str
    status: str
    type: FlinkJobType
    startTime: int | None | None = None
    shortImage: str
    flinkVersion: str
    parallelism: int
    resources: dict[str, FlinkJobResources]
    metadata: dict[str, str]


class UserRead(schemas.BaseUser[uuid.UUID]):
    pass


class UserCreate(schemas.BaseUserCreate):
    pass


class UserUpdate(schemas.BaseUserUpdate):
    pass
