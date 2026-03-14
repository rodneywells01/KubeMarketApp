# Local Performance Test Suite

This is a lightweight HTTP load tester for local development.

## Quick start

1. Start the app:
   - `make run`
2. Run a light performance pass:
   - `make perf-test`

## Direct usage

```bash
python3 scripts/perf_test.py \
  --base-url http://127.0.0.1:5000 \
  --config perf/endpoints.local.json \
  --requests 200 \
  --concurrency 20 \
  --timeout 5 \
  --output perf/results/latest.json
```

## Endpoint config format

Edit `perf/endpoints.local.json` to target the routes you care about:

```json
{
  "endpoints": [
    {
      "name": "landing_page",
      "method": "GET",
      "path": "/",
      "expected_statuses": [200],
      "weight": 5
    }
  ]
}
```

Fields:
- `name`: Label used in reports.
- `method`: HTTP method.
- `path`: Path appended to `--base-url`.
- `expected_statuses`: Status codes treated as success.
- `weight`: Relative frequency for this endpoint in request selection.
- `headers` (optional): Request headers.
- `body` (optional): JSON body for non-GET calls.

## Basic auth support

If your endpoint requires basic auth:

```bash
export PERF_BASIC_AUTH_USER="your-user"
export PERF_BASIC_AUTH_PASS="your-pass"
```

The tester will include `Authorization: Basic ...` automatically.

## Output

Each run writes:
- Console summary (throughput, error rate, latency percentiles)
- Full JSON report at `perf/results/latest.json`
