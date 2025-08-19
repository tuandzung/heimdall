from __future__ import annotations

import logging

from typing import TYPE_CHECKING

from .kubernetes_client import FlinkDeploymentClient
from .models import FlinkJob, FlinkJobResources, FlinkJobType

if TYPE_CHECKING:
    from .config import AppConfig

TM_NUMBER_OF_TASK_SLOTS = "taskmanager.numberOfTaskSlots"
UNKNOWN_STATUS = "UNKNOWN"
JM_LABEL = "jm"
TM_LABEL = "tm"


class FlinkJobLocator:
    async def find_all(self) -> list[FlinkJob]:
        raise NotImplementedError


class K8sOperatorFlinkJobLocator(FlinkJobLocator):
    def __init__(self, app_config: AppConfig, k8s_client: FlinkDeploymentClient | None = None) -> None:
        self.app_config = app_config
        self.k8s_client = k8s_client or FlinkDeploymentClient()
        self._logger = logging.getLogger(__name__)

    async def find_all(self) -> list[FlinkJob]:
        namespace = self.app_config.joblocator.k8s_operator.namespace_to_watch
        try:
            label_selector = self.app_config.joblocator.k8s_operator.label_selector
            deployments = await self.k8s_client.find(namespace, label_selector=label_selector)
            jobs: list[FlinkJob] = [self._to_flink_job(item) for item in deployments]
            if self.app_config.debug:
                self._logger.info("Found %d FlinkDeployment(s) in namespace '%s'", len(deployments), namespace)
            return jobs
        except Exception:
            self._logger.exception("Error listing FlinkDeployments in namespace '%s'", namespace)
            raise

    def _to_flink_job(self, deployment: dict) -> FlinkJob:
        spec = deployment.get("spec", {})
        status = deployment.get("status", {})
        metadata = deployment.get("metadata", {})

        job_type = self._get_job_type(spec)

        jm_spec = spec.get("jobManager", {})
        tm_spec = spec.get("taskManager", {})

        tm_replicas = tm_spec.get("replicas") or 0
        if tm_replicas == 0 and job_type == FlinkJobType.APPLICATION:
            tm_replicas = (((status or {}).get("taskManager") or {}).get("replicas")) or 0

        job_status = ((status or {}).get("jobStatus") or {}).get("state")
        if job_status is None:
            # Some operator versions use status.state instead of status.jobStatus.state
            job_status = status.get("state")

        start_time = ((status or {}).get("jobStatus") or {}).get("startTime")

        flink_job = FlinkJob(
            id=metadata.get("uid", ""),
            name=metadata.get("name", ""),
            status=str(job_status) if job_status is not None else UNKNOWN_STATUS,
            type=job_type,
            startTime=int(start_time) if start_time is not None else None,
            shortImage=self._get_short_image(spec),
            flinkVersion=self._get_flink_version(spec),
            parallelism=self._get_parallelism(spec, tm_spec),
            resources={
                JM_LABEL: FlinkJobResources(
                    replicas=jm_spec.get("replicas") or 0,
                    cpu=str(((jm_spec.get("resource") or {}).get("cpu")) or ""),
                    mem=((jm_spec.get("resource") or {}).get("memory")) or "",
                ),
                TM_LABEL: FlinkJobResources(
                    replicas=tm_replicas,
                    cpu=str(((tm_spec.get("resource") or {}).get("cpu")) or ""),
                    mem=((tm_spec.get("resource") or {}).get("memory")) or "",
                ),
            },
            metadata=(metadata.get("labels") or {}),
        )
        return flink_job

    def _get_job_type(self, spec: dict) -> FlinkJobType:
        return FlinkJobType.SESSION if spec.get("job") is None else FlinkJobType.APPLICATION

    def _get_short_image(self, spec: dict) -> str:
        image = spec.get("image") or ""
        return image.split("/", 1)[1] if "/" in image else image

    def _get_parallelism(self, spec: dict, tm_spec: dict) -> int:
        parallelism = 0
        job_spec = spec.get("job") or {}
        job_spec_parallelism = int(job_spec.get("parallelism") or 0)
        if job_spec_parallelism:
            return job_spec_parallelism

        # Fallback: replicas * configured task slots
        flink_conf: dict[str, str] | None = spec.get("flinkConfiguration")
        replicas = tm_spec.get("replicas")
        task_slots = None
        if flink_conf and isinstance(flink_conf, dict):
            task_slots = flink_conf.get(TM_NUMBER_OF_TASK_SLOTS)
        if task_slots is not None and replicas is not None:
            try:
                parallelism = int(task_slots) * int(replicas)
            except Exception:
                parallelism = 0
        return parallelism

    def _get_flink_version(self, spec: dict) -> str:
        raw = str(spec.get("flinkVersion") or "")
        return raw.replace("_", ".").replace("v", "")
