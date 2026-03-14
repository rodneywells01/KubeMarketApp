#!/usr/bin/env python3
"""
Lightweight local HTTP performance tester.

This script is intentionally dependency-free (stdlib only) so it can run in
local dev environments without extra setup.
"""

from __future__ import annotations

import argparse
import base64
import json
import math
import os
import random
import statistics
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Endpoint:
    name: str
    method: str
    path: str
    headers: dict[str, str]
    body: str | None
    expected_statuses: set[int]
    weight: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a light local HTTP performance test against configured endpoints."
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:5000",
        help="Base URL for the app (default: %(default)s)",
    )
    parser.add_argument(
        "--config",
        default="perf/endpoints.local.json",
        help="Path to endpoint config JSON (default: %(default)s)",
    )
    parser.add_argument(
        "--requests",
        type=int,
        default=100,
        help="Total requests to send (default: %(default)s)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=10,
        help="Concurrent workers (default: %(default)s)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        help="Per-request timeout in seconds (default: %(default)s)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for endpoint selection (default: %(default)s)",
    )
    parser.add_argument(
        "--output",
        default="perf/results/latest.json",
        help="Where to write JSON results (default: %(default)s)",
    )
    parser.add_argument(
        "--fail-on-error-rate",
        type=float,
        default=0.05,
        help="Exit non-zero if error rate is above this threshold (default: %(default)s)",
    )
    return parser.parse_args()


def load_config(config_path: Path) -> list[Endpoint]:
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    items = raw.get("endpoints", [])
    if not items:
        raise ValueError("No endpoints found in config.")

    endpoints: list[Endpoint] = []
    for item in items:
        name = str(item.get("name", "")).strip() or str(item.get("path", "")).strip()
        method = str(item.get("method", "GET")).upper()
        path = str(item.get("path", "")).strip()
        if not path.startswith("/"):
            raise ValueError(f"Endpoint path must start with '/': {path}")

        headers = dict(item.get("headers", {}))
        body_obj = item.get("body")
        body = None if body_obj is None else json.dumps(body_obj)
        expected_statuses = set(item.get("expected_statuses", [200]))
        weight = int(item.get("weight", 1))
        if weight < 1:
            raise ValueError(f"Endpoint weight must be >= 1: {name}")

        endpoints.append(
            Endpoint(
                name=name,
                method=method,
                path=path,
                headers=headers,
                body=body,
                expected_statuses=expected_statuses,
                weight=weight,
            )
        )

    return endpoints


def apply_basic_auth(
    headers: dict[str, str], username: str | None, password: str | None
) -> dict[str, str]:
    merged = dict(headers)
    if username is None or password is None:
        return merged
    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("utf-8")
    merged["Authorization"] = f"Basic {token}"
    return merged


def percentile(values_ms: list[float], pct: float) -> float:
    if not values_ms:
        return math.nan
    sorted_values = sorted(values_ms)
    rank = (pct / 100.0) * (len(sorted_values) - 1)
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return sorted_values[lower]
    lower_val = sorted_values[lower]
    upper_val = sorted_values[upper]
    return lower_val + (upper_val - lower_val) * (rank - lower)


def build_weighted_choices(endpoints: list[Endpoint]) -> list[Endpoint]:
    weighted: list[Endpoint] = []
    for ep in endpoints:
        weighted.extend([ep] * ep.weight)
    return weighted


def run_single_request(
    request_id: int,
    base_url: str,
    endpoint: Endpoint,
    timeout: float,
    auth_user: str | None,
    auth_pass: str | None,
) -> dict[str, Any]:
    url = base_url.rstrip("/") + endpoint.path
    payload = endpoint.body.encode("utf-8") if endpoint.body is not None else None
    headers = apply_basic_auth(endpoint.headers, auth_user, auth_pass)
    if payload is not None and "Content-Type" not in headers:
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(
        url=url,
        method=endpoint.method,
        data=payload,
        headers=headers,
    )

    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            status_code = int(response.getcode())
            _ = response.read()
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            ok = status_code in endpoint.expected_statuses
            return {
                "request_id": request_id,
                "endpoint": endpoint.name,
                "path": endpoint.path,
                "status_code": status_code,
                "ok": ok,
                "error": None if ok else "unexpected_status",
                "latency_ms": elapsed_ms,
            }
    except urllib.error.HTTPError as exc:
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        status_code = int(exc.code)
        ok = status_code in endpoint.expected_statuses
        return {
            "request_id": request_id,
            "endpoint": endpoint.name,
            "path": endpoint.path,
            "status_code": status_code,
            "ok": ok,
            "error": None if ok else "http_error",
            "latency_ms": elapsed_ms,
        }
    except Exception as exc:  # noqa: BLE001
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        return {
            "request_id": request_id,
            "endpoint": endpoint.name,
            "path": endpoint.path,
            "status_code": None,
            "ok": False,
            "error": str(exc),
            "latency_ms": elapsed_ms,
        }


