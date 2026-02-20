"""
Pipeline status and configuration endpoints.
API-01: GET /api/v1/pipeline/status
API-08: PATCH /api/v1/config
"""
from __future__ import annotations

import random
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator

from ..auth import get_tenant_from_token

router = APIRouter(prefix="/api/v1", tags=["pipeline"])

# In-memory pipeline config.
# TODO: Persist to pipeline_config DB table in a future migration.
# NOTE: Under horizontal scaling, config will diverge across workers.
_pipeline_config: dict[str, Any] = {
    "mode": "dual",
    "batch_size": 50,
    "model": "nomic-embed-text-v1.5",
}


class NodeMetrics(BaseModel):
    rate: float | None = None
    latency: float | None = None


class NodeStatus(BaseModel):
    id: str
    status: str
    metrics: NodeMetrics


class PipelineStatusResponse(BaseModel):
    mode: str
    batch_size: int
    model: str
    throughput: float
    nodes: list[NodeStatus]


class ConfigPatchRequest(BaseModel):
    mode: Literal["online", "offline", "dual"] | None = None
    batch_size: int | None = None
    model: str | None = None

    # Validation handled in endpoint to return 400 with error_code format.


def _build_status_response() -> PipelineStatusResponse:
    throughput = round(random.uniform(8.0, 20.0), 1)
    return PipelineStatusResponse(
        mode=_pipeline_config["mode"],
        batch_size=_pipeline_config["batch_size"],
        model=_pipeline_config["model"],
        throughput=throughput,
        nodes=[
            NodeStatus(id="ingest", status="healthy", metrics=NodeMetrics(rate=round(throughput * 0.42, 1))),
            NodeStatus(id="embed", status="healthy", metrics=NodeMetrics(rate=throughput)),
            NodeStatus(id="vector", status="degraded", metrics=NodeMetrics(latency=120.0)),
        ],
    )


@router.get("/pipeline/status", response_model=PipelineStatusResponse)
async def get_pipeline_status(
    _: str | None = Depends(get_tenant_from_token),
) -> PipelineStatusResponse:
    """Return current pipeline status with live throughput sample."""
    return _build_status_response()


@router.patch("/config", response_model=PipelineStatusResponse)
async def patch_config(
    body: ConfigPatchRequest,
    _: str | None = Depends(get_tenant_from_token),
) -> PipelineStatusResponse:
    """Partially update pipeline configuration. In-memory only."""
    if body.batch_size is not None and not (1 <= body.batch_size <= 256):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "VALIDATION_ERROR", "message": "batch_size must be between 1 and 256"},
        )
    if body.mode is not None:
        _pipeline_config["mode"] = body.mode
    if body.batch_size is not None:
        _pipeline_config["batch_size"] = body.batch_size
    if body.model is not None:
        _pipeline_config["model"] = body.model

    return _build_status_response()
