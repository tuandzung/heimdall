from __future__ import annotations

from typing import Any


class FlinkDeploymentClient:
    """Async wrapper around Kubernetes API for FlinkDeployment custom resources.

    Assumes the Flink K8s Operator CRD is installed. Uses the dynamic client.
    """

    def __init__(self) -> None:
        # Lazy import
        from kubernetes_asyncio import client, config  # type: ignore

        self._client_mod = client
        self._config_mod = config
        self.api: client.CustomObjectsApi | None = None  # type: ignore
        # Group/Version/Plural for FlinkDeployment
        self.group = "flink.apache.org"
        self.versions = ["v1beta1", "v1"]
        self.plural = "flinkdeployments"

    async def _ensure(self) -> None:
        if self.api is not None:
            return
        # Try in-cluster first, fall back to kubeconfig
        try:
            await self._config_mod.load_incluster_config()  # type: ignore
        except Exception:
            await self._config_mod.load_kube_config()  # type: ignore
        self.api = self._client_mod.CustomObjectsApi()  # type: ignore

    async def find(self, namespace: str, label_selector: str | None = None) -> list[dict[str, Any]]:
        from kubernetes_asyncio.client.exceptions import ApiException  # type: ignore

        await self._ensure()
        assert self.api is not None

        last_error: Exception | None = None
        for version in self.versions:
            try:
                if namespace in ("*", "_all_", "ALL", "all"):
                    resp = await self.api.list_cluster_custom_object(  # type: ignore
                        group=self.group,
                        version=version,
                        plural=self.plural,
                        label_selector=label_selector,
                    )
                else:
                    resp = await self.api.list_namespaced_custom_object(  # type: ignore
                        group=self.group,
                        version=version,
                        namespace=namespace,
                        plural=self.plural,
                        label_selector=label_selector,
                    )
                return resp.get("items", [])
            except ApiException as ex:  # type: ignore
                if ex.status in (400, 404):
                    last_error = ex
                    continue
                raise
        if last_error:
            raise last_error
        raise RuntimeError("Unable to query FlinkDeployment: no served versions available")
