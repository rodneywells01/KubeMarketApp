# KubeMarketApp - Project Findings

Last reviewed: 2026-02-07

## Purpose
This repository contains a simple Flask web app packaged for Kubernetes deployment with Helm and containerized via Docker/GHCR workflows.

## Current Structure
- `main.py`: Single-route Flask app returning an HTML landing page.
- `Dockerfile`: Python 3.11 slim image, runs `flask run` on port 5000.
- `mychart/`: Helm chart with Deployment, Service, Ingress, HPA, and ServiceAccount templates.
- `.github/workflows/build-push.yml`: Builds and pushes container images to GHCR on PR/push.
- `makefile`: Local run, Docker build/run, and GHCR release targets.

## Notable Findings
1. Helm values are currently aligned for Flask app deployment (`service.port` 5000; image points to GHCR).
2. Ingress is enabled by default and configured for `tradely.live` with cert-manager annotations.
3. HPA template uses `autoscaling/v2beta1`, which is deprecated on newer Kubernetes versions.
4. `README.md` is empty, so operational context currently depends on tribal knowledge and file inspection.
5. `.venv` appears in repository tree; evaluate whether environment artifacts should be tracked.
6. `.github/copilot-instructions.md` appears partially stale versus current templates and values.

## Deployment Model
- Build/push image to GHCR.
- Install/upgrade Helm chart into cluster.
- Expose route through NGINX ingress with cert-manager-managed TLS.

## Suggested Follow-ups
- Update chart HPA API version to a modern stable API (e.g., `autoscaling/v2`).
- Add README with local run, image publish, and Helm deploy instructions.
- Reconcile stale instruction docs with actual chart/runtime behavior.
- Confirm ingress host/TLS defaults are environment-appropriate (dev vs prod overlays).
