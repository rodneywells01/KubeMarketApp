# AGENTS.md

## Purpose
This file guides coding agents working in `KubeMarketApp`.
Use it to keep app, container, and Helm changes consistent and deployable.

## Repo Scope
- Flask web app (`main.py`).
- Container build and publish workflow (Docker + GHCR).
- Helm chart (`mychart`) used for Kubernetes deployment.

## People And Ownership
- Rodney Wells is the likely primary maintainer for this repo and should be treated as the default reviewer for runtime, chart, and release workflow changes.
- Coordinate with the platform/bootstrap owner before assuming cert-manager, ingress class, or cluster-wide defaults can be changed here.

## Agent Operating Rules
1. Preserve user changes and avoid reverting unrelated edits.
2. Keep Flask app behavior simple unless feature work is requested.
3. Ensure app/container/chart ports stay aligned (container and service currently use `5000`).
4. Avoid embedding secrets in chart values or source files.
5. Keep ingress and TLS defaults environment-aware; avoid forcing prod-only assumptions in dev.
6. Treat GHCR publishing config and any credential-bearing remote configuration as sensitive operational setup.

## Deployment Expectations
- Image source should remain configurable by chart values.
- Ingress + cert-manager annotations are allowed but must be explicit in values.
- Any API-versioned Kubernetes resources should use supported/stable APIs.

## Validation Workflow (when changing app/chart)
1. Run basic Python syntax check if Python files change.
2. Run Helm template/lint checks if chart templates or values change.
3. Verify probe paths/ports match Flask runtime.
4. If CI or image tags change, document release impact.

## High-Risk Areas
- `mychart/templates/hpa.yaml`: API version compatibility risk.
- `mychart/values.yaml`: ingress host/TLS defaults can accidentally impact environments.
- `.github/workflows/build-push.yml`: controls image publication behavior.

## Coordination Notes
- Ingress hostnames, TLS annotations, and cert-manager expectations should stay aligned with `ArgoCDBootstrap/`.
- If fixing something in both this repo and `../KubeMarketApp_hotfix`, call out whether the change should be mirrored or intentionally left divergent.

## Documentation Convention
- Keep persistent findings in `notes/`.
- Update notes with date when deployment assumptions change.
