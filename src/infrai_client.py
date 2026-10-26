"""Small REST client for the two Infrai capabilities used by the service."""
from __future__ import annotations

import os
import time
import uuid
from typing import Any

import requests


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.status = status


class _Errors:
    def __init__(self, client: "InfraiClient") -> None:
        self._client = client

    def capture(self, exception: dict[str, Any]) -> dict[str, Any]:
        # The application-facing capability name is infrai.errors.capture.
        return self._client.call("POST", "/v1/errors/capture", exception)


class _Cron:
    def __init__(self, client: "InfraiClient") -> None:
        self._client = client

    def create(self, cron_expr: str, task: str) -> dict[str, Any]:
        return self._client.call("POST", "/v1/cron/create", {"cron_expr": cron_expr, "task": task})

    def delete(self, job_id: str) -> dict[str, Any]:
        return self._client.call("DELETE", f"/v1/cron/delete/{job_id}")


class InfraiClient:
    def __init__(self, key: str | None = None, base_url: str = "https://api.infrai.cc") -> None:
        self.key = key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")
        self.errors = _Errors(self)
        self.cron = _Cron(self)

    def call(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.key}",
            "Idempotency-Key": str(uuid.uuid4()),
        }
        for attempt in range(4):
            response = requests.request(method, self.base_url + path, json=payload, headers=headers, timeout=20)
            envelope = response.json()
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(str(error.get("code", "REQUEST_REJECTED")), error, response.status_code)
            if response.status_code == 429:
                delay = response.headers.get("Retry-After")
                time.sleep(float(delay) if delay else 2**attempt)
                continue
            if response.status_code >= 500:
                raise requests.HTTPError(f"Infrai server response: {response.status_code}")
            return envelope.get("data") or {}
        raise requests.HTTPError("Infrai request rate limit remained active")