def summarize(results: list[dict[str, Any]], duration_seconds: float) -> dict[str, Any]:
    latencies = [float(r["latency_ms"]) for r in results]
    total = len(results)
    failures = [r for r in results if not r["ok"]]
    success = total - len(failures)
    error_rate = (len(failures) / total) if total else 0.0

    by_endpoint: dict[str, dict[str, Any]] = {}
    for r in results:
        key = str(r["endpoint"])
        bucket = by_endpoint.setdefault(
            key, {"total": 0, "success": 0, "failures": 0, "latencies_ms": []}
        )
        bucket["total"] += 1
        bucket["latencies_ms"].append(float(r["latency_ms"]))
        if r["ok"]:
            bucket["success"] += 1
        else:
            bucket["failures"] += 1

    endpoint_summary: dict[str, Any] = {}
    for key, value in by_endpoint.items():
        endpoint_summary[key] = {
            "total": value["total"],
            "success": value["success"],
            "failures": value["failures"],
            "error_rate": value["failures"] / value["total"] if value["total"] else 0.0,
            "avg_ms": statistics.mean(value["latencies_ms"]) if value["latencies_ms"] else math.nan,
            "p95_ms": percentile(value["latencies_ms"], 95),
        }

    return {
        "total_requests": total,
        "success_requests": success,
        "failed_requests": len(failures),
        "error_rate": error_rate,
        "duration_seconds": duration_seconds,
        "requests_per_second": (total / duration_seconds) if duration_seconds > 0 else 0.0,
        "latency_ms": {
            "min": min(latencies) if latencies else math.nan,
            "avg": statistics.mean(latencies) if latencies else math.nan,
            "p50": percentile(latencies, 50),
            "p90": percentile(latencies, 90),
            "p95": percentile(latencies, 95),
            "p99": percentile(latencies, 99),
            "max": max(latencies) if latencies else math.nan,
        },
        "by_endpoint": endpoint_summary,
        "sample_failures": failures[:10],
    }


def print_console_summary(summary: dict[str, Any]) -> None:
    print("\n=== Light Performance Test Summary ===")
    print(f"Total Requests:  {summary['total_requests']}")
    print(f"Success:         {summary['success_requests']}")
    print(f"Failures:        {summary['failed_requests']}")
    print(f"Error Rate:      {summary['error_rate']:.2%}")
    print(f"Duration:        {summary['duration_seconds']:.2f}s")
    print(f"Throughput:      {summary['requests_per_second']:.2f} req/s")
    l = summary["latency_ms"]
    print(
        "Latency (ms):    "
        f"min={l['min']:.2f} avg={l['avg']:.2f} "
        f"p50={l['p50']:.2f} p90={l['p90']:.2f} p95={l['p95']:.2f} "
        f"p99={l['p99']:.2f} max={l['max']:.2f}"
    )
    print("\nBy Endpoint:")
    for name, metrics in summary["by_endpoint"].items():
        print(
            f"  - {name}: total={metrics['total']} "
            f"errors={metrics['failures']} ({metrics['error_rate']:.2%}) "
            f"avg={metrics['avg_ms']:.2f}ms p95={metrics['p95_ms']:.2f}ms"
        )


def main() -> int:
    args = parse_args()
    if args.requests < 1:
        raise ValueError("--requests must be >= 1")
    if args.concurrency < 1:
        raise ValueError("--concurrency must be >= 1")
    if args.timeout <= 0:
        raise ValueError("--timeout must be > 0")

    config_path = Path(args.config)
    endpoints = load_config(config_path)
    weighted = build_weighted_choices(endpoints)

    random.seed(args.seed)
    auth_user = None
    auth_pass = None
    if "PERF_BASIC_AUTH_USER" in os.environ:
        auth_user = os.environ.get("PERF_BASIC_AUTH_USER")
        auth_pass = os.environ.get("PERF_BASIC_AUTH_PASS")

    lock = threading.Lock()
    results: list[dict[str, Any]] = []
    start = time.perf_counter()

    def submit_task(i: int) -> dict[str, Any]:
        endpoint = random.choice(weighted)
        return run_single_request(
            request_id=i,
            base_url=args.base_url,
            endpoint=endpoint,
            timeout=args.timeout,
            auth_user=auth_user,
            auth_pass=auth_pass,
        )

    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = [executor.submit(submit_task, i) for i in range(args.requests)]
        for future in as_completed(futures):
            result = future.result()
            with lock:
                results.append(result)

    duration = time.perf_counter() - start
    summary = summarize(results=results, duration_seconds=duration)
    print_console_summary(summary)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "config": {
            "base_url": args.base_url,
            "config_file": str(config_path),
            "requests": args.requests,
            "concurrency": args.concurrency,
            "timeout": args.timeout,
            "seed": args.seed,
        },
        "summary": summary,
        "results": results,
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nResults written to {output_path}")

    if summary["error_rate"] > args.fail_on_error_rate:
        print(
            f"Error rate {summary['error_rate']:.2%} exceeded threshold "
            f"{args.fail_on_error_rate:.2%}."
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
