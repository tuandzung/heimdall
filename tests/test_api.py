from __future__ import annotations

import asyncio

from typing import List

import pytest

from fastapi.testclient import TestClient

from heimdall.api import app, get_job_locator
from heimdall.models import FlinkJob, FlinkJobResources, FlinkJobType
from heimdall.service import FlinkJobLocator


class FakeLocator(FlinkJobLocator):
    def __init__(self, jobs: List[FlinkJob]) -> None:
        self._jobs = jobs

    async def find_all(self) -> List[FlinkJob]:
        await asyncio.sleep(0)  # ensure it's truly async
        return self._jobs


@pytest.fixture(autouse=True)
def override_locator():
    jobs = [
        FlinkJob(
            id="uid-1",
            name="demo-app",
            status="RUNNING",
            type=FlinkJobType.APPLICATION,
            startTime=1723940000,
            shortImage="flink:1.18",
            flinkVersion="1.18",
            parallelism=2,
            resources={
                "jm": FlinkJobResources(replicas=1, cpu="0.5", mem="1024m"),
                "tm": FlinkJobResources(replicas=1, cpu="0.5", mem="1024m"),
            },
            metadata={"app": "flink"},
        )
    ]

    def _provider() -> FlinkJobLocator:
        return FakeLocator(jobs)

    app.dependency_overrides[get_job_locator] = _provider
    yield
    app.dependency_overrides.clear()


def test_healthz():
    client = TestClient(app)
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_config():
    client = TestClient(app)
    resp = client.get("/config")
    assert resp.status_code == 200
    data = resp.json()
    assert "appVersion" in data
    assert "patterns" in data
    assert "endpointPathPatterns" in data


def test_jobs():
    client = TestClient(app)
    resp = client.get("/jobs")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 1
    job = data[0]
    assert job["name"] == "demo-app"
    assert job["type"] == "APPLICATION"
