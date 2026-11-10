"""Locust scenarios A/B/C for the OpinionLab API (PRD 13.8).

Run against a staging API:

    locust -f benchmarks/locustfile.py ScenarioAReadHeavy \
        --host https://staging.example --users 50 --spawn-rate 5 --run-time 15m

Credentials come from ``OPINIONLAB_TEST_EMAIL``/``OPINIONLAB_TEST_PASSWORD``.
"""

from __future__ import annotations

import os
import uuid

from locust import HttpUser, between, constant, task


class _BaseUser(HttpUser):
    abstract = True

    def on_start(self) -> None:
        email = os.environ.get("OPINIONLAB_TEST_EMAIL", "")
        password = os.environ.get("OPINIONLAB_TEST_PASSWORD", "")
        response = self.client.post(
            "/api/v1/auth/login", json={"email": email, "password": password}
        )
        token = response.json().get("access_token", "") if response.ok else ""
        self.client.headers.update({"Authorization": f"Bearer {token}"})
        self.scenario_id = os.environ.get("OPINIONLAB_SCENARIO_ID", "")
        self.token = token


class ScenarioAReadHeavy(_BaseUser):
    """50 concurrent readers + 3 job submissions per second, 15 minutes."""

    wait_time = constant(0.2)

    @task(20)
    def list_scenarios(self) -> None:
        self.client.get("/api/v1/scenarios", name="/scenarios")

    @task(10)
    def list_runs(self) -> None:
        self.client.get("/api/v1/runs", name="/runs")

    @task(10)
    def poll_metrics(self) -> None:
        run_id = os.environ.get("OPINIONLAB_RUN_ID", "")
        if run_id:
            self.client.get(f"/api/v1/runs/{run_id}/metrics", name="/runs/[id]/metrics")

    @task(1)
    def submit_job(self) -> None:
        if self.scenario_id:
            with self.client.post(
                "/api/v1/runs",
                json={"scenario_id": self.scenario_id, "repeats": 10},
                headers={"X-Idempotency-Key": f"load-{uuid.uuid4()}"},
                catch_response=True,
                name="/runs POST",
            ) as response:
                if response.status_code not in (201, 409, 429):
                    response.failure(f"unexpected {response.status_code}")


class ScenarioBBatchBurst(_BaseUser):
    """20 users submit ~60 large jobs in 30 minutes; queue position must be sane."""

    wait_time = between(15, 25)

    @task
    def submit_large_job(self) -> None:
        if not self.scenario_id:
            return
        with self.client.post(
            "/api/v1/runs",
            json={"scenario_id": self.scenario_id, "repeats": 100},
            headers={"X-Idempotency-Key": f"batch-{uuid.uuid4()}"},
            catch_response=True,
            name="/runs POST (batch)",
        ) as response:
            if response.status_code == 201:
                payload = response.json()["data"]
                assert payload["status"] in {"queued", "running"}
            elif response.status_code not in (409, 429):
                response.failure(f"unexpected {response.status_code}")


class ScenarioCAbuse(_BaseUser):
    """Single org hammering 500 job/s must see 429 and stay within the pool."""

    wait_time = constant(0.0)

    @task
    def spam_submit(self) -> None:
        if not self.scenario_id:
            return
        with self.client.post(
            "/api/v1/runs",
            json={"scenario_id": self.scenario_id, "repeats": 1},
            headers={"X-Idempotency-Key": f"abuse-{uuid.uuid4()}"},
            catch_response=True,
            name="/runs POST (abuse)",
        ) as response:
            if response.status_code == 429:
                response.success()
            elif response.status_code not in (201, 409):
                response.failure(f"unexpected {response.status_code}")
