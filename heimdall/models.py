from __future__ import annotations

from enum import Enum

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
