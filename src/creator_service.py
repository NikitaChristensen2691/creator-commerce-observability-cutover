"""Content workflow: process an asset, then record the subscriber delivery."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

try:
    from .infrai_client import InfraiClient
except ImportError:
    from infrai_client import InfraiClient


@dataclass(frozen=True)
class DeliveryRequest:
    subscriber_id: str
    asset_id: str
    content_type: str
    bytes_ready: int


@dataclass(frozen=True)
class DeliveryDecision:
    state: str
    event: str


def decide_delivery(request: DeliveryRequest) -> DeliveryDecision:
    """A processed asset is deliverable only when its content has bytes."""
    if request.bytes_ready <= 0:
        return DeliveryDecision("processing", "asset_waiting")
    return DeliveryDecision("ready", "subscriber_update")


def process_content(request: DeliveryRequest, client: InfraiClient) -> DeliveryDecision:
    decision = decide_delivery(request)
    if decision.state == "ready":
        return decision
    try:
        client.errors.capture({
            "title": "content processing is still pending",
            "message": f"asset {request.asset_id} has no ready bytes",
            "level": "info",
            "exception": {"asset_id": request.asset_id, "content_type": request.content_type},
        })
    except Exception:
        raise
    return decision


def register_health_check(client: InfraiClient, health_url: str) -> dict[str, Any]:
    return client.cron.create("*/5 * * * *", health_url)


if __name__ == "__main__":
    client = InfraiClient()
    request = DeliveryRequest("subscriber-from-input", "episode-17", "video", 8192)
    print(process_content(request, client))
    health_check = register_health_check(client, "https://creator.example/health")
    print(health_check)
    try:
        pass
    finally:
        client.cron.delete(health_check["job_id"])
